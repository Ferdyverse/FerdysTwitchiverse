import sqlite3
import couchdb
import datetime
import config

# SQLite connection
sqlite_db_path = "./storage/data.db"
sqlite_conn = sqlite3.connect(sqlite_db_path)
sqlite_cursor = sqlite_conn.cursor()

# CouchDB connection
couch = couchdb.Server(config.COUCHDB_URL)

# Retrieve all tables from SQLite
sqlite_cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables_to_migrate = [row[0] for row in sqlite_cursor.fetchall()]

# Fields that may contain date values
date_fields = ["created_at", "updated_at", "timestamp", "date", "last_active", "follower_date", "subscriber_date"]

def convert_to_iso(value):
    """Converts UNIX timestamps or date strings to ISO-8601 format."""
    if isinstance(value, int):  # If UNIX timestamp (seconds)
        return datetime.datetime.utcfromtimestamp(value).isoformat()
    if isinstance(value, str):
        try:
            return datetime.datetime.fromisoformat(value).isoformat()
        except ValueError:
            pass  # If not in ISO format, leave unchanged
    return value  # If not convertible, return as is

for table in tables_to_migrate:
    print(f"📥 Migrating table: {table} to CouchDB database {table}")

    # Create database for the table (if it does not exist)
    if table not in couch:
        db = couch.create(table)
    else:
        db = couch[table]

    # Retrieve data from SQLite
    sqlite_cursor.execute(f"SELECT * FROM {table}")
    columns = [desc[0] for desc in sqlite_cursor.description]  # Get column names

    for row in sqlite_cursor.fetchall():
        doc = dict(zip(columns, row))  # Create a dictionary with column names as keys
        doc["_id"] = f"{table}_{row[0]}"  # Unique ID (e.g., "viewers_123")

        # Convert date fields
        for field in date_fields:
            if field in doc:
                doc[field] = convert_to_iso(doc[field])

        # Save data to CouchDB
        try:
            db.save(doc)
            print(f"✅ Imported: {doc['_id']}")
        except couchdb.http.ResourceConflict:
            print(f"⚠️ Skipped (already exists): {doc['_id']}")

# Close connection
sqlite_conn.close()
print("🚀 Migration completed!")
