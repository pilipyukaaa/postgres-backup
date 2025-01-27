import os
import hashlib
import time
from pathlib import Path
from typing import Union
from datetime import datetime
from cryptography.fernet import Fernet


def calculate_file_hash(file_path: Path, chunk_size: int = 64 * 1024 * 1024) -> str:
    """Calculate SHA-256 hash of a file."""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(chunk_size), b""):
            sha256_hash.update(chunk)
    return sha256_hash.hexdigest()


def format_size(size: float) -> str:
    """Convert size in bytes to human-readable format."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size < 1024:
            return f"{size:.2f} {unit}"
        size /= 1024
    return f"{size:.2f} PB"


def format_time(seconds: float) -> str:
    """Convert seconds to human-readable format."""
    if seconds < 60:
        return f"{seconds:.2f} seconds"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.2f} minutes"
    else:
        hours = seconds / 3600
        return f"{hours:.2f} hours"


def encrypt_string(string: str, enc_key: bytes) -> str:
    """Encrypt a string using Fernet symmetric encryption."""
    fernet = Fernet(enc_key)
    return fernet.encrypt(string.encode()).decode("utf-8")


def decrypt_string(string: Union[str, bytes], enc_key: bytes) -> str:
    """Decrypt a string using Fernet symmetric encryption."""
    fernet = Fernet(enc_key)
    if isinstance(string, str):
        string = string.encode()
    return fernet.decrypt(string).decode("utf-8")


def encrypt_file(
        file_path: Union[str, Path],
        enc_key: bytes,
        logger,
        chunk_size: int = 64 * 1024 * 1024,  # 64MB chunks
        progress_interval: int = 5  # Log progress every 5 seconds
) -> Path:
    """
    Encrypt a large file using Fernet symmetric encryption, processing it in chunks.

    Args:
        file_path: Path to the file to encrypt
        enc_key: Encryption-key
        logger: Logger instance
        chunk_size: Size of chunks to process (default: 64KB)
        progress_interval: How often to log progress in seconds (default: 5)

    Returns:
        Path: Path to the encrypted file

    Raises:
        Exception: If encryption fails
    """
    file_path = Path(file_path)
    fernet = Fernet(enc_key)
    encrypted_path = file_path.with_suffix('.sql.encrypted')

    try:
        # Get file size and calculate hash
        file_size = file_path.stat().st_size
        logger.info(f"Starting encryption of file: {file_path}")
        logger.info(f"File size: {format_size(file_size)}")

        original_hash = calculate_file_hash(file_path)
        logger.info(f"Original file hash (SHA-256): {original_hash}")

        # Initialize progress tracking
        processed_size = 0
        start_time = time.time()
        last_progress_update = start_time

        with open(file_path, 'rb') as infile, open(encrypted_path, 'wb') as outfile:
            # Write original file hash at the beginning of encrypted file
            outfile.write(len(original_hash).to_bytes(8, byteorder='big'))
            outfile.write(original_hash.encode())

            while chunk := infile.read(chunk_size):
                encrypted_chunk = fernet.encrypt(chunk)
                # Write the size of the encrypted chunk first
                outfile.write(len(encrypted_chunk).to_bytes(8, byteorder='big'))
                outfile.write(encrypted_chunk)

                # Update progress
                processed_size += len(chunk)
                current_time = time.time()

                # Log progress at specified intervals
                if current_time - last_progress_update >= progress_interval:
                    progress = (processed_size / file_size) * 100
                    elapsed_time = current_time - start_time
                    speed = processed_size / elapsed_time  # bytes per second
                    remaining_size = file_size - processed_size
                    estimated_time_remaining = remaining_size / speed if speed > 0 else 0

                    logger.info(
                        f"Progress: {progress:.2f}% | "
                        f"Speed: {format_size(speed)}/s | "
                        f"Processed: {format_size(processed_size)} | "
                        f"Remaining time: {format_time(estimated_time_remaining)}"
                    )
                    last_progress_update = current_time

        # Calculate hash of encrypted file
        encrypted_hash = calculate_file_hash(encrypted_path)

        # Save metadata
        metadata = {
            'original_filename': file_path.name,
            'original_size': file_size,
            'original_hash': original_hash,
            'encrypted_hash': encrypted_hash,
            'encryption_date': datetime.now().isoformat(),
            'encryption_time': time.time() - start_time
        }

        # Save metadata to companion file
        metadata_path = encrypted_path.with_suffix('.metadata')
        with open(metadata_path, 'w') as meta_file:
            for key, value in metadata.items():
                meta_file.write(f"{key}: {value}\n")

        # Remove original file
        os.remove(file_path)

        # Log completion
        total_time = time.time() - start_time
        average_speed = file_size / total_time
        logger.info(f"Encryption completed successfully:")
        logger.info(f"Encrypted file: {encrypted_path}")
        logger.info(f"Total time: {format_time(total_time)}")
        logger.info(f"Average speed: {format_size(average_speed)}/s")
        logger.info(f"Encrypted file hash (SHA-256): {encrypted_hash}")

        return encrypted_path

    except Exception as e:
        logger.error(f"Error encrypting file {file_path}: {str(e)}")
        # Clean up partial files if they exist
        if encrypted_path.exists():
            encrypted_path.unlink()
        metadata_path = encrypted_path.with_suffix('.metadata')
        if metadata_path.exists():
            metadata_path.unlink()
        raise


def decrypt_file(
        file_path: Union[str, Path],
        enc_key: bytes,
        logger,
        chunk_size: int = 64 * 1024,  # 64KB chunks
        progress_interval: int = 5  # Log progress every 5 seconds
) -> Path:
    """
    Decrypt a large file using Fernet symmetric encryption, processing it in chunks.

    Args:
        file_path: Path to the encrypted file
        enc_key: Encryption-key
        logger: Logger instance
        chunk_size: Size of chunks to process (default: 64KB)
        progress_interval: How often to log progress in seconds (default: 5)

    Returns:
        Path: Path to the decrypted file

    Raises:
        Exception: If decryption fails
    """
    file_path = Path(file_path)
    fernet = Fernet(enc_key)

    # Read metadata if available
    metadata_path = file_path.with_suffix('.metadata')
    metadata = {}
    if metadata_path.exists():
        with open(metadata_path, 'r') as meta_file:
            for line in meta_file:
                key, value = line.strip().split(': ', 1)
                metadata[key] = value

    # Determine output filename
    if 'original_filename' in metadata:
        decrypted_path = file_path.parent / f"decrypted_{metadata['original_filename']}"
    else:
        decrypted_path = Path(str(file_path).replace('.encrypted', '.decrypted'))

    try:
        # Get file size
        file_size = file_path.stat().st_size
        logger.info(f"Starting decryption of file: {file_path}")
        logger.info(f"Encrypted file size: {format_size(file_size)}")

        # Initialize progress tracking
        processed_size = 0
        start_time = time.time()
        last_progress_update = start_time

        with open(file_path, 'rb') as infile, open(decrypted_path, 'wb') as outfile:
            # Read the original file hash length and hash
            hash_length = int.from_bytes(infile.read(8), byteorder='big')
            original_hash = infile.read(hash_length).decode()

            # Adjust file size to exclude header
            file_size -= (8 + hash_length)

            while True:
                # Read the size of the next chunk
                chunk_size_bytes = infile.read(8)
                if not chunk_size_bytes:
                    break

                chunk_size = int.from_bytes(chunk_size_bytes, byteorder='big')
                encrypted_chunk = infile.read(chunk_size)

                if not encrypted_chunk:
                    break

                decrypted_chunk = fernet.decrypt(encrypted_chunk)
                outfile.write(decrypted_chunk)

                # Update progress
                processed_size += len(encrypted_chunk)
                current_time = time.time()

                # Log progress at specified intervals
                if current_time - last_progress_update >= progress_interval:
                    progress = (processed_size / file_size) * 100
                    elapsed_time = current_time - start_time
                    speed = processed_size / elapsed_time  # bytes per second
                    remaining_size = file_size - processed_size
                    estimated_time_remaining = remaining_size / speed if speed > 0 else 0

                    logger.info(
                        f"Progress: {progress:.2f}% | "
                        f"Speed: {format_size(speed)}/s | "
                        f"Processed: {format_size(processed_size)} | "
                        f"Remaining time: {format_time(estimated_time_remaining)}"
                    )
                    last_progress_update = current_time

        # Verify file hash
        decrypted_hash = calculate_file_hash(decrypted_path)
        if original_hash == decrypted_hash:
            logger.info("File hash verification successful!")
        else:
            raise ValueError("File hash verification failed! The decrypted file may be corrupted.")

        # Save decryption metadata
        decryption_metadata = {
            'original_filename': file_path.name,
            'decrypted_filename': decrypted_path.name,
            'decrypted_size': decrypted_path.stat().st_size,
            'decrypted_hash': decrypted_hash,
            'decryption_date': datetime.now().isoformat(),
            'decryption_time': time.time() - start_time
        }

        # Save metadata to companion file
        decryption_metadata_path = decrypted_path.with_suffix('.decryption_metadata')
        with open(decryption_metadata_path, 'w') as meta_file:
            for key, value in decryption_metadata.items():  # type: ignore
                meta_file.write(f"{key}: {value}\n")

        # Remove encrypted file and its metadata
        os.remove(file_path)
        if metadata_path.exists():
            os.remove(metadata_path)

        # Log completion
        total_time = time.time() - start_time
        average_speed = file_size / total_time
        logger.info(f"Decryption completed successfully:")
        logger.info(f"- Decrypted file: {decrypted_path}")
        logger.info(f"- Total time: {format_time(total_time)}")
        logger.info(f"- Average speed: {format_size(average_speed)}/s")
        logger.info(f"- Decrypted file hash (SHA-256): {decrypted_hash}")

        return decrypted_path

    except Exception as e:
        logger.error(f"Error decrypting file {file_path}: {str(e)}")
        # Clean up partial files if they exist
        if decrypted_path.exists():
            decrypted_path.unlink()
        decryption_metadata_path = decrypted_path.with_suffix('.decryption_metadata')
        if decryption_metadata_path.exists():
            decryption_metadata_path.unlink()
        raise
