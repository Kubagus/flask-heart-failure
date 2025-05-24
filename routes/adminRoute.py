from flask import render_template, request, redirect, url_for, session, flash, jsonify, send_file, Blueprint
import pandas as pd
import os
from werkzeug.security import generate_password_hash, check_password_hash
from db.database import get_db_connection, get_user_predictions
from auth.middleware import login_required, admin_required
import joblib
import json
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
import io

admin_bp = Blueprint('admin', __name__)

def adminRoute(app):
# Admin dashboard
    @app.route('/admin/dashboard')
    @admin_required
    def admin_dashboard():
        conn = get_db_connection()
        users = conn.execute('SELECT * FROM users WHERE role != "admin"').fetchall()
        predictions = get_user_predictions()
        conn.close()

        # Calculate statistics
        total_users = len(users)
        total_predictions = len(predictions)
        
        # Count high risk predictions
        high_risk_predictions = 0
        for pred in predictions:
            result = json.loads(pred['prediction_result'])
            # Count as high risk if any of the models predict high risk
            if any(risk == 'Risiko tinggi terkena gagal jantung' for risk in [
                result.get('decision_tree_risk', ''),
                result.get('random_forest_risk', ''),
                result.get('xgboost_risk', '')
            ]):
                high_risk_predictions += 1

        # Count today's predictions
        today = datetime.now().date()
        today_predictions = sum(1 for pred in predictions 
                              if datetime.strptime(pred['created_at'], '%Y-%m-%d %H:%M:%S').date() == today)

        return render_template('admin/dashboard.html',
                             total_users=total_users,
                             total_predictions=total_predictions,
                             high_risk_predictions=high_risk_predictions,
                             today_predictions=today_predictions,
                             recent_predictions=predictions[:5])

    @app.route('/admin/users')
    @admin_required
    def admin_users():
        conn = get_db_connection()
        admin_users = conn.execute('SELECT * FROM users WHERE role = "admin"').fetchall()
        regular_users = conn.execute('SELECT * FROM users WHERE role != "admin"').fetchall()
        conn.close()
        return render_template('admin/users.html', admin_users=admin_users, regular_users=regular_users)

    @app.route('/admin/users/create', methods=['GET', 'POST'])
    @admin_required
    def create_user():
        if request.method == 'POST':
            username = request.form.get('username')
            email = request.form.get('email')
            password = request.form.get('password')
            full_name = request.form.get('full_name')
            role = request.form.get('role', 'patient')

            conn = get_db_connection()
            try:
                conn.execute(
                    "INSERT INTO users (username, email, password, full_name, role) VALUES (?, ?, ?, ?, ?)",
                    (username, email, generate_password_hash(password), full_name, role)
                )
                conn.commit()
                flash('User created successfully!', 'success')
                return redirect(url_for('admin_users'))
            except Exception as e:
                flash(f'Error creating user: {str(e)}', 'danger')
            finally:
                conn.close()
        return render_template('admin/create_user.html')

    @app.route('/admin/users/<int:user_id>/edit', methods=['GET', 'POST'])
    @admin_required
    def edit_user(user_id):
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
        
        if request.method == 'POST':
            username = request.form.get('username')
            email = request.form.get('email')
            full_name = request.form.get('full_name')
            role = request.form.get('role')
            password = request.form.get('password')

            try:
                if password:
                    conn.execute(
                        "UPDATE users SET username = ?, email = ?, password = ?, full_name = ?, role = ? WHERE id = ?",
                        (username, email, generate_password_hash(password), full_name, role, user_id)
                    )
                else:
                    conn.execute(
                        "UPDATE users SET username = ?, email = ?, full_name = ?, role = ? WHERE id = ?",
                        (username, email, full_name, role, user_id)
                    )
                conn.commit()
                flash('User updated successfully!', 'success')
                return redirect(url_for('admin_users'))
            except Exception as e:
                flash(f'Error updating user: {str(e)}', 'danger')
            finally:
                conn.close()
        return render_template('admin/edit_user.html', user=user)

    @app.route('/admin/users/<int:user_id>/delete', methods=['POST'])
    @admin_required
    def delete_user(user_id):
        conn = get_db_connection()
        try:
            conn.execute('DELETE FROM users WHERE id = ?', (user_id,))
            conn.commit()
            flash('User deleted successfully!', 'success')
        except Exception as e:
            flash(f'Error deleting user: {str(e)}', 'danger')
        finally:
            conn.close()
        return redirect(url_for('admin_users'))

    @app.route('/admin/predictions')
    @admin_required
    def admin_predictions():
        predictions = get_user_predictions()
        
        # Process predictions to make them more readable
        processed_predictions = []
        for pred in predictions:
            prediction_data = json.loads(pred['prediction_data'])
            prediction_result = json.loads(pred['prediction_result'])
            
            processed_pred = {
                'id': pred['id'],
                'full_name': pred['full_name'],
                'created_at': pred['created_at'],
                'risk_level': 'High' if any(risk == 'Risiko tinggi terkena gagal jantung' for risk in [
                    prediction_result.get('decision_tree_risk', ''),
                    prediction_result.get('random_forest_risk', ''),
                    prediction_result.get('xgboost_risk', '')
                ]) else 'Low',
                'decision_tree': prediction_result.get('decision_tree', 0),
                'decision_tree_risk': prediction_result.get('decision_tree_risk', ''),
                'random_forest': prediction_result.get('random_forest', 0),
                'random_forest_risk': prediction_result.get('random_forest_risk', ''),
                'xgboost': prediction_result.get('xgboost', 0),
                'xgboost_risk': prediction_result.get('xgboost_risk', ''),
                'age': prediction_data.get('age', ''),
                'sex': prediction_data.get('sex', ''),
                'chestpaintype': prediction_data.get('chestpaintype', ''),
                'restingbp': prediction_data.get('restingbp', ''),
                'cholesterol': prediction_data.get('cholesterol', ''),
                'fastingbs': prediction_data.get('fastingbs', ''),
                'restingecg': prediction_data.get('restingecg', ''),
                'maxhr': prediction_data.get('maxhr', ''),
                'exerciseangina': prediction_data.get('exerciseangina', ''),
                'oldpeak': prediction_data.get('oldpeak', ''),
                'stslope': prediction_data.get('stslope', '')
            }
            processed_predictions.append(processed_pred)
        
        return render_template('admin/predictions.html', predictions=processed_predictions)

    @app.route('/admin/predictions/export/<format>')
    @admin_required
    def export_predictions(format):
        predictions = get_user_predictions()
        data = []
        
        for pred in predictions:
            pred_data = dict(pred)
            pred_data['prediction_data'] = json.loads(pred_data['prediction_data'])
            pred_data['prediction_result'] = json.loads(pred_data['prediction_result'])
            data.append(pred_data)

        if format == 'json':
            return jsonify(data)
        elif format == 'csv':
            df = pd.DataFrame(data)
            csv_data = df.to_csv(index=False)
            return csv_data, 200, {
                'Content-Type': 'text/csv',
                'Content-Disposition': 'attachment; filename=predictions.csv'
            }
        elif format == 'pdf':
            # Create PDF
            buffer = io.BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=letter)
            styles = getSampleStyleSheet()
            elements = []

            # Add title
            title = Paragraph("Prediction History Report", styles['Title'])
            elements.append(title)
            elements.append(Spacer(1, 20))

            # Create table data
            table_data = [['User', 'Date', 'Input Data', 'Result']]
            for pred in predictions:
                pred_data = json.loads(pred['prediction_data'])
                pred_result = json.loads(pred['prediction_result'])
                
                # Format input data
                input_data = "\n".join([f"{k}: {v}" for k, v in pred_data.items()])
                
                # Format result
                result = "\n".join([
                    f"Decision Tree: {pred_result['decision_tree']}% ({pred_result['decision_tree_risk']})",
                    f"Random Forest: {pred_result['random_forest']}% ({pred_result['random_forest_risk']})",
                    f"XGBoost: {pred_result['xgboost']}% ({pred_result['xgboost_risk']})"
                ])
                
                table_data.append([
                    pred['full_name'],
                    pred['created_at'],
                    input_data,
                    result
                ])

            # Create table
            table = Table(table_data, colWidths=[100, 100, 200, 200])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 14),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 12),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            elements.append(table)

            # Build PDF
            doc.build(elements)
            buffer.seek(0)
            return send_file(
                buffer,
                as_attachment=True,
                download_name='predictions.pdf',
                mimetype='application/pdf'
            )

    @app.route('/admin/predictions/edit/<int:prediction_id>', methods=['POST'])
    @admin_required
    def edit_prediction(prediction_id):
        conn = get_db_connection()
        try:
            prediction = conn.execute('SELECT * FROM predictions WHERE id = ?', (prediction_id,)).fetchone()
            if not prediction:
                flash('Prediction not found', 'danger')
                return redirect(url_for('admin_predictions'))

            result = request.form.get('result')
            result_data = request.form.get('result_data')

            conn.execute(
                'UPDATE predictions SET result = ?, result_data = ? WHERE id = ?',
                (result, result_data, prediction_id)
            )
            conn.commit()
            flash('Prediction updated successfully', 'success')
        except Exception as e:
            flash(f'Error updating prediction: {str(e)}', 'danger')
        finally:
            conn.close()
        return redirect(url_for('admin_predictions'))

    @app.route('/admin/predictions/delete/<int:prediction_id>', methods=['POST'])
    @admin_required
    def delete_prediction(prediction_id):
        conn = get_db_connection()
        try:
            # Check if prediction exists
            prediction = conn.execute('SELECT * FROM prediction_history WHERE id = ?', (prediction_id,)).fetchone()
            if not prediction:
                flash('Prediction not found', 'danger')
                return redirect(url_for('admin_predictions'))

            # Delete the prediction
            conn.execute('DELETE FROM prediction_history WHERE id = ?', (prediction_id,))
            conn.commit()
            flash('Prediction deleted successfully', 'success')
        except Exception as e:
            flash(f'Error deleting prediction: {str(e)}', 'danger')
        finally:
            conn.close()
        return redirect(url_for('admin_predictions'))
