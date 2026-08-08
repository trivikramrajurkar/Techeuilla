from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware

import pandas as pd
import numpy as np
import joblib
import io
import shap


# ============================================================
# APP
# ============================================================

app = FastAPI(
    title="Techeuilla Financial Fraud Detection API",
    description="AI-powered financial fraud detection using XGBoost and SHAP",
    version="1.0.0"
)


# ============================================================
# CORS
# ============================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# LOAD MODEL
# ============================================================

try:
    model = joblib.load("../saved_models/xgboost.pkl")
    imputer = joblib.load("../saved_models/imputer.pkl")

    # SHAP explainer for XGBoost
    explainer = shap.TreeExplainer(model)

    print("Model loaded successfully.")
    print("Imputer loaded successfully.")
    print("SHAP explainer initialized.")

except Exception as e:
    print("ERROR LOADING MODEL:", e)
    model = None
    imputer = None
    explainer = None


# ============================================================
# HOME
# ============================================================

@app.get("/")
def home():
    return {
        "message": "Financial Fraud Detection API Running",
        "model": "XGBoost",
        "explainability": "SHAP",
        "status": "online"
    }


# ============================================================
# HEALTH CHECK
# ============================================================

@app.get("/health")
def health():

    return {
        "status": "healthy" if model is not None else "model_not_loaded",
        "model_loaded": model is not None,
        "imputer_loaded": imputer is not None,
        "shap_loaded": explainer is not None
    }


# ============================================================
# PREDICTION
# ============================================================

