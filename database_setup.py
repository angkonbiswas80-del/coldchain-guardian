import sqlite3
import bcrypt

def init_db():
    # Connect with a generous timeout to prevent locking conflicts
    conn = sqlite3.connect("cold_chain_iot.db", timeout=30)
    conn.execute("PRAGMA journal_mode=WAL;")
    cursor = conn.cursor()
    
    # Create the authenticated users table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password_hash TEXT,
            role TEXT
        )
    """)
    
    # Create the telemetry engine ingestion table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS telemetry_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            device_id TEXT,
            temperature REAL,
            vibration REAL,
            current_draw REAL,
            latitude REAL,
            longitude REAL,
            status TEXT
        )
    """)
    
    # Defensive check: Only insert the admin user if it does not already exist
    cursor.execute("SELECT * FROM users WHERE username = ?", ("admin",))
    if not cursor.fetchone():
        hashed = bcrypt.hashpw("admin123".encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        cursor.execute("INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)", 
                       ("admin", hashed, "Logistics Manager"))
        conn.commit()
        print("[SUCCESS] Database schema initialized and default admin user created successfully!")
    else:
        print("[INFO] Database schema verified. Default admin profile already exists. Skipping insertion.")
        
    conn.close()

if __name__ == "__main__":
    init_db()