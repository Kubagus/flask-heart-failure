from flask import Flask, render_template, request, redirect, url_for, session, flash
from predict_route import predict_bp
import pandas as pd
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import os
from functools import wraps
from dotenv import load_dotenv
load_dotenv()
from db.database import init_db, get_db_connection
from auth.middleware import login_required, admin_required
from flask import render_template, request, redirect, url_for, session, flash
import os
from werkzeug.security import generate_password_hash, check_password_hash
from db.database import get_db_connection
from auth.middleware import login_required, admin_required
import joblib
init_db()

def authRoutes(app):
    
    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if 'user_id' in session:
            return redirect(url_for('home'))

        if request.method == 'POST':
            username = request.form.get('username')
            password = request.form.get('password')
            remember = request.form.get('remember')

            user = get_user_by_username(username or '') or get_user_by_email(username or '')

            if user and check_password_hash(user['password'], password):
                session['user_id'] = user['id']
                session['username'] = user['username']
                session['full_name'] = user['full_name']
                session['role'] = user['role']

                if remember:
                    session.permanent = True

                flash(f'Welcome back, {user["full_name"]}!', 'success')
                
                if user['role'] == 'admin':
                    return redirect(url_for('admin_dashboard'))
                return redirect(url_for('home'))
            else:
                flash('Invalid username/email or password!', 'danger')

        return render_template('login.html')

    @app.route('/register', methods=['GET', 'POST'])
    def register():
        if 'user_id' in session:
            return redirect(url_for('home'))

        if request.method == 'POST':
            username = request.form.get('username')
            email = request.form.get('email')
            password = request.form.get('password')
            confirm_password = request.form.get('confirmPassword')
            full_name = request.form.get('name')

            # Validation
            if not all([username, email, password, confirm_password, full_name]):
                flash('All fields are required!', 'danger')
                return redirect(url_for('register'))

            if password != confirm_password:
                flash('Passwords do not match!', 'danger')
                return redirect(url_for('register'))

            if len(password) < 6:
                flash('Password must be at least 6 characters!', 'danger')
                return redirect(url_for('register'))

            if get_user_by_username(username):
                flash('Username already exists!', 'danger')
                return redirect(url_for('register'))

            if get_user_by_email(email):
                flash('Email already registered!', 'danger')
                return redirect(url_for('register'))

            if create_user(username, email, password, full_name):
                flash('Registration successful! Please login.', 'success')
                return redirect(url_for('login'))
            else:
                flash('Registration failed! Please try again.', 'danger')

        return render_template('register.html')

    @app.route('/logout')
    @login_required
    def logout():
        flash(f'Goodbye, {session.get("full_name")}!', 'info')
        session.clear()
        return redirect(url_for('login'))

    # Helper functions
    def create_user(username, email, password, full_name):
        conn = get_db_connection()
        try:
            conn.execute(
                "INSERT INTO users (username, email, password, full_name, role) VALUES (?, ?, ?, ?, 'patient')",
                (username, email, generate_password_hash(password), full_name)
            )
            conn.commit()
            return True
        except sqlite3.IntegrityError as e:
            print(f"Database error: {e}")
            return False
        finally:
            conn.close()

    def get_user_by_username(username):
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        conn.close()
        return user

    def get_user_by_email(email):
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
        conn.close()
        return user
