from fastapi import FastAPI, UploadFile, File, HTTPException
import pandas as pd
import joblib
import io
import numpy as np

app = FastAPI(title="Financial Fraud Detection API")

# Load model and imputer
model = joblib.load("../saved_models/xgboost.pkl")
imputer = joblib.load("../saved_models/imputer.pkl")


@app.get("/")
def home():
    return {
        "message": "Financial Fraud Detection API Running"
    }


@app.post("/predict")
async def predict(file: UploadFile = File(...)):
    try:
        # Read uploaded CSV
        contents = await file.read()
        df = pd.read_csv(io.BytesIO(contents))

        # Remove target column if present
        if "isFraud" in df.columns:
            df = df.drop(columns=["isFraud"])

        # Add missing columns expected by model
        for col in model.feature_names_in_:
            if col not in df.columns:
                df[col] = 0

        # Keep only columns used during training
        X = df[model.feature_names_in_].copy()

        # Encode categorical columns
        object_cols = X.select_dtypes(include=["object"]).columns

        for col in object_cols:
            X[col] = X[col].astype("category").cat.codes

        # Fill missing values using trained imputer
        X = pd.DataFrame(
            imputer.transform(X),
            columns=X.columns
        )

        # Predict
        probabilities = model.predict_proba(X)[:, 1]
        predictions = (probabilities >= 0.5).astype(int)

        # Prepare output
        result = df.copy()

        result["Fraud Probability"] = probabilities
        result["Prediction"] = predictions

        # Replace NaN and Infinity with JSON-safe values
        result = result.replace([np.inf, -np.inf], np.nan)
        result = result.fillna("")

        # Convert NumPy data types to Python data types
        records = result.head(20).to_dict(orient="records")

        for row in records:
            for key, value in row.items():
                if isinstance(value, np.integer):
                    row[key] = int(value)
                elif isinstance(value, np.floating):
                    row[key] = float(value)
                elif isinstance(value, np.bool_):
                    row[key] = bool(value)

        return records

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )