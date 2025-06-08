from flask import Flask, render_template, request, redirect, url_for, session, flash
from predict_route import predict_bp
import pandas as pd
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import os
from functools import wraps
from dotenv import load_dotenv
import json
from datetime import datetime
from flask_wtf.csrf import CSRFProtect
from routes.main import main
from routes.authRoutes import authRoutes
from routes.adminRoute import adminRoute
from db.database import init_db, get_db_connection
from auth.middleware import login_required, admin_required
from routes.loadModel import loadModel
import logging

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = "RAHASIA"  # Ganti dengan secret key yang aman
app.config['WTF_CSRF_ENABLED'] = True
app.config['WTF_CSRF_SECRET_KEY'] = "RAHASIA"  # Ganti dengan secret key yang aman
csrf = CSRFProtect(app)

# Add fromjson filter
@app.template_filter('fromjson')
def fromjson_filter(value):
    return json.loads(value)

# Load ML modelsFUNGSI PREDIKSI TIDFAK NISA
loadModel(app)

app.register_blueprint(predict_bp)

# Initialize routes
main(app)
authRoutes(app)
adminRoute(app)

# Initialize database
init_db()

if __name__ == '__main__':
    app.run(host="0.0.0.0", debug=True)