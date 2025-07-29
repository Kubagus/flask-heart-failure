import pandas as pd
import numpy as np
import os
import joblib
import warnings
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
from imblearn.combine import SMOTEENN

warnings.filterwarnings('ignore')

# Load dataset
data = pd.read_csv('heart.csv')

# Encode kategori
label_encoders = {}
for column in data.select_dtypes(include=['object']).columns:
    le = LabelEncoder()
    data[column] = le.fit_transform(data[column])
    label_encoders[column] = le

# Bersihkan data
data['RestingBP'] = pd.to_numeric(data['RestingBP'], errors='coerce')
data['Cholesterol'] = pd.to_numeric(data['Cholesterol'], errors='coerce')
data['RestingBP'] = data['RestingBP'].apply(lambda x: np.nan if x > 140 or x < 40 else x)
data['Cholesterol'] = data['Cholesterol'].replace(0, np.nan)
data['RestingBP'].fillna(data['RestingBP'].median(), inplace=True)
data['Cholesterol'].fillna(data['Cholesterol'].median(), inplace=True)

# Pisahkan fitur dan label
X = data.drop('HeartDisease', axis=1)
y = data['HeartDisease']

# Split data
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

# Scaling - tetap gunakan kolom fitur agar sesuai dengan Flask app
scaler = StandardScaler()
X_train_scaled = pd.DataFrame(scaler.fit_transform(X_train), columns=X.columns)
X_test_scaled = pd.DataFrame(scaler.transform(X_test), columns=X.columns)

# Terapkan SMOTEENN
sm = SMOTEENN(sampling_strategy=0.96, random_state=42)
X_train_res, y_train_res = sm.fit_resample(X_train_scaled, y_train)

# Fungsi evaluasi dan mengembalikan model
def evaluate_model(model, X_train, y_train, X_test, y_test, name, hasil):
    model.fit(X_train, y_train)
    pred = model.predict(X_test)
    hasil.append({
        'Model': name,
        'Accuracy': accuracy_score(y_test, pred),
        'Precision': precision_score(y_test, pred),
        'Recall': recall_score(y_test, pred),
        'F1-Score': f1_score(y_test, pred)
    })
    return model

# Evaluasi model
hasil_sesudah = []

rf_model = evaluate_model(
    RandomForestClassifier(n_estimators=100, max_depth=40, random_state=42, min_samples_split=4),
    X_train_res, y_train_res, X_test_scaled, y_test,
    'Random Forest (After)', hasil_sesudah)

# Simpan model dan scaler
saved_models = {
    'scaler': scaler,
    'rf_model': rf_model
}

if not os.path.exists('models'):
    os.makedirs('models')

joblib.dump(saved_models, 'models/models_and_scaler_smoteenn.pkl')

# Tampilkan hasil evaluasi
df_hasil = pd.DataFrame(hasil_sesudah)
print("\n=== Kinerja Model Random Forest Sesudah SMOTEENN ===")
print(df_hasil.sort_values(by='Model').reset_index(drop=True))
print("✅ Model Random Forest dan scaler telah disimpan ke 'models/models_and_scaler_smoteenn.pkl'.")
