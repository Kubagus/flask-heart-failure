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
            'SELECT * FROM prediction_history WHERE user_id = ? ORDER BY created_at DESC',
            (session['user_id'],)
        ).fetchall()
        conn.close()
        
        # Process predictions to make them more readable
        processed_predictions = []
        for pred in predictions:
            prediction_data = json.loads(pred['prediction_data'])
            prediction_result = json.loads(pred['prediction_result'])
            
            processed_pred = {
                'id': pred['id'],
                'created_at': pred['created_at'],
                'data': prediction_data,
                'result': prediction_result,
                'risk_level': 'High' if any(risk == 'Risiko tinggi terkena gagal jantung' for risk in [
                    prediction_result.get('decision_tree_risk', ''),
                    prediction_result.get('random_forest_risk', ''),
                    prediction_result.get('xgboost_risk', '')
                ]) else 'Low'
            }
            processed_predictions.append(processed_pred)
        
        return render_template('history.html', predictions=processed_predictions)
