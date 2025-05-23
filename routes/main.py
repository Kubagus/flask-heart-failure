from flask import render_template, request, redirect, url_for, session, flash
import os
import pandas as pd
from werkzeug.security import generate_password_hash, check_password_hash
from db.database import get_db_connection
from auth.middleware import login_required, admin_required
import joblib

def main(app):
    @app.route('/')
    def home():
        df = pd.read_csv('heart.csv')
        data = df.head(10).values.tolist()
        return render_template('index.html', 
                            data=data)

    @app.route('/prediksi')
    @login_required
    def prediksi():
        return render_template('prediksi.html')
