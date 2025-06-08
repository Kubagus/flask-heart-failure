from flask import render_template, request, redirect, url_for, session, flash
import os
import pandas as pd
from werkzeug.security import generate_password_hash, check_password_hash
from db.database import get_db_connection
from auth.middleware import login_required, admin_required
import joblib
import json

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

    @app.route('/history')
    @login_required
    def history():
        conn = get_db_connection()
        # Get predictions for the current user
        predictions = conn.execute(
            """SELECT p.*, r.* 
            FROM predictions p 
            JOIN risk_by_algorithm r ON p.id = r.prediction_id 
            WHERE p.user_id = ? 
            ORDER BY p.created_at DESC""",
            (session['user_id'],)
        ).fetchall()
        conn.close()
        
        # Process predictions to make them more readable
        processed_predictions = []
        for pred in predictions:
            processed_pred = {
                'id': pred['id'],
                'created_at': pred['created_at'],
                'data': {
                    'age': pred['age'],
                    'sex': pred['sex'],
                    'chestpaintype': pred['chestpaintype'],
                    'restingbp': pred['restingbp'],
                    'cholesterol': pred['cholesterol'],
                    'fastingbs': pred['fastingbs'],
                    'restingecg': pred['restingecg'],
                    'maxhr': pred['maxhr'],
                    'exerciseangina': pred['exerciseangina'],
                    'oldpeak': pred['oldpeak'],
                    'stslope': pred['stslope']
                },
                'result': {
                    'decision_tree': pred['decision_tree'],
                    'decision_tree_risk': pred['decision_tree_risk'],
                    'random_forest': pred['random_forest'],
                    'random_forest_risk': pred['random_forest_risk'],
                    'xgboost': pred['xgboost'],
                    'xgboost_risk': pred['xgboost_risk']
                },
                'risk_level': 'High' if any(risk == 'Risiko tinggi terkena gagal jantung' for risk in [
                    pred['decision_tree_risk'],
                    pred['random_forest_risk'],
                    pred['xgboost_risk']
                ]) else 'Low'
            }
            processed_predictions.append(processed_pred)
        
        return render_template('history.html', predictions=processed_predictions)
