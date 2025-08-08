from flask import Blueprint, request, jsonify, current_app, session
import pandas as pd
import traceback
from db.database import save_classification
import logging

predict_bp = Blueprint('predict_bp', __name__)

@predict_bp.route('/predict', methods=['POST'])
def predict():
    try:
        if not request.is_json:
            return jsonify({'error': 'Request must be JSON'}), 400
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        data = {k.lower(): v for k, v in data.items()}
        required_fields = ['age', 'sex', 'chestpaintype', 'restingbp', 'cholesterol', 
                         'fastingbs', 'restingecg', 'maxhr', 'exerciseangina', 
                         'oldpeak', 'stslope']
        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            return jsonify({'error': f"Missing required fields: {', '.join(missing_fields)}"}), 400
        valid_values = {
            'sex': ['M', 'F'],
            'chestpaintype': ['TA', 'ATA', 'NAP', 'ASY'],
            'restingecg': ['Normal', 'ST', 'LVH'],
            'exerciseangina': ['N', 'Y'],
            'stslope': ['Up', 'Flat', 'Down']
        }
        for field, valid_options in valid_values.items():
            value = data[field]
            if value not in valid_options:
                return jsonify({'error': f"Invalid value for {field}: {value}. Must be one of {valid_options}"}), 400
        categorical_mappings = {
            'sex': {'M': 1, 'F': 0},
            'chestpaintype': {'TA': 3, 'ATA': 1, 'NAP': 2, 'ASY': 0},
            'restingecg': {'Normal': 1, 'ST': 2, 'LVH': 0},
            'exerciseangina': {'N': 0, 'Y': 1},
            'stslope': {'Up': 2, 'Flat': 1, 'Down': 0}
        }
        input_data = pd.DataFrame([{
            'Age': float(data['age']),
            'Sex': categorical_mappings['sex'][data['sex']],
            'ChestPainType': categorical_mappings['chestpaintype'][data['chestpaintype']],
            'RestingBP': float(data['restingbp']),
            'Cholesterol': float(data['cholesterol']),
            'FastingBS': int(data['fastingbs']),
            'RestingECG': categorical_mappings['restingecg'][data['restingecg']],
            'MaxHR': float(data['maxhr']),
            'ExerciseAngina': categorical_mappings['exerciseangina'][data['exerciseangina']],
            'Oldpeak': float(data['oldpeak']),
            'ST_Slope': categorical_mappings['stslope'][data['stslope']]
        }])
        if not all(key in current_app.config for key in ['SCALER', 'RF_MODEL']):
            return jsonify({'error': 'ML model not properly loaded'}), 500
        scaler = current_app.config['SCALER']
        rf_model = current_app.config['RF_MODEL']
        input_scaled = pd.DataFrame(scaler.transform(input_data), columns=input_data.columns)
        rf_pred = int(rf_model.predict(input_scaled)[0])
        if rf_pred == 1:
            rf_result = 'ya'
            rf_keterangan = 'Pasien diklasifikasi risiko gagal jantung.'
        else:
            rf_result = 'tidak'
            rf_keterangan = 'Pasien tidak diklasifikasi risiko gagal jantung.'
        # Simpan ke database jika user login
        if 'user_id' in session:
            save_classification(
                user_id=session['user_id'],
                classification_data=data,
                rf_result=rf_result,
                rf_keterangan=rf_keterangan
            )
        return jsonify({
            'random_forest': rf_result,
            'keterangan': rf_keterangan
        })
    except Exception as e:
        logging.error(f"An error occurred during classification: {str(e)}")
        logging.error(traceback.format_exc())
        return jsonify({'error': f"An error occurred during classification: {str(e)}"}), 500
