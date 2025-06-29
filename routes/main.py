from flask import render_template, request, redirect, url_for, session, flash, send_file
import os
import pandas as pd
from werkzeug.security import generate_password_hash, check_password_hash
from db.database import get_db_connection, get_user_predictions
from auth.middleware import login_required, admin_required
import joblib
import json
import io
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from datetime import datetime

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
        # Get user info from database
        user = conn.execute('SELECT full_name FROM users WHERE id = ?', (session['user_id'],)).fetchone()
        
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
        
        return render_template('history.html', predictions=processed_predictions, user_full_name=user['full_name'])

    @app.route('/print_user_history')
    def print_user_history():
        user_id = session.get('user_id')
        predictions = get_user_predictions(user_id=user_id)
        return generate_user_history_pdf(predictions, "Prediction History")

    @app.route('/print_user_history_by_date_range')
    def print_user_history_by_date_range():
        user_id = session.get('user_id')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        predictions = get_user_predictions(user_id=user_id, start_date=start_date, end_date=end_date)
        return generate_user_history_pdf(predictions, f"Prediction History {start_date} to {end_date}")

def generate_user_history_pdf(predictions, title_text):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    elements = []
    title = Paragraph(title_text, styles['Title'])
    elements.append(title)
    elements.append(Spacer(1, 20))
    table_data = [['Date', 'Risk Level']]
    for pred in predictions:
        # Ambil risk level dari salah satu model, misal random_forest_risk
        risk = pred['random_forest_risk'] if 'random_forest_risk' in pred.keys() else pred['decision_tree_risk']
        table_data.append([
            str(pred['created_at']),
            risk
        ])
    table = Table(table_data, colWidths=[150, 250])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    elements.append(table)
    doc.build(elements)
    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name='prediction_history.pdf', mimetype='application/pdf')
