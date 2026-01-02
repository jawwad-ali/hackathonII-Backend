"""Database migration: Add due_date, priority, and tags columns to todos table.

This migration adds the following columns to the todos table:
- due_date: TIMESTAMP (optional) - when the todo is due
- priority: VARCHAR(10) (default 'medium') - priority level (low/medium/high)
- tags: JSON (optional) - list of category tags

Run this migration ONCE before using the updated create_todo tool.
"""

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def run_migration():
    """Execute the database migration to add new columns."""

    # Get database URL from environment
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise ValueError("DATABASE_URL environment variable not set")

    print("Connecting to database...")
    conn = psycopg2.connect(database_url)
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cursor = conn.cursor()

    try:
        print("Starting migration: Add due_date, priority, and tags columns...")

        # Check if columns already exist
        cursor.execute("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'todos'
            AND column_name IN ('due_date', 'priority', 'tags')
        """)
        existing_columns = {row[0] for row in cursor.fetchall()}

        # Add due_date column if it doesn't exist
        if 'due_date' not in existing_columns:
            print("Adding due_date column...")
            cursor.execute("""
                ALTER TABLE todos
                ADD COLUMN due_date TIMESTAMP WITH TIME ZONE
            """)

            # Create index on due_date for better query performance
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_todos_due_date
                ON todos(due_date)
            """)
            print("[OK] Added due_date column with index")
        else:
            print("[OK] due_date column already exists, skipping")

        # Add priority column if it doesn't exist
        if 'priority' not in existing_columns:
            print("Adding priority column...")
            cursor.execute("""
                ALTER TABLE todos
                ADD COLUMN priority VARCHAR(10) NOT NULL DEFAULT 'medium'
            """)

            # Create index on priority for better query performance
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_todos_priority
                ON todos(priority)
            """)
            print("[OK] Added priority column with index (default: 'medium')")
        else:
            print("[OK] priority column already exists, skipping")

        # Add tags column if it doesn't exist
        if 'tags' not in existing_columns:
            print("Adding tags column...")
            cursor.execute("""
                ALTER TABLE todos
                ADD COLUMN tags JSON
            """)
            print("[OK] Added tags column (JSON type)")
        else:
            print("[OK] tags column already exists, skipping")

        print("\n[SUCCESS] Migration completed successfully!")
        print("\nNew schema:")
        print("  - due_date: TIMESTAMP WITH TIME ZONE (nullable)")
        print("  - priority: VARCHAR(10) NOT NULL DEFAULT 'medium'")
        print("  - tags: JSON (nullable)")

    except Exception as e:
        print(f"\n[ERROR] Migration failed: {e}")
        raise

    finally:
        cursor.close()
        conn.close()
        print("\nDatabase connection closed.")


if __name__ == "__main__":
    print("=" * 60)
    print("Database Migration Script")
    print("Adding due_date, priority, and tags columns to todos table")
    print("=" * 60)
    print()

    try:
        run_migration()
    except Exception as e:
        print(f"\nFatal error: {e}")
        exit(1)
