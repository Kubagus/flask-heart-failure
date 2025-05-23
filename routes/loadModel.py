def loadModel(app):
    # Load models (your existing code)
    def load_models():
        import os
        import joblib
        if not os.path.exists('models/models_and_scaler_smoteenn.pkl'):
            raise FileNotFoundError("Models not found. Please run train_models.py first.")
        
        models = joblib.load('models/models_and_scaler_smoteenn.pkl')
        return models['dt_model'], models['rf_model'], models['xgb_model'], models['scaler']

    try:
        dt_model, rf_model, xgb_model, scaler = load_models()
        app.config['DT_MODEL'] = dt_model
        app.config['RF_MODEL'] = rf_model
        app.config['XGB_MODEL'] = xgb_model
        app.config['SCALER'] = scaler
    except FileNotFoundError as e:
        print(f"❌ Error: {e}")
        exit(1)
