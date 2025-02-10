import sqlite3

DB_PATH = "data.db"

# Initialize the database
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    # Create table overlay_data
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS overlay_data (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        key TEXT UNIQUE,
        value TEXT
    )
    """)

    # Create table planets
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS planets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date DATETIME DEFAULT current_timestamp,
        raider_name TEXT NOT NULL,
        raid_size INTEGER NOT NULL,
        angle REAL NOT NULL,
        distance REAL NOT NULL
    )
    """)

    # Create table users
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        created_at DATETIME DEFAULT current_timestamp,
        twitch_id INTEGER NOT NULL,
        login TEXT NOT NULL,
        display_name TEXT NOT NULL,
        account_type TEXT,
        broadcaster_type TEXT,
        profile_image_url TEXT NOT NULL,
        account_age TEXT NOT NULL,
        follower_date DATETIME,
        subscriber_date DATETIME
    )
    """)

    conn.commit()
    conn.close()

# Save data to the database
def save_data(key, value):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO overlay_data (key, value) VALUES (?, ?)
    ON CONFLICT(key) DO UPDATE SET value = excluded.value
    """, (key, value))
    conn.commit()
    conn.close()

# Retrieve data from the database
def get_data(key):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM overlay_data WHERE key = ?", (key,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None

def save_planet(raider_name: str, raid_size: int, angle: float, distance: float):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO planets (raider_name, raid_size, angle, distance)
    VALUES (?, ?, ?, ?)
    """, (raider_name, raid_size, angle, distance))
    conn.commit()
    conn.close()

def get_planets(raider_name=None):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    if raider_name:
        cursor.execute("SELECT raider_name, raid_size, angle, distance FROM planets WHERE raider_name = ?", (raider_name,))
    else:
        cursor.execute("SELECT raider_name, raid_size, angle, distance FROM planets")
    planets = cursor.fetchall()
    conn.close()
    return planets

def clear_planets():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM planets")
    conn.commit()
    conn.close()
