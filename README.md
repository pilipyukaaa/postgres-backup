# Postgres Backup

## Overview

Postgres Backup is a simple Python application designed to facilitate the backup of PostgreSQL databases. This tool aims to provide an easy-to-use interface for creating and managing backups, ensuring that your data is safe and recoverable.

## Features

- **Database Backup**: Create backups of your PostgreSQL databases. encrypt them and upload in s3.
- **Easy Configuration**: Simple configuration options to set up your database connection.
- **Automated Backups**: Schedule backups to run at specified intervals (with k8s cronjob on ansible).

## Requirements

- Docker builder

## Installation

1. Clone the repository:
   ```bash
   docker build -t docker build -t postgres-backup/backup:1.0.0 -f Dockerfile-backup .
   docker build -t docker build -t postgres-backup/restore:1.0.0 -f Dockerfile-restore .
   ```

2. Install the required Python packages:
   ```bash
   ansible-playbook ansible/playbook/backup.yml # for backup
   ansible-playbook ansible/playbook/restore.yml # for restore
   ```

3. Configure your database connection settings in the configuration file (details to be provided).

