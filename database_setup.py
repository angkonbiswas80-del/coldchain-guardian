import sqlite3
import bcrypt

def init_db():
    db_name = "cold_chain_iot.db"
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    
    # Drop old user table to clear mismatched schemas
    cursor.execute("DROP TABLE IF EXISTS users")
    
    # 1. Telemetry Data Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS telemetry_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            device_id TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            temperature REAL,
            vibration REAL,
            current_draw REAL,
            latitude REAL,
            longitude REAL,
            status TEXT
        )
    """)
    
    # 2. Secure User Authentication Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL
        )
    """)
    
    # 3. Insert Fresh Admin User with exact matching column (password_hash)
    raw_password = "admin123"
    hashed = bcrypt.hashpw(raw_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    cursor.execute("INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)", 
                   ("admin", hashed, "Logistics Manager"))
    
    conn.commit()
    conn.close()
    print("[SUCCESS] Fresh Admin User Created with exact column mappings!")

if __name__ == "__main__":
    init_db()