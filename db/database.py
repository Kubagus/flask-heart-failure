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
        CREATE TABLE IF NOT EXISTS predictions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            age INTEGER NOT NULL,
            sex TEXT NOT NULL,
            chestpaintype TEXT NOT NULL,
            restingbp INTEGER NOT NULL,
            cholesterol INTEGER NOT NULL,
            fastingbs INTEGER NOT NULL,
            restingecg TEXT NOT NULL,
            maxhr INTEGER NOT NULL,
            exerciseangina TEXT NOT NULL,
            oldpeak REAL NOT NULL,
            stslope TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS rf_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            prediction_id INTEGER NOT NULL,
            rf_result TEXT NOT NULL,
            rf_keterangan TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (prediction_id) REFERENCES predictions (id)
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

def save_prediction(user_id, prediction_data, rf_result, rf_keterangan):
    conn = get_db_connection()
    try:
        # Insert into predictions table
        cursor = conn.execute(
            """INSERT INTO predictions (
                user_id, age, sex, chestpaintype, restingbp, cholesterol,
                fastingbs, restingecg, maxhr, exerciseangina, oldpeak, stslope
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                user_id,
                prediction_data['age'],
                prediction_data['sex'],
                prediction_data['chestpaintype'],
                prediction_data['restingbp'],
                prediction_data['cholesterol'],
                prediction_data['fastingbs'],
                prediction_data['restingecg'],
                prediction_data['maxhr'],
                prediction_data['exerciseangina'],
                prediction_data['oldpeak'],
                prediction_data['stslope']
            )
        )
        prediction_id = cursor.lastrowid

        # Insert into rf_results table
        conn.execute(
            """INSERT INTO rf_results (
                prediction_id, rf_result, rf_keterangan
            ) VALUES (?, ?, ?)""",
            (
                prediction_id,
                rf_result,
                rf_keterangan
            )
        )
        conn.commit()
        return True
    except Exception as e:
        print(f"Error saving prediction: {e}")
        return False
    finally:
        conn.close()

def get_user_predictions(user_id=None, start_date=None, end_date=None):
    conn = get_db_connection()
    try:
        query = """SELECT p.*, u.username, u.full_name, r.rf_result, r.rf_keterangan, r.created_at as rf_created_at \
                FROM predictions p \
                JOIN users u ON p.user_id = u.id \
                JOIN rf_results r ON p.id = r.prediction_id \
                """
        params = []
        conditions = []
        if user_id:
            conditions.append("p.user_id = ?")
            params.append(user_id)
        if start_date:
            conditions.append("DATE(p.created_at) >= DATE(?)")
            params.append(start_date)
        if end_date:
            conditions.append("DATE(p.created_at) <= DATE(?)")
            params.append(end_date)
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        query += " ORDER BY p.created_at DESC"
        predictions = conn.execute(query, tuple(params)).fetchall()
        return predictions
    finally:
        conn.close()

def delete_rf_result(id):
    conn = get_db_connection()
    try:
        conn.execute('DELETE FROM rf_results WHERE prediction_id = ?', (id,))
        conn.commit()
        return True
    except Exception as e:
        print(f"Error deleting rf_result: {e}")
        return False
    finally:
        conn.close()
