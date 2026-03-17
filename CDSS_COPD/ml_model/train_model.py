import pandas as pd
import joblib

from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import accuracy_score
from xgboost import XGBClassifier

print("Loading dataset...")

df = pd.read_excel("dataset/copd_oxygen_therapy_dataset_4000_balanced.xlsx")

# -------------------------
# Convert YES/NO columns
# -------------------------

yes_no_columns = [
    "COPD_History",
    "Chronic_Hypoxemia",
    "Home_Oxygen_Use"
]

for col in yes_no_columns:
    df[col] = df[col].map({"Yes":1, "No":0})

# -------------------------
# Encode categorical columns
# -------------------------

le_gender = LabelEncoder()
le_device = LabelEncoder()

df["Gender"] = le_gender.fit_transform(df["Gender"])
df["Recommended_Device"] = le_device.fit_transform(df["Recommended_Device"])

# -------------------------
# Split dataset
# -------------------------

X = df.drop("Recommended_Device", axis=1)
y = df["Recommended_Device"]

X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=0.2,
    random_state=42,
    stratify=y
)

print("Training model...")

model = XGBClassifier(
    n_estimators=700,
    max_depth=8,
    learning_rate=0.05,
    tree_method="hist",
    eval_metric="mlogloss",
    n_jobs=-1
)

model.fit(X_train, y_train)

# -------------------------
# Evaluate
# -------------------------

pred = model.predict(X_test)

accuracy = accuracy_score(y_test, pred)

print("Model Accuracy:", accuracy)

# -------------------------
# Save model
# -------------------------

joblib.dump(model, "trained_model/oxygen_model.pkl")
joblib.dump(le_gender, "trained_model/gender_encoder.pkl")
joblib.dump(le_device, "trained_model/device_encoder.pkl")

print("Model saved successfully!")