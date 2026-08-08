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

    model = joblib.load(
        "../saved_models/xgboost.pkl"
    )

    imputer = joblib.load(
        "../saved_models/imputer.pkl"
    )

    explainer = shap.TreeExplainer(model)

    print("Model loaded successfully.")
    print("Imputer loaded successfully.")
    print("SHAP explainer initialized.")

except Exception as e:

    print(
        "ERROR LOADING MODEL:",
        e
    )

    model = None
    imputer = None
    explainer = None


# ============================================================
# HUMAN EXPLANATION ENGINE
# ============================================================

def create_human_explanation(
    feature_name,
    contribution,
    transaction_value=None
):
    """
    Convert a SHAP contribution into
    an explanation understandable to
    a non-technical user.
    """

    impact = abs(contribution)


    # ========================================================
    # FEATURE INCREASES FRAUD RISK
    # ========================================================

    if contribution > 0:

        if impact >= 0.75:

            severity = "Strong fraud signal"

        elif impact >= 0.35:

            severity = "Moderate fraud signal"

        else:

            severity = "Possible fraud signal"


        # ----------------------------------------------------
        # Transaction amount
        # ----------------------------------------------------

        if feature_name == "TransactionAmt":

            if transaction_value is not None:

                explanation = (
                    f"The transaction amount of "
                    f"{transaction_value:.2f} is contributing "
                    f"to the higher fraud risk predicted by "
                    f"the model."
                )

            else:

                explanation = (
                    "The transaction amount is contributing "
                    "to the higher fraud risk predicted by "
                    "the model."
                )


        # ----------------------------------------------------
        # Known categorical features
        # ----------------------------------------------------

        elif feature_name in [
            "ProductCD",
            "card4",
            "card6"
        ]:

            explanation = (
                f"The transaction's {feature_name} "
                "characteristics are associated with "
                "a higher predicted fraud risk."
            )


        # ----------------------------------------------------
        # Anonymous / engineered features
        # ----------------------------------------------------

        else:

            explanation = (
                "This transaction contains a pattern "
                "that the model has learned to associate "
                "with fraudulent transactions."
            )


        return {
            "title": severity,
            "explanation": explanation,
            "impact": (
                "high"
                if impact >= 0.75
                else "medium"
            )
        }


    # ========================================================
    # FEATURE REDUCES FRAUD RISK
    # ========================================================

    else:

        if impact >= 0.75:

            severity = "Strong legitimate signal"

        elif impact >= 0.35:

            severity = "Moderate legitimate signal"

        else:

            severity = "Lower-risk signal"


        explanation = (
            "This characteristic is pushing the model "
            "toward considering the transaction legitimate."
        )


        return {
            "title": severity,
            "explanation": explanation,
            "impact": "positive"
        }


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
        "status": (
            "healthy"
            if model is not None
            else "model_not_loaded"
        ),

        "model_loaded":
            model is not None,

        "imputer_loaded":
            imputer is not None,

        "shap_loaded":
            explainer is not None
    }


# ============================================================
# PREDICT
# ============================================================

