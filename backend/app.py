from fastapi import FastAPI, UploadFile, File, HTTPException
import pandas as pd
import joblib
import io
import numpy as np

app = FastAPI(title="Techeuilla Financial Fraud Detection API")

# Load trained model
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

        if df.empty:
            raise HTTPException(
                status_code=400,
                detail="Uploaded CSV is empty."
            )

        # Keep original target for evaluation if available
        actual_fraud = None

        if "isFraud" in df.columns:
            actual_fraud = df["isFraud"].copy()
            df = df.drop(columns=["isFraud"])

        # Make sure every model feature exists
        for column in model.feature_names_in_:
            if column not in df.columns:
                df[column] = 0

        # Exact feature order expected by XGBoost
        X = df[model.feature_names_in_].copy()

        # Convert categorical/object columns to numeric codes
        object_columns = X.select_dtypes(
            include=["object", "category"]
        ).columns

        for column in object_columns:
            X[column] = X[column].astype("category").cat.codes

        # Apply trained imputer
        X = pd.DataFrame(
            imputer.transform(X),
            columns=X.columns
        )

        # Model prediction
        probabilities = model.predict_proba(X)[:, 1]

        predictions = (probabilities >= 0.5).astype(int)

        # Statistics
        total_transactions = len(df)
        fraud_count = int(predictions.sum())
        safe_count = int(total_transactions - fraud_count)

        average_risk = float(probabilities.mean())

        high_risk_count = int((probabilities >= 0.75).sum())
        medium_risk_count = int(
            ((probabilities >= 0.40) & (probabilities < 0.75)).sum()
        )
        low_risk_count = int((probabilities < 0.40).sum())

        # Create result table
        results = df.copy()

        results["Fraud Probability"] = probabilities
        results["Prediction"] = predictions

        results["Risk Score"] = (
            probabilities * 100
        ).round(2)

        results["Risk Level"] = np.select(
            [
                probabilities >= 0.75,
                probabilities >= 0.40
            ],
            [
                "HIGH",
                "MEDIUM"
            ],
            default="LOW"
        )

        # Top 10 risky transactions
        top_risk = (
            results
            .sort_values(
                "Fraud Probability",
                ascending=False
            )
            .head(10)
        )

        # Select useful columns for dashboard
        display_columns = [
            column
            for column in [
                "TransactionID",
                "TransactionAmt",
                "ProductCD",
                "Fraud Probability",
                "Prediction",
                "Risk Score",
                "Risk Level"
            ]
            if column in top_risk.columns
        ]

        top_risk = top_risk[display_columns]

        # Make JSON safe
        top_risk = top_risk.replace(
            [np.inf, -np.inf],
            np.nan
        )

        top_risk = top_risk.fillna("")

        top_risk = top_risk.to_dict(
            orient="records"
        )

        return {
            "success": True,

            "summary": {
                "total_transactions": total_transactions,
                "fraud_detected": fraud_count,
                "safe_transactions": safe_count,
                "average_risk": round(
                    average_risk * 100,
                    2
                ),
                "high_risk": high_risk_count,
                "medium_risk": medium_risk_count,
                "low_risk": low_risk_count
            },

            "top_risk_transactions": top_risk
        }

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )