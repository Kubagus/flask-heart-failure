import os
import joblib
import logging
import numpy as np

def loadModel(app):
    def load_models():
        model_path = 'models/models_and_scaler_smoteenn.pkl'
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Models not found at {model_path}. Please run train_models.py first.")
        try:
            models = joblib.load(model_path)
            required_keys = ['rf_model', 'scaler']
            missing_keys = [key for key in required_keys if key not in models]
            if missing_keys:
                raise KeyError(f"Missing required models in file: {', '.join(missing_keys)}")
            return models['rf_model'], models['scaler']
        except Exception as e:
            raise Exception(f"Error loading models: {str(e)}")
    try:
        logging.info("Loading ML models...")
        rf_model, scaler = load_models()
        # Validate models
        test_data = np.array([[40, 1, 0, 120, 200, 0, 1, 150, 0, 0.0, 1]])  # Sample data
        test_data_scaled = scaler.transform(test_data)
        rf_pred = rf_model.predict_proba(test_data_scaled)
        if not isinstance(rf_pred, np.ndarray):
            raise ValueError("Random Forest model failed to make classifications")
        # Store models in app config
        app.config['RF_MODEL'] = rf_model
        app.config['SCALER'] = scaler
        logging.info("✅ Random Forest model and scaler loaded successfully")
    except FileNotFoundError as e:
        logging.error(f"❌ Error: {e}")
        raise
    except Exception as e:
        logging.error(f"❌ Error loading models: {str(e)}")
        raise
