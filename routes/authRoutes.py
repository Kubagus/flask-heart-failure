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
    
    @app.route('/logout')
    
    @login_required
    def logout():
        flash(f'Goodbye, {session.get("full_name")}!', 'info')
        session.clear()
        return redirect(url_for('login'))
