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
    @app.route('/admin/dashboard')
    @admin_required
    def admin_dashboard():
        conn = get_db_connection()
        try:
            # Get total users
            total_users = conn.execute('SELECT COUNT(*) FROM users WHERE role = ?', ('patient',)).fetchone()[0]
            
            # Get total predictions
            total_predictions = conn.execute('SELECT COUNT(*) FROM predictions').fetchone()[0]
            
            # Get high risk predictions (any model risk is 'Risiko tinggi terkena gagal jantung')
            high_risk_predictions = conn.execute('''
                SELECT COUNT(*) FROM risk_by_algorithm 
                WHERE decision_tree_risk = ? OR random_forest_risk = ? OR xgboost_risk = ?
            ''', (
                'Risiko tinggi terkena gagal jantung',
                'Risiko tinggi terkena gagal jantung',
                'Risiko tinggi terkena gagal jantung',
            )).fetchone()[0]

            # Get today's predictions
            today_str = datetime.now().strftime('%Y-%m-%d')
            today_predictions = conn.execute('''
                SELECT COUNT(*) FROM predictions 
                WHERE DATE(created_at) = DATE(?)
            ''', (today_str,)).fetchone()[0]

            # Get recent predictions with user info
            recent_predictions = conn.execute(
                """SELECT p.*, u.username, u.full_name, r.* 
                FROM predictions p 
                JOIN users u ON p.user_id = u.id 
                JOIN risk_by_algorithm r ON p.id = r.prediction_id 
                ORDER BY p.created_at DESC LIMIT 5"""
            ).fetchall()

            return render_template('admin/dashboard.html',
                                total_users=total_users,
                                total_predictions=total_predictions,
                                high_risk_predictions=high_risk_predictions,
                                today_predictions=today_predictions,
                                recent_predictions=recent_predictions)
        finally:
            conn.close()

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
        return render_template('admin/predictions.html', predictions=predictions)

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
                pred_dict = dict(pred)

                # Format input data directly from pred_dict
                input_data_formatted = "<br/>".join([
                    f"<strong>Age:</strong> {pred_dict.get('age', 'N/A')}",
                    f"<strong>Sex:</strong> {pred_dict.get('sex', 'N/A')}",
                    f"<strong>Chest Pain Type:</strong> {pred_dict.get('chestpaintype', 'N/A')}",
                    f"<strong>Resting BP:</strong> {pred_dict.get('restingbp', 'N/A')}",
                    f"<strong>Cholesterol:</strong> {pred_dict.get('cholesterol', 'N/A')}",
                    f"<strong>Fasting BS:</strong> {pred_dict.get('fastingbs', 'N/A')}",
                    f"<strong>Resting ECG:</strong> {pred_dict.get('restingecg', 'N/A')}",
                    f"<strong>Max HR:</strong> {pred_dict.get('maxhr', 'N/A')}",
                    f"<strong>Exercise Angina:</strong> {pred_dict.get('exerciseangina', 'N/A')}",
                    f"<strong>Old Peak:</strong> {pred_dict.get('oldpeak', 'N/A')}",
                    f"<strong>ST Slope:</strong> {pred_dict.get('stslope', 'N/A')}"
                ])
                
                # Format result directly from pred_dict
                result_formatted = "<br/>".join([
                    f"<strong>Decision Tree:</strong> {pred_dict.get('decision_tree', 'N/A')}% ({pred_dict.get('decision_tree_risk', 'N/A')})",
                    f"<strong>Random Forest:</strong> {pred_dict.get('random_forest', 'N/A')}% ({pred_dict.get('random_forest_risk', 'N/A')})",
                    f"<strong>XGBoost:</strong> {pred_dict.get('xgboost', 'N/A')}% ({pred_dict.get('xgboost_risk', 'N/A')})"
                ])
                
                table_data.append([
                    Paragraph(pred_dict.get('full_name', 'N/A'), styles['Normal']),
                    Paragraph(str(pred_dict.get('created_at', 'N/A')), styles['Normal']),
                    Paragraph(input_data_formatted, styles['Normal']),
                    Paragraph(result_formatted, styles['Normal'])
                ])

            # Create table
            table = Table(table_data, colWidths=[80, 100, 180, 180])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 8),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('LEFTPADDING', (0,0), (-1,-1), 6),
                ('RIGHTPADDING', (0,0), (-1,-1), 6),
                ('TOPPADDING', (0,0), (-1,-1), 6),
                ('BOTTOMPADDING', (0,0), (-1,-1), 6),
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

    @app.route('/admin/predictions/delete/<int:prediction_id>', methods=['POST'])
    @admin_required
    def delete_prediction_admin(prediction_id):
        conn = get_db_connection()
        try:
            # Check if prediction exists
            prediction = conn.execute('SELECT * FROM predictions WHERE id = ?', (prediction_id,)).fetchone()
            if not prediction:
                flash('Prediksi tidak ditemukan', 'danger')
                return redirect(url_for('admin_predictions'))

            # Delete from risk_by_algorithm first due to foreign key constraint
            conn.execute('DELETE FROM risk_by_algorithm WHERE prediction_id = ?', (prediction_id,))
            # Then delete from predictions
            conn.execute('DELETE FROM predictions WHERE id = ?', (prediction_id,))
            conn.commit()
            flash('Prediksi berhasil dihapus', 'success')
        except Exception as e:
            flash(f'Gagal menghapus prediksi: {str(e)}', 'danger')
        finally:
            conn.close()
        return redirect(url_for('admin_predictions'))

    @app.route('/print_all_predictions')
    @admin_required
    def print_all_predictions():
        predictions = get_user_predictions()
        return generate_predictions_pdf(predictions, "All Predictions Report")

    @app.route('/print_predictions_by_date_range')
    @admin_required
    def print_predictions_by_date_range():
        start_date_str = request.args.get('start_date')
        end_date_str = request.args.get('end_date')

        if not start_date_str or not end_date_str:
            flash('Start date and end date are required for printing by range.', 'danger')
            return redirect(url_for('admin_predictions'))

        predictions = get_user_predictions(start_date=start_date_str, end_date=end_date_str)
        return generate_predictions_pdf(predictions, f"Predictions Report from {start_date_str} to {end_date_str}")

