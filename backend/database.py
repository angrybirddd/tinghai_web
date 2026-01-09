import sqlite3
import os

DB_PATH = 'tinghai.db'

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Create users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password_hash TEXT
        )
    ''')
    
    # Check if password_hash column exists (for migration)
    cursor.execute("PRAGMA table_info(users)")
    columns = [col[1] for col in cursor.fetchall()]
    if 'password_hash' not in columns:
        print("[INFO] Migrating users table: adding password_hash column")
        cursor.execute('ALTER TABLE users ADD COLUMN password_hash TEXT')

    # Create groups table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS groups (
            id TEXT PRIMARY KEY,
            username TEXT NOT NULL,
            name TEXT NOT NULL,
            prompt TEXT,
            FOREIGN KEY (username) REFERENCES users (username)
        )
    ''')
    
    conn.commit()
    conn.close()
    print(f"[INFO] Database initialized at {DB_PATH}")

def add_user(username, password_hash=None):
    """
    Register a new user.
    Returns True if created, False if already exists.
    """
    conn = get_db_connection()
    try:
        # Check if user exists
        existing = conn.execute('SELECT username FROM users WHERE username = ?', (username,)).fetchone()
        if existing:
            return False
            
        conn.execute('INSERT INTO users (username, password_hash) VALUES (?, ?)', (username, password_hash))
        conn.commit()
        return True
    finally:
        conn.close()

def verify_user(username, password_hash):
    """
    Verify username and password.
    Returns:
      - True: valid credentials
      - False: invalid password
      - None: user does not exist
    """
    conn = get_db_connection()
    try:
        user = conn.execute('SELECT password_hash FROM users WHERE username = ?', (username,)).fetchone()
        if not user:
            return None # User not found
            
        stored_hash = user['password_hash']
        
        # If no password stored yet (migration scenario), we might update it?
        # Or require it to match if provided. 
        # Policy: If stored_hash is None, accept and update? 
        # Let's be strict: if migration happened, old users have NULL password.
        # We should allow them to claim it on first login? 
        # Let's say: if stored is NULL, update it.
        if stored_hash is None:
            conn.execute('UPDATE users SET password_hash = ? WHERE username = ?', (password_hash, username))
            conn.commit()
            return True
            
        return stored_hash == password_hash
    finally:
        conn.close()

def get_groups(username):
    conn = get_db_connection()
    groups = conn.execute('SELECT * FROM groups WHERE username = ?', (username,)).fetchall()
    conn.close()
    return [dict(g) for g in groups]

def add_group(group_id, username, name, prompt):
    conn = get_db_connection()
    try:
        conn.execute('INSERT INTO groups (id, username, name, prompt) VALUES (?, ?, ?, ?)',
                     (group_id, username, name, prompt))
        conn.commit()
    finally:
        conn.close()

def update_group(group_id, username, name, prompt):
    conn = get_db_connection()
    try:
        conn.execute('UPDATE groups SET name = ?, prompt = ? WHERE id = ? AND username = ?',
                     (name, prompt, group_id, username))
        conn.commit()
    finally:
        conn.close()

def delete_group(group_id, username):
    conn = get_db_connection()
    try:
        conn.execute('DELETE FROM groups WHERE id = ? AND username = ?', (group_id, username))
        conn.commit()
    finally:
        conn.close()
