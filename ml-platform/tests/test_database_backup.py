import hashlib
import subprocess
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from src.pipelines import database_backup as backup


@pytest.fixture
def s3():
    client = Mock()
    payload = b"PGDMP-test-payload"
    client.head_object.return_value = {
        "ContentLength": len(payload),
        "Metadata": {"sha256": hashlib.sha256(payload).hexdigest()},
    }
    client.download_file.side_effect = lambda bucket, key, filename: Path(filename).write_bytes(
        payload
    )
    return client


def test_backup_dumps_and_checks_uploaded_object(monkeypatch, s3):
    def dump(command, **kwargs):
        Path(command[command.index("--file") + 1]).write_bytes(b"PGDMP-test-payload")

    monkeypatch.setattr(backup.subprocess, "run", dump)
    key = backup.backup_database("backups", client=s3)
    assert key.startswith("mlflow-backups/") and key.endswith(".dump")
    s3.upload_file.assert_called_once()
    assert (
        s3.upload_file.call_args.kwargs["ExtraArgs"]["Metadata"]["sha256"]
        == s3.head_object.return_value["Metadata"]["sha256"]
    )


def test_failed_dump_is_never_uploaded(monkeypatch, s3):
    monkeypatch.setattr(
        backup.subprocess, "run", Mock(side_effect=subprocess.CalledProcessError(1, "pg_dump"))
    )
    with pytest.raises(subprocess.CalledProcessError):
        backup.backup_database("backups", client=s3)
    s3.upload_file.assert_not_called()


@pytest.mark.parametrize("failure", ["empty", "size", "checksum"])
def test_backup_rejects_invalid_output(monkeypatch, s3, failure):
    def dump(command, **kwargs):
        Path(command[command.index("--file") + 1]).write_bytes(
            b"" if failure == "empty" else b"PGDMP-test-payload"
        )

    monkeypatch.setattr(backup.subprocess, "run", dump)
    if failure == "size":
        s3.head_object.return_value["ContentLength"] = 0
    elif failure == "checksum":
        s3.head_object.return_value["Metadata"]["sha256"] = "bad"
    with pytest.raises(ValueError):
        backup.backup_database("backups", client=s3)


@pytest.mark.parametrize(
    "source,target",
    [
        ("mlflow", "mlflow"),
        (None, "recovery"),
        ("mlflow", ""),
        ("mlflow", "postgresql://another-host/database"),
    ],
)
def test_restore_never_overwrites_source(monkeypatch, s3, source, target):
    monkeypatch.delenv("PGDATABASE", raising=False)
    command = Mock()
    monkeypatch.setattr(backup.subprocess, "run", command)
    with pytest.raises(ValueError):
        backup.restore_database("backups", "key", target, s3, source_database=source)
    command.assert_not_called()
    s3.download_file.assert_not_called()


@pytest.mark.parametrize("failure", ["occupied", "missing-checksum", "corrupt", None])
def test_restore_verifies_empty_target_and_integrity(monkeypatch, s3, failure):
    command = Mock(return_value=SimpleNamespace(stdout="1" if failure == "occupied" else "0"))
    monkeypatch.setattr(backup.subprocess, "run", command)
    if failure == "missing-checksum":
        s3.head_object.return_value["Metadata"] = {}
    elif failure == "corrupt":
        s3.download_file.side_effect = lambda bucket, key, filename: Path(filename).write_bytes(
            b"corrupt"
        )
    if failure:
        with pytest.raises(ValueError):
            backup.restore_database("backups", "key", "recovery", s3, source_database="mlflow")
        assert command.call_count == 1
    else:
        backup.restore_database("backups", "key", "recovery", s3, source_database="mlflow")
        args = command.call_args.args[0]
        assert args[0] == "pg_restore" and "--single-transaction" in args
        assert command.call_args.kwargs["env"]["PGDATABASE"] == "recovery"
