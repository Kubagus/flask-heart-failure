from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, session
from db.database import get_db_connection, get_user_predictions
from auth.middleware import login_required, admin_required
from datetime import datetime

prediction_bp = Blueprint('prediction', __name__)

@prediction_bp.route('/predictions')
@login_required
def list_predictions():
    conn = get_db_connection()
    try:
        predictions = get_user_predictions(session.get('user_id'))
        return render_template('predictions/list.html', predictions=predictions)
    finally:
        conn.close()

@prediction_bp.route('/predictions/<int:id>')
@login_required
def view_prediction(id):
    conn = get_db_connection()
    try:
        prediction = conn.execute(
            """SELECT p.*, u.username, u.full_name, r.* 
            FROM predictions p 
            JOIN users u ON p.user_id = u.id 
            JOIN risk_by_algorithm r ON p.id = r.prediction_id 
            WHERE p.id = ? AND p.user_id = ?""",
            (id, session.get('user_id'))
        ).fetchone()
        
        if not prediction:
            flash('Prediksi tidak ditemukan', 'error')
            return redirect(url_for('prediction.list_predictions'))
            
        return render_template('predictions/view.html', prediction=prediction)
    finally:
        conn.close()

@prediction_bp.route('/predictions/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit_prediction(id):
    conn = get_db_connection()
    try:
        # Check if prediction exists and belongs to user
        prediction = conn.execute(
            """SELECT p.*, u.username, u.full_name, r.* 
            FROM predictions p 
            JOIN users u ON p.user_id = u.id 
            JOIN risk_by_algorithm r ON p.id = r.prediction_id 
            WHERE p.id = ? AND p.user_id = ?""",
            (id, session.get('user_id'))
        ).fetchone()
        
        if not prediction:
            flash('Prediksi tidak ditemukan', 'error')
            return redirect(url_for('prediction.list_predictions'))

        if request.method == 'POST':
            try:
                conn.execute(
                    """UPDATE predictions SET 
                    age = ?, sex = ?, chestpaintype = ?, restingbp = ?,
                    cholesterol = ?, fastingbs = ?, restingecg = ?,
                    maxhr = ?, exerciseangina = ?, oldpeak = ?, stslope = ?
                    WHERE id = ? AND user_id = ?""",
                    (
                        request.form['age'],
                        request.form['sex'],
                        request.form['chestpaintype'],
                        request.form['restingbp'],
                        request.form['cholesterol'],
                        request.form['fastingbs'],
                        request.form['restingecg'],
                        request.form['maxhr'],
                        request.form['exerciseangina'],
                        request.form['oldpeak'],
                        request.form['stslope'],
                        id,
                        session.get('user_id')
                    )
                )
                conn.commit()
                flash('Prediksi berhasil diperbarui', 'success')
                return redirect(url_for('prediction.view_prediction', id=id))
            except Exception as e:
                flash(f'Gagal memperbarui prediksi: {str(e)}', 'error')
        
        return render_template('predictions/edit.html', prediction=prediction)
    finally:
        conn.close()

@prediction_bp.route('/predictions/<int:id>/delete', methods=['POST'])
@login_required
def delete_prediction(id):
    conn = get_db_connection()
    try:
        # Check if prediction exists and belongs to user
        prediction = conn.execute(
            'SELECT * FROM predictions WHERE id = ? AND user_id = ?',
            (id, session.get('user_id'))
        ).fetchone()
        
        if not prediction:
            flash('Prediksi tidak ditemukan', 'error')
            return redirect(url_for('prediction.list_predictions'))

        # Delete from risk_by_algorithm first due to foreign key constraint
        conn.execute('DELETE FROM risk_by_algorithm WHERE prediction_id = ?', (id,))
        # Then delete from predictions
        conn.execute('DELETE FROM predictions WHERE id = ? AND user_id = ?', (id, session.get('user_id')))
        conn.commit()
        flash('Prediksi berhasil dihapus', 'success')
    except Exception as e:
        flash(f'Gagal menghapus prediksi: {str(e)}', 'error')
    finally:
        conn.close()
    
    return redirect(url_for('prediction.list_predictions')) 