@app.post("/predict")
async def predict(
    file: UploadFile = File(...)
):

    try:

        # ====================================================
        # FILE VALIDATION
        # ====================================================

        if not file.filename.lower().endswith(".csv"):

            raise HTTPException(
                status_code=400,
                detail="Please upload a CSV file."
            )


        if model is None or imputer is None:

            raise HTTPException(
                status_code=500,
                detail="Model or imputer could not be loaded."
            )


        # ====================================================
        # READ CSV
        # ====================================================

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


        # ====================================================
        # KEEP TARGET IF PRESENT
        # ====================================================

        actual_fraud = None


        if "isFraud" in df.columns:

            actual_fraud = df["isFraud"].copy()

            df = df.drop(
                columns=["isFraud"]
            )


        # ====================================================
        # MODEL FEATURES
        # ====================================================

        expected_features = list(
            model.feature_names_in_
        )


        # Add missing columns

        for column in expected_features:

            if column not in df.columns:

                df[column] = 0


        # Exact feature order

        X = df[
            expected_features
        ].copy()


        # ====================================================
        # CONVERT CATEGORICAL FEATURES
        # ====================================================

        object_columns = X.select_dtypes(
            include=[
                "object",
                "category"
            ]
        ).columns


        for column in object_columns:

            X[column] = (
                X[column]
                .astype("category")
                .cat.codes
            )


        # ====================================================
        # CLEAN INFINITE VALUES
        # ====================================================

        X = X.replace(
            [
                np.inf,
                -np.inf
            ],
            np.nan
        )


        # ====================================================
        # IMPUTATION
        # ====================================================

        X = pd.DataFrame(
            imputer.transform(X),
            columns=X.columns,
            index=X.index
        )


        # ====================================================
        # MODEL PREDICTION
        # ====================================================

        probabilities = model.predict_proba(
            X
        )[:, 1]


        predictions = (
            probabilities >= 0.5
        ).astype(int)


        # ====================================================
        # SUMMARY
        # ====================================================

        total_transactions = int(
            len(df)
        )


        fraud_count = int(
            predictions.sum()
        )


        safe_count = int(
            total_transactions -
            fraud_count
        )


        average_risk = float(
            probabilities.mean()
        )


        # ====================================================
        # RISK LEVELS
        # ====================================================

        high_risk_count = int(
            (
                probabilities >= 0.75
            ).sum()
        )


        medium_risk_count = int(
            (
                (probabilities >= 0.40)
                &
                (probabilities < 0.75)
            ).sum()
        )


        low_risk_count = int(
            (
                probabilities < 0.40
            ).sum()
        )


        # ====================================================
        # RESULT DATAFRAME
        # ====================================================

        results = df.copy()


        results["Fraud Probability"] = (
            probabilities
        )


        results["Prediction"] = (
            predictions
        )


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


        # ====================================================
        # TOP 10 RISK TRANSACTIONS
        # ====================================================

        top_risk = (
            results
            .sort_values(
                "Fraud Probability",
                ascending=False
            )
            .head(10)
            .copy()
        )


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


        # ====================================================
        # JSON SAFETY
        # ====================================================

        top_risk = top_risk.replace(
            [
                np.inf,
                -np.inf
            ],
            np.nan
        )


        top_risk = top_risk.fillna("")


        top_risk_records = (
            top_risk
            .to_dict(
                orient="records"
            )
        )


        # ====================================================
        # SHAP EXPLANATIONS
        # ====================================================

        explanations = []


        if explainer is not None:

            # Top 10 highest-risk transactions

            top_indices = np.argsort(
                probabilities
            )[::-1][:10]


            X_top = X.iloc[
                top_indices
            ]


            shap_values = (
                explainer.shap_values(
                    X_top
                )
            )


            # =================================================
            # HANDLE SHAP OUTPUT FORMAT
            # =================================================

            if isinstance(
                shap_values,
                list
            ):

                shap_values = (
                    shap_values[-1]
                )


            # Some SHAP versions return:
            #
            # rows × features × classes

            if len(
                shap_values.shape
            ) == 3:

                shap_values = (
                    shap_values[:, :, -1]
                )


            # =================================================
            # EACH TRANSACTION
            # =================================================

            for position, original_index in enumerate(
                top_indices
            ):

                values = (
                    shap_values[position]
                )


                # Five most influential features

                feature_indices = (
                    np.argsort(
                        np.abs(values)
                    )[::-1][:5]
                )


                factors = []


                # =================================================
                # FEATURES
                # =================================================

                for feature_index in feature_indices:

                    feature_name = (
                        X.columns[
                            feature_index
                        ]
                    )


                    contribution = float(
                        values[
                            feature_index
                        ]
                    )


                    transaction_value = None


                    if (
                        "TransactionAmt"
                        in df.columns
                    ):

                        value = df.iloc[
                            original_index
                        ]["TransactionAmt"]


                        if pd.notna(value):

                            try:

                                transaction_value = float(
                                    value
                                )

                            except (
                                ValueError,
                                TypeError
                            ):

                                transaction_value = None


                    human = (
                        create_human_explanation(
                            feature_name,
                            contribution,
                            transaction_value
                        )
                    )


                    factors.append(
                        {
                            "feature":
                                feature_name,

                            "impact":
                                round(
                                    contribution,
                                    4
                                ),

                            "direction":
                                (
                                    "increases fraud risk"
                                    if contribution > 0
                                    else
                                    "reduces fraud risk"
                                ),

                            "title":
                                human["title"],

                            "explanation":
                                human["explanation"],

                            "impact_level":
                                human["impact"]
                        }
                    )


                # =================================================
                # OVERALL HUMAN EXPLANATION
                # =================================================

                probability = float(
                    probabilities[
                        original_index
                    ]
                )


                positive_factors = [
                    factor
                    for factor in factors
                    if factor["impact"] > 0
                ]


                negative_factors = [
                    factor
                    for factor in factors
                    if factor["impact"] < 0
                ]


                # -----------------------------------------------
                # HIGH RISK
                # -----------------------------------------------

                if probability >= 0.75:

                    overall_explanation = (
                        "This transaction has been "
                        "classified as high risk. "
                        "The model detected multiple "
                        "characteristics that strongly "
                        "resemble patterns associated "
                        "with fraudulent transactions."
                    )


                    recommendation = (
                        "Manual review is recommended "
                        "before approving this transaction."
                    )


                    risk_level = "HIGH"


                # -----------------------------------------------
                # MEDIUM RISK
                # -----------------------------------------------

                elif probability >= 0.40:

                    overall_explanation = (
                        "This transaction shows some "
                        "characteristics associated with "
                        "fraudulent activity, but the "
                        "evidence is not conclusive."
                    )


                    recommendation = (
                        "Consider additional verification "
                        "before approval."
                    )


                    risk_level = "MEDIUM"


                # -----------------------------------------------
                # LOW RISK
                # -----------------------------------------------

                else:

                    overall_explanation = (
                        "The transaction appears relatively "
                        "low risk. The model found stronger "
                        "evidence consistent with legitimate "
                        "activity."
                    )


                    recommendation = (
                        "The transaction can proceed under "
                        "normal monitoring."
                    )


                    risk_level = "LOW"


                # =================================================
                # ADD EXPLANATION
                # =================================================

                explanations.append(
                    {
                        "transaction_index":
                            int(original_index),

                        "fraud_probability":
                            round(
                                probability,
                                4
                            ),

                        "risk_level":
                            risk_level,

                        "overall_explanation":
                            overall_explanation,

                        "recommendation":
                            recommendation,

                        "positive_signal_count":
                            len(
                                positive_factors
                            ),

                        "negative_signal_count":
                            len(
                                negative_factors
                            ),

                        "top_factors":
                            factors
                    }
                )


        # ====================================================
        # ACTUAL LABEL INFORMATION
        # ====================================================

        actual_results = None


        if actual_fraud is not None:

            try:

                actual_fraud_values = pd.to_numeric(
                    actual_fraud,
                    errors="coerce"
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


        # ====================================================
        # RESPONSE
        # ====================================================

        response = {

            "success":
                True,

            "filename":
                file.filename,

            "summary":
                {
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


        if actual_results is not None:

            response[
                "actual_labels"
            ] = actual_results


        return response


    # ========================================================
    # ERROR HANDLING
    # ========================================================

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