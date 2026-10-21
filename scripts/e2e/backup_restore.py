import os
import subprocess

import boto3

from src.pipelines.database_backup import backup_database, restore_database

bucket = os.environ['S3_BACKUP_BUCKET']
client = boto3.client('s3')
client.create_bucket(Bucket=bucket)


def runs(database):
    result = subprocess.run(
        ['psql', '--no-psqlrc', '--tuples-only', '--no-align', '--command', 'SELECT count(*) FROM runs;'],
        env={**os.environ, 'PGDATABASE': database}, check=True, capture_output=True, text=True,
    )
    return int(result.stdout.strip())


source = os.environ['PGDATABASE']
before = runs(source)
assert before > 0, 'Training must create MLflow runs before the restore test'
key = backup_database(bucket, client=client)
subprocess.run(['createdb', '--maintenance-db', source, 'e2e_restore'], check=True)
restore_database(bucket, key, 'e2e_restore', client=client)
assert runs('e2e_restore') == before, 'Restored MLflow runs differ from the source'
assert runs(source) == before, 'Restore changed the source database'
try:
    restore_database(bucket, key, source, client=client)
except ValueError:
    pass
else:
    raise AssertionError('Restore accepted the source database')
print('Backup checksum, restored runs and source protection verified')
