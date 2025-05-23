import sqlite3
from werkzeug.security import generate_password_hash
import json
from datetime import datetime

def init_db():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            full_name TEXT,
            role TEXT NOT NULL DEFAULT 'patient',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS prediction_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            prediction_data TEXT NOT NULL,
            prediction_result TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')

    # Buat admin default
    cursor.execute("SELECT * FROM users WHERE role='admin'")
    if not cursor.fetchone():
        cursor.execute(
            "INSERT INTO users (username, email, password, full_name, role) VALUES (?, ?, ?, ?, ?)",
            ('admin', 'admin@example.com', generate_password_hash('admin123'), 'Admin User', 'admin')
        )

    conn.commit()
    conn.close()

def get_db_connection():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

def save_prediction(user_id, prediction_data, prediction_result):
    conn = get_db_connection()
    try:
        conn.execute(
            "INSERT INTO prediction_history (user_id, prediction_data, prediction_result) VALUES (?, ?, ?)",
            (user_id, json.dumps(prediction_data), json.dumps(prediction_result))
        )
        conn.commit()
        return True
    except Exception as e:
        print(f"Error saving prediction: {e}")
        return False
    finally:
        conn.close()

def get_user_predictions(user_id=None):
    conn = get_db_connection()
    try:
        if user_id:
            predictions = conn.execute(
                "SELECT ph.*, u.username, u.full_name FROM prediction_history ph JOIN users u ON ph.user_id = u.id WHERE ph.user_id = ? ORDER BY ph.created_at DESC",
                (user_id,)
            ).fetchall()
        else:
            predictions = conn.execute(
                "SELECT ph.*, u.username, u.full_name FROM prediction_history ph JOIN users u ON ph.user_id = u.id ORDER BY ph.created_at DESC"
            ).fetchall()
        return predictions
    finally:
        conn.close()
