from flask import Blueprint, request, jsonify, current_app, session
import pandas as pd
import traceback
from db.database import save_prediction

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
        data = request.json
        input_data = pd.DataFrame([{
            'Age': float(data['age']),
            'Sex': data['sex'],
            'ChestPainType': data['chestPainType'],
            'RestingBP': float(data['restingBP']),
            'Cholesterol': float(data['cholesterol']),
            'FastingBS': int(data['fastingBS']),
            'RestingECG': data['restingECG'],
            'MaxHR': float(data['maxHR']),
            'ExerciseAngina': data['exerciseAngina'],
            'Oldpeak': float(data['oldpeak']),
            'ST_Slope': data['stSlope']
        }])

        mappings = {
            'Sex': {'M': 1, 'F': 0},
            'ChestPainType': {'TA': 3, 'ATA': 1, 'NAP': 2, 'ASY': 0},
            'RestingECG': {'Normal': 1, 'ST': 2, 'LVH': 0},
            'ExerciseAngina': {'N': 0, 'Y': 1},
            'ST_Slope': {'Up': 2, 'Flat': 1, 'Down': 0}
        }

        for col, map_dict in mappings.items():
            input_data[col] = input_data[col].map(map_dict)

        # ambil dari config
        scaler = current_app.config['SCALER']
        dt_model = current_app.config['DT_MODEL']
        rf_model = current_app.config['RF_MODEL']
        xgb_model = current_app.config['XGB_MODEL']

        input_scaled = pd.DataFrame(scaler.transform(input_data), columns=input_data.columns)

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

    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': str(e)}), 400
