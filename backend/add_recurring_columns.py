import asyncio
import os
from sqlalchemy import text
from database import engine

async def run_migration():
    print("Starting migration...")
    async with engine.begin() as conn:
        print("Adding is_recurring column...")
        try:
            await conn.execute(text("ALTER TABLE financial_entries ADD COLUMN is_recurring INTEGER NOT NULL DEFAULT 0;"))
            print("Successfully added is_recurring")
        except Exception as e:
            print(f"Error (maybe it already exists?): {e}")
            
        print("Adding recurrence_interval column...")
        try:
            await conn.execute(text("ALTER TABLE financial_entries ADD COLUMN recurrence_interval VARCHAR(50);"))
            print("Successfully added recurrence_interval")
        except Exception as e:
            print(f"Error (maybe it already exists?): {e}")

if __name__ == "__main__":
    asyncio.run(run_migration())
