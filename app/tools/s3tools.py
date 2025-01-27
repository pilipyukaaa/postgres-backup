import threading
from pathlib import Path

import boto3  # type: ignore
import time
import os

ACCESS_KEY = os.environ.get('S3_ACCESS_KEY')
SECRET_KEY = os.environ.get('S3_SECRET_KEY')
ENDPOINT = os.environ.get('S3_ENDPOINT')
BUCKET = os.environ.get('S3_BUCKET')

s3 = boto3.client(
    's3',
    aws_access_key_id=ACCESS_KEY,
    aws_secret_access_key=SECRET_KEY,
    endpoint_url=ENDPOINT
)


class ProgressPercentage:
    def __init__(self, filename, size, logger):
        self._filename = filename
        self._size = size
        self._seen_so_far = 0
        self._lock = threading.Lock()
        self._logger = logger
        self._last_logged_percentage = 0

    def __call__(self, bytes_amount):
        with self._lock:
            self._seen_so_far += bytes_amount
            percentage = (self._seen_so_far / self._size) * 100
            current_percentage = int(percentage)
            if current_percentage % 10 == 0 and current_percentage != self._last_logged_percentage:
                self._logger.info(
                    f"Upload progress for {self._filename}: {current_percentage}% ({self._seen_so_far}/{self._size}"
                    f" bytes)"
                )
                self._last_logged_percentage = current_percentage


def upload_file(prefix, file_path, logger):
    size = file_path.stat().st_size
    logger.info(f"Starting upload of file: {file_path} with size {size} bytes")
    logger.debug(f"Upload prefix: {prefix}")

    with open(file_path, 'rb') as data:
        file_name = os.path.basename(file_path)
        path = f"{prefix}{time.strftime("%Y/%m/%d/")}{file_name}"
        logger.info(f"Uploading to S3 path: {path}")
        progress_callback = ProgressPercentage(file_name, size, logger)
        # Upload with progress tracking
        s3.upload_fileobj(
            data,
            BUCKET,
            path,
            Callback=progress_callback
        )
        logger.info(f"Successfully uploaded file to: s3://{BUCKET}/{path}")


def download_file(path, logger) -> Path:
    s3_path = path
    filename = Path(path).name
    local_path = f'./tmp/{filename}'
    logger.info(f"Starting download of file: s3://{BUCKET}/{s3_path}")

    try:
        # Get file size for progress tracking
        response = s3.head_object(Bucket=BUCKET, Key=s3_path)
        file_size = response['ContentLength']

        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(local_path), exist_ok=True)

        # Download with progress tracking
        progress_callback = ProgressPercentage('test', file_size, logger)

        s3.download_file(
            BUCKET,
            s3_path,
            local_path,
            Callback=progress_callback
        )

        logger.info(f"Successfully downloaded file to: {local_path}")
        return Path(os.path.abspath(local_path))

    except Exception as e:
        logger.error(f"Error downloading file from S3: {str(e)}")
        raise
