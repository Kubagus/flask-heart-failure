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
