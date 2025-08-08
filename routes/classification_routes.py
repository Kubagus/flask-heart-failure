from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, session
from db.database import get_db_connection, get_user_classifications
from auth.middleware import login_required, admin_required
from datetime import datetime

classification_bp = Blueprint('classification', __name__)

@classification_bp.route('/classifications')
@login_required
def list_classifications():
    conn = get_db_connection()
    try:
        classifications = get_user_classifications(session.get('user_id'))
        return render_template('classifications/list.html', classifications=classifications)
    finally:
        conn.close()

@classification_bp.route('/classifications/<int:id>')
@login_required
def view_classification(id):
    conn = get_db_connection()
    try:
        classification = conn.execute(
            """SELECT p.*, u.username, u.full_name, r.rf_result, r.rf_keterangan, r.created_at as rf_created_at \
            FROM classifications p \
            JOIN users u ON p.user_id = u.id \
            JOIN rf_results r ON p.id = r.classification_id \
            WHERE p.id = ? AND p.user_id = ?""",
            (id, session.get('user_id'))
        ).fetchone()
        if not classification:
            flash('klasifikasi tidak ditemukan', 'error')
            return redirect(url_for('classification.list_classifications'))
        return render_template('classifications/view.html', classification=classification)
    finally:
        conn.close()

@classification_bp.route('/classifications/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit_classification(id):
    conn = get_db_connection()
    try:
        classification = conn.execute(
            """SELECT p.*, u.username, u.full_name, r.rf_result, r.rf_keterangan, r.created_at as rf_created_at \
            FROM classifications p \
            JOIN users u ON p.user_id = u.id \
            JOIN rf_results r ON p.id = r.classification_id \
            WHERE p.id = ? AND p.user_id = ?""",
            (id, session.get('user_id'))
        ).fetchone()
        if not classification:
            flash('klasifikasi tidak ditemukan', 'error')
            return redirect(url_for('classification.list_classifications'))
        if request.method == 'POST':
            try:
                conn.execute(
                    """UPDATE classifications SET 
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
                flash('klasifikasi berhasil diperbarui', 'success')
                return redirect(url_for('classification.view_classification', id=id))
            except Exception as e:
                flash(f'Gagal memperbarui klasifikasi: {str(e)}', 'error')
        return render_template('classifications/edit.html', classification=classification)
    finally:
        conn.close()

@classification_bp.route('/classifications/<int:id>/delete', methods=['POST'])
@login_required
def delete_classification(id):
    conn = get_db_connection()
    try:
        classification = conn.execute(
            'SELECT * FROM classifications WHERE id = ? AND user_id = ?',
            (id, session.get('user_id'))
        ).fetchone()
        if not classification:
            flash('klasifikasi tidak ditemukan', 'error')
            return redirect(url_for('classification.list_classifications'))
        # Delete from rf_results first due to foreign key constraint
        conn.execute('DELETE FROM rf_results WHERE classification_id = ?', (id,))
        # Then delete from classifications
        conn.execute('DELETE FROM classifications WHERE id = ? AND user_id = ?', (id, session.get('user_id')))
        conn.commit()
        flash('klasifikasi berhasil dihapus', 'success')
    except Exception as e:
        flash(f'Gagal menghapus klasifikasi: {str(e)}', 'error')
    finally:
        conn.close()
    return redirect(url_for('classification.list_classifications')) 