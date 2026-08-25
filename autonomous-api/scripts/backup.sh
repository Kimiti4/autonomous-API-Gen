#!/bin/bash
# Automated backup script for Autonomous Evolution Engine
# Creates backups of database, memory, and logs

set -e  # Exit on error

# Configuration
BACKUP_DIR="/backups/evolution-engine"
APP_DIR="/opt/evolution-engine"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
RETENTION_DAYS=30

echo "======================================"
echo "  Evolution Engine Backup Script"
echo "  Timestamp: $TIMESTAMP"
echo "======================================"

# Create backup directory
mkdir -p $BACKUP_DIR

# Backup SQLite database
echo ""
echo "[1/4] Backing up database..."
if [ -f "$APP_DIR/data/evolution.db" ]; then
    cp $APP_DIR/data/evolution.db $BACKUP_DIR/evolution_db_$TIMESTAMP.db
    echo "✅ Database backed up"
else
    echo "⚠️  Database file not found, skipping"
fi

# Backup memory (elite learning data)
echo ""
echo "[2/4] Backing up memory..."
if [ -f "$APP_DIR/memory.json" ]; then
    cp $APP_DIR/memory.json $BACKUP_DIR/memory_$TIMESTAMP.json
    echo "✅ Memory backed up"
else
    echo "⚠️  Memory file not found, skipping"
fi

# Backup logs (last 7 days)
echo ""
echo "[3/4] Backing up logs..."
if [ -d "$APP_DIR/logs" ]; then
    tar -czf $BACKUP_DIR/logs_$TIMESTAMP.tar.gz -C $APP_DIR logs/
    echo "✅ Logs backed up"
else
    echo "⚠️  Logs directory not found, skipping"
fi

# Backup configuration
echo ""
echo "[4/4] Backing up configuration..."
if [ -f "$APP_DIR/.env" ]; then
    cp $APP_DIR/.env $BACKUP_DIR/env_$TIMESTAMP
    echo "✅ Configuration backed up"
else
    echo "⚠️  .env file not found, skipping"
fi

# Clean old backups
echo ""
echo "Cleaning backups older than $RETENTION_DAYS days..."
find $BACKUP_DIR -type f -mtime +$RETENTION_DAYS -delete
echo "✅ Old backups cleaned"

# Show backup summary
echo ""
echo "======================================"
echo "  Backup Summary"
echo "======================================"
echo "Backup location: $BACKUP_DIR"
echo "Files created:"
ls -lh $BACKUP_DIR/*$TIMESTAMP* 2>/dev/null || echo "No files found"
echo ""
echo "Total backup size:"
du -sh $BACKUP_DIR | cut -f1
echo ""
echo "✅ Backup completed successfully!"
