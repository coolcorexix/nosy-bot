#!/bin/bash

# Configuration
REMOTE_USER="root"
REMOTE_HOST="178.128.212.29"
REMOTE_DB_PATH="/root/nosy-bot/nosy_bot.db"
LOCAL_BACKUP_DIR="./db_backups"
LOCAL_DB_PATH="./nosy_bot.db"

# Create backup directory if it doesn't exist
mkdir -p $LOCAL_BACKUP_DIR

# Get current timestamp for backup
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")

# Backup current local database if it exists
if [ -f $LOCAL_DB_PATH ]; then
    echo "Backing up current local database..."
    cp $LOCAL_DB_PATH "${LOCAL_BACKUP_DIR}/nosy_bot_${TIMESTAMP}.db"
fi

# Copy database from remote server
echo "Copying database from remote server..."
scp "${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_DB_PATH}" $LOCAL_DB_PATH

# Check if copy was successful
if [ $? -eq 0 ]; then
    echo "Database successfully synced!"
    echo "Local database: $LOCAL_DB_PATH"
    echo "Backup created: ${LOCAL_BACKUP_DIR}/nosy_bot_${TIMESTAMP}.db"
else
    echo "Error: Failed to sync database"
    exit 1
fi 