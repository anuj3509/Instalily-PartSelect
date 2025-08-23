#!/usr/bin/env python3
"""
Database Schema Migration Script

This script migrates the existing database to support the new PartSelect parts schema.
It backs up existing data and recreates the database with the updated schema.
"""

import sqlite3
import json
import logging
from pathlib import Path
import shutil
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def backup_database(db_path: str) -> str:
    """Create a backup of the existing database"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"{db_path}.backup_{timestamp}"
    
    if Path(db_path).exists():
        shutil.copy2(db_path, backup_path)
        logger.info(f"Database backed up to: {backup_path}")
        return backup_path
    else:
        logger.info("No existing database found, no backup needed")
        return None

def create_new_database(db_path: str, schema_path: str):
    """Create new database with updated schema"""
    # Remove existing database
    if Path(db_path).exists():
        Path(db_path).unlink()
        logger.info(f"Removed existing database: {db_path}")
    
    # Create new database with schema
    conn = sqlite3.connect(db_path)
    
    # Read and execute schema
    with open(schema_path, 'r') as f:
        schema_sql = f.read()
    
    conn.executescript(schema_sql)
    conn.commit()
    conn.close()
    
    logger.info(f"New database created with updated schema: {db_path}")

def migrate_existing_data(backup_path: str, new_db_path: str):
    """Migrate existing data from backup to new database"""
    if not backup_path or not Path(backup_path).exists():
        logger.info("No backup found, skipping data migration")
        return
    
    # Connect to both databases
    backup_conn = sqlite3.connect(backup_path)
    backup_conn.row_factory = sqlite3.Row
    
    new_conn = sqlite3.connect(new_db_path)
    
    try:
        # Migrate existing parts (with old schema)
        backup_cursor = backup_conn.execute("SELECT * FROM parts")
        existing_parts = backup_cursor.fetchall()
        
        logger.info(f"Migrating {len(existing_parts)} existing parts...")
        
        for part in existing_parts:
            # Map old schema to new schema
            new_conn.execute("""
                INSERT OR REPLACE INTO parts 
                (part_number, name, description, price, brand, category, 
                 image_url, product_url, installation_guide, install_video_url, 
                 in_stock, specifications, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, [
                part['part_number'],
                part['name'],
                part['description'],
                part['price'],
                part['brand'],
                part['category'],
                part['image_url'],
                part['product_url'],
                part['installation_guide'],
                part['install_video_url'],
                part['in_stock'],
                part['specifications'],
                part['created_at'],
                part['updated_at']
            ])
        
        # Migrate other tables
        tables_to_migrate = ['part_compatibility', 'repairs', 'blogs', 'part_categories']
        
        for table in tables_to_migrate:
            try:
                # Check if table exists in backup
                backup_cursor = backup_conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name=?", 
                    [table]
                )
                if not backup_cursor.fetchone():
                    logger.info(f"Table {table} not found in backup, skipping")
                    continue
                
                # Get all data from backup table
                backup_cursor = backup_conn.execute(f"SELECT * FROM {table}")
                rows = backup_cursor.fetchall()
                
                if rows:
                    # Get column names
                    columns = [description[0] for description in backup_cursor.description]
                    placeholders = ', '.join(['?' for _ in columns])
                    columns_str = ', '.join(columns)
                    
                    # Insert data into new database
                    for row in rows:
                        new_conn.execute(
                            f"INSERT OR REPLACE INTO {table} ({columns_str}) VALUES ({placeholders})",
                            list(row)
                        )
                    
                    logger.info(f"Migrated {len(rows)} records from {table}")
                
            except Exception as e:
                logger.warning(f"Error migrating table {table}: {e}")
        
        new_conn.commit()
        logger.info("Data migration completed successfully")
        
    except Exception as e:
        logger.error(f"Error during data migration: {e}")
        new_conn.rollback()
        raise
    finally:
        backup_conn.close()
        new_conn.close()

def main():
    """Main migration function"""
    try:
        logger.info("Starting database schema migration...")
        
        # Paths
        db_path = "partselect.db"
        schema_path = "schema.sql"
        
        # Step 1: Backup existing database
        backup_path = backup_database(db_path)
        
        # Step 2: Create new database with updated schema
        create_new_database(db_path, schema_path)
        
        # Step 3: Migrate existing data
        migrate_existing_data(backup_path, db_path)
        
        logger.info("✅ Database schema migration completed successfully!")
        logger.info("You can now run the PartSelect parts import script.")
        
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        raise

if __name__ == "__main__":
    main()
