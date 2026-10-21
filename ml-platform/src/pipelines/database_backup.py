import hashlib
import os
import re
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from uuid import uuid4

import boto3


def _checksum(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def backup_database(bucket: str, prefix: str = "mlflow-backups", client=None) -> str:
    client = client or boto3.client("s3")
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    key = f"{prefix.strip('/')}/{timestamp}-{uuid4().hex}.dump"
    with tempfile.TemporaryDirectory() as directory:
        dump = Path(directory) / "database.dump"
        subprocess.run(
            ["pg_dump", "--format=custom", "--no-owner", "--file", str(dump)],
            check=True,
            timeout=1800,
        )
        if not dump.stat().st_size:
            raise ValueError("Database backup is empty")
        checksum = _checksum(dump)
        client.upload_file(str(dump), bucket, key, ExtraArgs={"Metadata": {"sha256": checksum}})
        metadata = client.head_object(Bucket=bucket, Key=key)
        if metadata["ContentLength"] != dump.stat().st_size:
            raise ValueError("Uploaded backup size does not match")
        if metadata.get("Metadata", {}).get("sha256") != checksum:
            raise ValueError("Uploaded backup checksum metadata does not match")
    return key


def restore_database(
    bucket: str, key: str, database: str, client=None, source_database: Optional[str] = None
) -> None:
    source_database = source_database or os.environ.get("PGDATABASE")
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]{0,62}", database or ""):
        raise ValueError("Restore target must be a plain PostgreSQL database name")
    if not source_database or database == source_database:
        raise ValueError("Restore requires a separate, empty database and the source PGDATABASE")
    client = client or boto3.client("s3")
    env = {**os.environ, "PGDATABASE": database}
    result = subprocess.run(
        ["psql", "--no-psqlrc", "--tuples-only", "--no-align", "--command",
         "SELECT count(*) FROM information_schema.tables "
         "WHERE table_schema NOT IN ('pg_catalog', 'information_schema');"],
        env=env, check=True, capture_output=True, text=True, timeout=30,
    )
    if result.stdout.strip() != "0":
        raise ValueError("Restore target database is not empty")
    with tempfile.TemporaryDirectory() as directory:
        dump = Path(directory) / "database.dump"
        metadata = client.head_object(Bucket=bucket, Key=key)
        checksum = metadata.get("Metadata", {}).get("sha256")
        if not checksum:
            raise ValueError("Backup has no checksum metadata")
        client.download_file(bucket, key, str(dump))
        if _checksum(dump) != checksum:
            raise ValueError("Backup checksum verification failed")
        subprocess.run(
            ["pg_restore", "--exit-on-error", "--single-transaction", "--no-owner",
             "--no-privileges", "--dbname", database, str(dump)],
            env=env, check=True, timeout=1800,
        )
