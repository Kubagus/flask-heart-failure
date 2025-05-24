from flask import Blueprint, request, jsonify, current_app, session
import pandas as pd
import traceback
from db.database import save_prediction
import logging

predict_bp = Blueprint('predict_bp', __name__)

def classify_risk(prob):
    if prob < 30:
        return "Risiko rendah terkena gagal jantung"
    elif prob < 70:
        return "Risiko sedang terkena gagal jantung"
    else:
        return "Risiko tinggi terkena gagal jantung"

@predict_bp.route('/predict', methods=['POST'])
def predict():
    try:
        # Log request details
        logging.info(f"Request method: {request.method}")
        logging.info(f"Request headers: {dict(request.headers)}")
        logging.info(f"Request content type: {request.content_type}")
        
        # Check if request has JSON data
        if not request.is_json:
            error_msg = "Request must be JSON"
            logging.error(error_msg)
            return jsonify({'error': error_msg}), 400

        data = request.json
        if not data:
            error_msg = "No data provided"
            logging.error(error_msg)
            return jsonify({'error': error_msg}), 400

        # Log the received data
        logging.info(f"Received prediction data: {data}")

        # Convert all keys to lowercase for case-insensitive comparison
        data = {k.lower(): v for k, v in data.items()}
        
        # Validate required fields (using lowercase keys)
        required_fields = ['age', 'sex', 'chestpaintype', 'restingbp', 'cholesterol', 
                         'fastingbs', 'restingecg', 'maxhr', 'exerciseangina', 
                         'oldpeak', 'stslope']
        
        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            error_msg = f"Missing required fields: {', '.join(missing_fields)}"
            logging.error(error_msg)
            return jsonify({'error': error_msg}), 400

        # Validate field values
        try:
            input_data = pd.DataFrame([{
                'Age': float(data['age']),
                'Sex': data['sex'],
                'ChestPainType': data['chestpaintype'],
                'RestingBP': float(data['restingbp']),
                'Cholesterol': float(data['cholesterol']),
                'FastingBS': int(data['fastingbs']),
                'RestingECG': data['restingecg'],
                'MaxHR': float(data['maxhr']),
                'ExerciseAngina': data['exerciseangina'],
                'Oldpeak': float(data['oldpeak']),
                'ST_Slope': data['stslope']
            }])
        except ValueError as e:
            error_msg = f"Invalid numeric value: {str(e)}"
            logging.error(error_msg)
            return jsonify({'error': error_msg}), 400

        # Validate categorical values
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
                error_msg = f"Invalid value for {field}: {value}. Must be one of {valid_options}"
                logging.error(error_msg)
                return jsonify({'error': error_msg}), 400

        mappings = {
            'Sex': {'M': 1, 'F': 0},
            'ChestPainType': {'TA': 3, 'ATA': 1, 'NAP': 2, 'ASY': 0},
            'RestingECG': {'Normal': 1, 'ST': 2, 'LVH': 0},
            'ExerciseAngina': {'N': 0, 'Y': 1},
            'ST_Slope': {'Up': 2, 'Flat': 1, 'Down': 0}
        }

        for col, map_dict in mappings.items():
            input_data[col] = input_data[col].map(map_dict)

        # Check if models are loaded
        if not all(key in current_app.config for key in ['SCALER', 'DT_MODEL', 'RF_MODEL', 'XGB_MODEL']):
            error_msg = "ML models not properly loaded"
            logging.error(error_msg)
            return jsonify({'error': error_msg}), 500

        # Get models from config
        scaler = current_app.config['SCALER']
        dt_model = current_app.config['DT_MODEL']
        rf_model = current_app.config['RF_MODEL']
        xgb_model = current_app.config['XGB_MODEL']

        # Scale input data
        input_scaled = pd.DataFrame(scaler.transform(input_data), columns=input_data.columns)

        # Make predictions
        dt_prob = float(dt_model.predict_proba(input_scaled)[0][1]) * 100
        rf_prob = float(rf_model.predict_proba(input_scaled)[0][1]) * 100
        xgb_prob = float(xgb_model.predict_proba(input_scaled)[0][1]) * 100

        result = {
            'decision_tree': round(dt_prob, 2),
            'decision_tree_risk': classify_risk(dt_prob),
            'random_forest': round(rf_prob, 2),
            'random_forest_risk': classify_risk(rf_prob),
            'xgboost': round(xgb_prob, 2),
            'xgboost_risk': classify_risk(xgb_prob)
        }

        # Save prediction history if user is logged in
        if 'user_id' in session:
            save_prediction(
                user_id=session['user_id'],
                prediction_data=data,
                prediction_result=result
            )

        return jsonify(result)

    except KeyError as e:
        error_msg = f"Missing required field: {str(e)}"
        logging.error(error_msg)
        return jsonify({'error': error_msg}), 400
    except ValueError as e:
        error_msg = f"Invalid value provided: {str(e)}"
        logging.error(error_msg)
        return jsonify({'error': error_msg}), 400
    except Exception as e:
        error_msg = f"An error occurred during prediction: {str(e)}"
        logging.error(error_msg)
        logging.error(traceback.format_exc())
        return jsonify({'error': error_msg}), 500
