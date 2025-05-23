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
init_db()
from routes.route import register_routes
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY") 
app.register_blueprint(predict_bp)

register_routes(app)

if __name__ == '__main__':
    app.run(host="0.0.0.0", debug=True)