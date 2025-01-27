import subprocess
import os
from pathlib import Path


class PostgresBackupError(Exception):
    pass


class PostgresRestoreError(Exception):
    pass


def backup_postgres_db(
        host: str,
        port: str,
        database_name: str,
        user: str,
        password: str,
        dest_file: Path,
        logger,
        verbose: bool = False,
) -> bytes:
    logger.info(f"Starting backup of database '{database_name}' to {dest_file}")
    logger.debug(f"Connection details - Host: {host}, Port: {port}, User: {user}")
    try:
        if verbose:
            logger.info("Running backup in verbose mode using pg_dump")
            os.environ["PGPASSWORD"] = password
            command = [
                'pg_dump',
                '-U', user,
                '-h', host,
                '-p', port,
                '-d', database_name,
                '-w',
                '-c',
                '-f', dest_file,
                '-v'
            ]
        else:
            logger.info("Running backup in non verbose mode using pg_dump")
            os.environ["PGPASSWORD"] = password
            command = [
                'pg_dump',
                '-U', user,
                '-h', host,
                '-p', port,
                '-d', database_name,
                '-w',
                '-c',
                '-f', dest_file
            ]
        logger.debug(f"Executing command: {' '.join(str(command)).replace(' ', '')}")
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

        output, error = process.communicate()

        if process.returncode != 0:
            raise PostgresBackupError(f'Command failed with return code: {process.returncode}\nError: {error.decode()}')
        logger.info(f"Backup completed successfully to {dest_file}")
        return output

    except Exception as e:
        raise PostgresBackupError(f"Backup failed: {str(e)}")


def restore_postgres_db(
        host: str,
        port: str,
        database_name: str,
        user: str,
        password: str,
        dump_file: Path,
        logger,
        verbose: bool = False,
) -> bytes:
    logger.info(f"Starting restore of database '{database_name}' from {dump_file}")
    logger.debug(f"Connection details - Host: {host}, Port: {port}, User: {user}")
    try:
        os.environ["PGPASSWORD"] = password
        command = ['psql',
                   '-U', user,
                   '-h', host,
                   '-p', port,
                   '-c', f"CREATE DATABASE {database_name};"]
        process = subprocess.Popen(
            command
        )
        process.communicate()
        if verbose:
            logger.info("Running restore in verbose mode using psql")

            command = [
                'psql',
                '-U', user,
                '-h', host,
                '-p', port,
                '-d', database_name,
                '-v',
                'ON_ERROR_STOP=0',
                '-f', dump_file
            ]

        else:
            logger.info("Running backup in non verbose mode using pg_dump")
            command = [
                'psql',
                '-U', user,
                '-h', host,
                '-p', port,
                '-d', database_name,
                '-f', dump_file,
                '-q'
            ]
        logger.debug(f"Executing command: {' '.join(str(command)).replace(' ', '')}")
        process = subprocess.Popen(
            command
        )
        output = process.communicate()

        if int(process.returncode) != 0:
            print('Command failed. Return code : {}'.format(process.returncode))

        return output

    except Exception as e:
        raise PostgresRestoreError(f"Restore failed: {str(e)}")