@app.post("/predict")
async def predict(file: UploadFile = File(...)):

    try:

        # --------------------------------------------------------
        # Check file type
        # --------------------------------------------------------

        if not file.filename.lower().endswith(".csv"):
            raise HTTPException(
                status_code=400,
                detail="Please upload a CSV file."
            )


        # --------------------------------------------------------
        # Check model
        # --------------------------------------------------------

        if model is None or imputer is None:
            raise HTTPException(
                status_code=500,
                detail="Model or imputer could not be loaded."
            )


        # --------------------------------------------------------
        # Read CSV
        # --------------------------------------------------------

        contents = await file.read()

        if not contents:
            raise HTTPException(
                status_code=400,
                detail="Uploaded file is empty."
            )

        df = pd.read_csv(
            io.BytesIO(contents)
        )


        if df.empty:
            raise HTTPException(
                status_code=400,
                detail="CSV contains no rows."
            )


        # --------------------------------------------------------
        # Keep original target if present
        # --------------------------------------------------------

        actual_fraud = None

        if "isFraud" in df.columns:

            actual_fraud = df["isFraud"].copy()

            df = df.drop(
                columns=["isFraud"]
            )


        # --------------------------------------------------------
        # Make sure all model features exist
        # --------------------------------------------------------

        expected_features = list(
            model.feature_names_in_
        )

        for column in expected_features:

            if column not in df.columns:
                df[column] = 0


        # --------------------------------------------------------
        # Keep EXACT feature order
        # --------------------------------------------------------

        X = df[
            expected_features
        ].copy()


        # --------------------------------------------------------
        # Convert categorical columns
        # --------------------------------------------------------

        object_columns = X.select_dtypes(
            include=["object", "category"]
        ).columns


        for column in object_columns:

            X[column] = (
                X[column]
                .astype("category")
                .cat.codes
            )


        # --------------------------------------------------------
        # Replace infinite values
        # --------------------------------------------------------

        X = X.replace(
            [np.inf, -np.inf],
            np.nan
        )


        # --------------------------------------------------------
        # Apply trained imputer
        # --------------------------------------------------------

        X = pd.DataFrame(
            imputer.transform(X),
            columns=X.columns,
            index=X.index
        )


        # --------------------------------------------------------
        # XGBoost prediction
        # --------------------------------------------------------

        probabilities = model.predict_proba(X)[:, 1]

        predictions = (
            probabilities >= 0.5
        ).astype(int)


        # ========================================================
        # SUMMARY STATISTICS
        # ========================================================

        total_transactions = int(
            len(df)
        )

        fraud_count = int(
            predictions.sum()
        )

        safe_count = int(
            total_transactions - fraud_count
        )

        average_risk = float(
            probabilities.mean()
        )


        # --------------------------------------------------------
        # Risk categories
        # --------------------------------------------------------

        high_risk_count = int(
            (probabilities >= 0.75).sum()
        )

        medium_risk_count = int(
            (
                (probabilities >= 0.40)
                &
                (probabilities < 0.75)
            ).sum()
        )

        low_risk_count = int(
            (probabilities < 0.40).sum()
        )


        # ========================================================
        # RESULT DATAFRAME
        # ========================================================

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


        # ========================================================
        # TOP RISK TRANSACTIONS
        # ========================================================

        top_risk = (
            results
            .sort_values(
                "Fraud Probability",
                ascending=False
            )
            .head(10)
            .copy()
        )


        # --------------------------------------------------------
        # Useful dashboard columns
        # --------------------------------------------------------

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


        top_risk = top_risk[
            display_columns
        ]


        # --------------------------------------------------------
        # Make JSON safe
        # --------------------------------------------------------

        top_risk = top_risk.replace(
            [np.inf, -np.inf],
            np.nan
        )

        top_risk = top_risk.fillna("")


        top_risk_records = (
            top_risk
            .to_dict(orient="records")
        )


        # ========================================================
        # SHAP EXPLANATIONS
        # ========================================================

        explanations = []


        if explainer is not None:

            # Only explain top 10 transactions
            top_indices = np.argsort(
                probabilities
            )[::-1][:10]


            X_top = X.iloc[
                top_indices
            ]


            shap_values = explainer.shap_values(
                X_top
            )


            # ----------------------------------------------------
            # Handle different SHAP output formats
            # ----------------------------------------------------

            if isinstance(
                shap_values,
                list
            ):

                shap_values = shap_values[-1]


            # Some SHAP versions return
            # (rows, features, classes)

            if len(shap_values.shape) == 3:

                shap_values = shap_values[:, :, -1]


            # ----------------------------------------------------
            # Create explanations
            # ----------------------------------------------------

            for position, original_index in enumerate(
                top_indices
            ):

                values = shap_values[
                    position
                ]


                # Five most influential features
                feature_indices = np.argsort(
                    np.abs(values)
                )[::-1][:5]


                factors = []


                for feature_index in feature_indices:

                    feature_name = X.columns[
                        feature_index
                    ]

                    contribution = float(
                        values[feature_index]
                    )


                    factors.append(
                        {
                            "feature": feature_name,

                            "impact": round(
                                contribution,
                                4
                            ),

                            "direction": (
                                "increases fraud risk"
                                if contribution > 0
                                else
                                "reduces fraud risk"
                            )
                        }
                    )


                explanations.append(
                    {
                        "transaction_index": int(
                            original_index
                        ),

                        "fraud_probability": round(
                            float(
                                probabilities[
                                    original_index
                                ]
                            ),
                            4
                        ),

                        "top_factors": factors
                    }
                )


        # ========================================================
        # OPTIONAL ACTUAL LABEL STATISTICS
        # ========================================================

        actual_results = None


        if actual_fraud is not None:

            try:

                actual_fraud_values = (
                    pd.to_numeric(
                        actual_fraud,
                        errors="coerce"
                    )
                )


                actual_fraud_count = int(
                    actual_fraud_values.sum()
                )


                actual_results = {
                    "actual_fraud_count":
                        actual_fraud_count
                }

            except Exception:

                actual_results = None


        # ========================================================
        # FINAL RESPONSE
        # ========================================================

        response = {

            "success": True,

            "filename": file.filename,

            "summary": {

                "total_transactions":
                    total_transactions,

                "fraud_detected":
                    fraud_count,

                "safe_transactions":
                    safe_count,

                "average_risk":
                    round(
                        average_risk * 100,
                        2
                    ),

                "high_risk":
                    high_risk_count,

                "medium_risk":
                    medium_risk_count,

                "low_risk":
                    low_risk_count
            },

            "top_risk_transactions":
                top_risk_records,

            "explanations":
                explanations
        }


        # Add actual-label information
        # only when uploaded CSV contains isFraud

        if actual_results is not None:

            response[
                "actual_labels"
            ] = actual_results


        return response


    # ============================================================
    # ERROR HANDLING
    # ============================================================

    except HTTPException:

        raise


    except Exception as e:

        print(
            "Prediction error:",
            repr(e)
        )

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )