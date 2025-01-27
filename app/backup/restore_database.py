import os
from datetime import datetime
from pathlib import Path
from app.tools.pgtools import restore_postgres_db
from app.tools.cryptools import decrypt_file
from app.tools.s3tools import download_file
from app.backup.logging_config import setup_logger


class DatabaseRestore:
    def __init__(self):
        # Read from environment variables with defaults
        self.dump_date = datetime.strptime(os.getenv('DB_DATE'),  '%Y-%m-%d')
        self.host = os.getenv('DB_HOST', 'localhost')
        self.port = os.getenv('DB_PORT', '5432')
        self.database = os.getenv('DB_NAME')
        self.user = os.getenv('DB_USER')
        self.password = os.getenv('DB_PASSWORD')
        self.logger = setup_logger('backup_executor')
        self.instance = os.getenv('INSTANCE')
        self.enc_key = os.getenv('ENC_KEY')

    def execute(self, verbose: bool = False) -> None:
        """Execute the full backup process: backup -> encrypt -> upload"""
        backup_file = Path()
        encrypted_file = Path()
        try:
            backup_file = self._download_backup(self.dump_date, self.logger, self.instance, self.database)
            decrypted_file = self._decrypt_backup(backup_file, self.enc_key, self.logger)
            # decrypted_file = Path('/Users/andrewpilipyuk/PycharmProjects/postgres_backup/app/backup/tmp'
            #                       '/backup_datahub.sql.decrypted')
            self._restore_backup(decrypted_file, verbose, self.logger)
        except Exception as e:
            raise BackupError(f"Backup failed: {str(e)}")
        finally:
            self._cleanup_files(backup_file, encrypted_file)

    def _restore_backup(self, dump_file, verbose: bool, logger) -> Path:
        """Create database backup"""
        restore_postgres_db(
            self.host,
            self.port,
            self.database,
            self.user,
            self.password,
            dump_file,
            logger,
            verbose
        )
        return dump_file

    @staticmethod
    def _decrypt_backup(backup_file: Path, enc_key, logger) -> Path:
        """Decrypt the backup file"""
        return Path(decrypt_file(backup_file, enc_key, logger))

    @staticmethod
    def _download_backup(dump_date, logger, instance, db_name) -> Path:
        """Download encrypted backup from S3"""
        path = (f'postgres_backup/{instance}/{dump_date.year}/{dump_date.month:02d}/{dump_date.day:02d}'
                f'/backup_{db_name}.sql'
                f'.encrypted')
        local_path = download_file(path, logger)
        return local_path

    @staticmethod
    def _cleanup_files(*files: Path) -> None:
        """Clean up temporary files"""
        for file in files:
            if file and file.exists():
                file.unlink()


class BackupError(Exception):
    """Custom exception for backup operations"""
    pass


backup = DatabaseRestore()
backup.execute(verbose=os.getenv('VERBOSE'))
exit(0)
