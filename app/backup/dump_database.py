import os
from pathlib import Path
from app.tools.pgtools import backup_postgres_db
from app.tools.cryptools import encrypt_file
from app.tools.s3tools import upload_file
from app.backup.logging_config import setup_logger


class DatabaseBackup:
    def __init__(self):
        # Read from environment variables with defaults
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
            backup_file = self._create_backup(verbose, self.logger)
            encrypted_file = self._encrypt_backup(backup_file, self.enc_key, self.logger)
            self._upload_backup(encrypted_file, self.logger, self.instance)
            self._upload_backup(encrypted_file.with_suffix('.metadata'), self.logger, self.instance)
        except Exception as e:
            raise BackupError(f"Backup failed: {str(e)}")
        finally:
            self._cleanup_files(backup_file, encrypted_file)

    def _create_backup(self, verbose: bool, logger) -> Path:
        """Create database backup"""
        backup_file = self._get_backup_path(self.database)
        backup_postgres_db(
            self.host,
            self.port,
            self.database,
            self.user,
            self.password,
            backup_file,
            logger,
            verbose
        )
        return backup_file

    @staticmethod
    def _encrypt_backup(backup_file: Path, enc_key, logger) -> Path:
        """Encrypt the backup file"""
        return Path(encrypt_file(backup_file, enc_key, logger))

    @staticmethod
    def _upload_backup(encrypted_file: Path, logger, instance) -> None:
        """Upload encrypted backup to S3"""
        upload_file(f'postgres_backup/{instance}/', encrypted_file, logger)

    @staticmethod
    def _get_backup_path(database) -> Path:
        """Generate backup file path"""
        return Path.cwd() / f"backup_{database}.sql"

    @staticmethod
    def _cleanup_files(*files: Path) -> None:
        """Clean up temporary files"""
        for file in files:
            if file and file.exists():
                file.unlink()


class BackupError(Exception):
    """Custom exception for backup operations"""
    pass


backup = DatabaseBackup()
backup.execute(verbose=os.getenv('VERBOSE'))
exit(0)