def generate_predictions_pdf(predictions, title_text):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    elements = []

    # Add title
    title = Paragraph(title_text, styles['Title'])
    elements.append(title)
    elements.append(Spacer(1, 20))

    # Create table data
    table_data = [['User', 'Date', 'Input Data', 'Result']]
    for pred in predictions:
        pred_dict = dict(pred)

        # Format input data directly from pred_dict
        input_data_formatted = "<br/>".join([
            f"<strong>Age:</strong> {pred_dict.get('age', 'N/A')}",
            f"<strong>Sex:</strong> {pred_dict.get('sex', 'N/A')}",
            f"<strong>Chest Pain Type:</strong> {pred_dict.get('chestpaintype', 'N/A')}",
            f"<strong>Resting BP:</strong> {pred_dict.get('restingbp', 'N/A')}",
            f"<strong>Cholesterol:</strong> {pred_dict.get('cholesterol', 'N/A')}",
            f"<strong>Fasting BS:</strong> {pred_dict.get('fastingbs', 'N/A')}",
            f"<strong>Resting ECG:</strong> {pred_dict.get('restingecg', 'N/A')}",
            f"<strong>Max HR:</strong> {pred_dict.get('maxhr', 'N/A')}",
            f"<strong>Exercise Angina:</strong> {pred_dict.get('exerciseangina', 'N/A')}",
            f"<strong>Old Peak:</strong> {pred_dict.get('oldpeak', 'N/A')}",
            f"<strong>ST Slope:</strong> {pred_dict.get('stslope', 'N/A')}"
        ])
        
        # Format result directly from pred_dict
        result_formatted = "<br/>".join([
            f"<strong>Decision Tree:</strong> {pred_dict.get('decision_tree', 'N/A')}% ({pred_dict.get('decision_tree_risk', 'N/A')})",
            f"<strong>Random Forest:</strong> {pred_dict.get('random_forest', 'N/A')}% ({pred_dict.get('random_forest_risk', 'N/A')})",
            f"<strong>XGBoost:</strong> {pred_dict.get('xgboost', 'N/A')}% ({pred_dict.get('xgboost_risk', 'N/A')})"
        ])
        
        table_data.append([
            Paragraph(pred_dict.get('full_name', 'N/A'), styles['Normal']),
            Paragraph(str(pred_dict.get('created_at', 'N/A')), styles['Normal']),
            Paragraph(input_data_formatted, styles['Normal']),
            Paragraph(result_formatted, styles['Normal'])
        ])

    # Create table
    # Increased column widths for better readability and to prevent text overflow
    table = Table(table_data, colWidths=[80, 100, 180, 180])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
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
