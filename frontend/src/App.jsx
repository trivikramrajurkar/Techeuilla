import { useState } from "react";
import axios from "axios";

import {
  ShieldCheck,
  Upload,
  AlertTriangle,
  CheckCircle,
  Activity,
  FileWarning,
  Download,
  Brain,
  ArrowUp,
  ArrowDown,
} from "lucide-react";

import {
  PieChart,
  Pie,
  Cell,
  ResponsiveContainer,
  Tooltip,
} from "recharts";

import "./App.css";


function App() {
  const [file, setFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState(null);
  const [error, setError] = useState("");


  // ============================================================
  // ANALYZE FILE
  // ============================================================

  const analyzeFile = async () => {
    if (!file) {
      setError("Please select a CSV file first.");
      return;
    }

    setLoading(true);
    setError("");
    setData(null);

    try {
      const formData = new FormData();
      formData.append("file", file);

      const response = await axios.post(
        "http://127.0.0.1:8000/predict",
        formData
      );

      setData(response.data);

    } catch (err) {
      console.error(err);

      setError(
        err.response?.data?.detail ||
        "Unable to analyze the file. Make sure the backend is running."
      );

    } finally {
      setLoading(false);
    }
  };


  // ============================================================
  // DOWNLOAD REPORT
  // ============================================================

  const downloadReport = () => {
    if (!data?.top_risk_transactions?.length) {
      return;
    }

    const rows = data.top_risk_transactions;
    const headers = Object.keys(rows[0]);

    const csv = [
      headers.join(","),

      ...rows.map((row) =>
        headers
          .map(
            (header) =>
              `"${String(row[header] ?? "").replace(/"/g, '""')}"`
          )
          .join(",")
      ),
    ].join("\n");

    const blob = new Blob(
      [csv],
      {
        type: "text/csv;charset=utf-8;",
      }
    );

    const url = URL.createObjectURL(blob);

    const link = document.createElement("a");

    link.href = url;
    link.download = "techeuilla_fraud_report.csv";

    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);

    URL.revokeObjectURL(url);
  };


  // ============================================================
  // DATA
  // ============================================================

  const summary = data?.summary;

  const chartData = summary
    ? [
        {
          name: "Low Risk",
          value: summary.low_risk,
        },
        {
          name: "Medium Risk",
          value: summary.medium_risk,
        },
        {
          name: "High Risk",
          value: summary.high_risk,
        },
      ]
    : [];


  // ============================================================
  // UI
  // ============================================================

  return (
    <div className="app">

      {/* ======================================================
          HEADER
      ====================================================== */}

      <header className="header">

        <div className="brand">

          <div className="logo">
            <ShieldCheck size={28} />
          </div>

          <div>
            <h1>Techeuilla</h1>

            <p>
              Financial Fraud Detection
            </p>
          </div>

        </div>


        <div className="status">

          <span className="status-dot"></span>

          AI Engine Online

        </div>

      </header>


      {/* ======================================================
          MAIN
      ====================================================== */}

      <main className="container">


        {/* ====================================================
            HERO
        ==================================================== */}

        <section className="hero">

          <div>

            <p className="eyebrow">
              AI-POWERED TRANSACTION ANALYSIS
            </p>

            <h2>
              Detect suspicious transactions
              <span>
                {" "}before they become fraud.
              </span>
            </h2>

            <p className="hero-text">
              Upload transaction data and let our
              XGBoost fraud detection engine identify
              high-risk activity and explain why it was flagged.
            </p>

          </div>

        </section>


        {/* ====================================================
            UPLOAD
        ==================================================== */}

        <section className="upload-card">

          <div className="upload-icon">
            <Upload size={30} />
          </div>

          <h3>
            Upload Transaction Data
          </h3>

          <p>
            Upload a CSV file containing transaction features.
          </p>

          <label className="file-input">

            <input
              type="file"
              accept=".csv"
              onChange={(event) => {
                setFile(
                  event.target.files?.[0] || null
                );

                setError("");
              }}
            />

            <span>
              {file
                ? file.name
                : "Choose CSV file"}
            </span>

          </label>


          <button
            className="analyze-btn"
            onClick={analyzeFile}
            disabled={loading}
          >

            {loading
              ? "Analyzing transactions..."
              : "Analyze Transactions"}

          </button>


          {error && (
            <div className="error">
              {error}
            </div>
          )}

        </section>


        {/* ====================================================
            RESULTS
        ==================================================== */}

        {data && summary && (
          <>


            {/* ==================================================
                STAT CARDS
            ================================================== */}

            <section className="stats-grid">

              <StatCard
                icon={<Activity />}
                title="Transactions"
                value={summary.total_transactions}
              />

              <StatCard
                icon={<AlertTriangle />}
                title="Fraud Detected"
                value={summary.fraud_detected}
                danger
              />

              <StatCard
                icon={<CheckCircle />}
                title="Safe Transactions"
                value={summary.safe_transactions}
                success
              />

              <StatCard
                icon={<FileWarning />}
                title="Average Risk"
                value={`${summary.average_risk}%`}
              />

            </section>


            {/* ==================================================
                RISK DASHBOARD
            ================================================== */}

            <section className="dashboard-grid">


              {/* RISK DISTRIBUTION */}

              <div className="card chart-card">

                <div className="card-header">

                  <div>

                    <h3>
                      Risk Distribution
                    </h3>

                    <p>
                      Transaction risk classification
                    </p>

                  </div>

                </div>


                <div className="chart">

                  <ResponsiveContainer
                    width="100%"
                    height={280}
                  >

                    <PieChart>

                      <Pie
                        data={chartData}
                        dataKey="value"
                        nameKey="name"
                        cx="50%"
                        cy="50%"
                        outerRadius={100}
                        innerRadius={60}
                      >

                        <Cell />
                        <Cell />
                        <Cell />

                      </Pie>

                      <Tooltip />

                    </PieChart>

                  </ResponsiveContainer>

                </div>


                <div className="legend">

                  <span>
                    <i className="low"></i>
                    Low
                  </span>

                  <span>
                    <i className="medium"></i>
                    Medium
                  </span>

                  <span>
                    <i className="high"></i>
                    High
                  </span>

                </div>

              </div>


              {/* RISK OVERVIEW */}

              <div className="card risk-card">

                <div className="card-header">

                  <div>

                    <h3>
                      Risk Overview
                    </h3>

                    <p>
                      Current threat levels
                    </p>

                  </div>

                </div>


                <RiskRow
                  label="High Risk"
                  value={summary.high_risk}
                  total={summary.total_transactions}
                  type="high"
                />

                <RiskRow
                  label="Medium Risk"
                  value={summary.medium_risk}
                  total={summary.total_transactions}
                  type="medium"
                />

                <RiskRow
                  label="Low Risk"
                  value={summary.low_risk}
                  total={summary.total_transactions}
                  type="low"
                />

              </div>

            </section>


            {/* ==================================================
                HIGHEST RISK TRANSACTIONS
            ================================================== */}

            <section className="card table-card">

              <div className="card-header">

                <div>

                  <h3>
                    Highest Risk Transactions
                  </h3>

                  <p>
                    Transactions requiring immediate attention
                  </p>

                </div>


                <button
                  className="download-btn"
                  onClick={downloadReport}
                >

                  <Download size={16} />

                  Download Report

                </button>

              </div>


              <div className="table-wrapper">

                <table>

                  <thead>

                    <tr>

                      <th>
                        Transaction
                      </th>

                      <th>
                        Amount
                      </th>

                      <th>
                        Probability
                      </th>

                      <th>
                        Risk Score
                      </th>

                      <th>
                        Status
                      </th>

                    </tr>

                  </thead>


                  <tbody>

                    {data.top_risk_transactions?.map(
                      (transaction, index) => (

                        <tr key={index}>

                          <td>
                            {transaction.TransactionID ||
                              `TXN-${index + 1}`}
                          </td>


                          <td>

                            {transaction.TransactionAmt !==
                              undefined &&
                            transaction.TransactionAmt !==
                              ""
                              ? `$${transaction.TransactionAmt}`
                              : "—"}

                          </td>


                          <td>

                            {(
                              Number(
                                transaction[
                                  "Fraud Probability"
                                ]
                              ) * 100
                            ).toFixed(2)}

                            %

                          </td>


                          <td>

                            {transaction[
                              "Risk Score"
                            ]}

                          </td>


                          <td>

                            <span
                              className={`badge ${String(
                                transaction[
                                  "Risk Level"
                                ] || ""
                              ).toLowerCase()}`}
                            >

                              {transaction[
                                "Risk Level"
                              ] || "UNKNOWN"}

                            </span>

                          </td>

                        </tr>

                      )
                    )}

                  </tbody>

                </table>

              </div>

            </section>


            {/* ==================================================
                EXPLAINABLE AI
            ================================================== */}

            {data.explanations?.length > 0 && (

              <section className="card explanation-section">

                <div className="card-header">

                  <div>

                    <h3>
                      Explainable AI
                    </h3>

                    <p>
                      Understand why the AI considers
                      these transactions risky.
                    </p>

                  </div>

                  <div className="ai-badge">
                    <Brain size={15} />
                    SHAP Powered
                  </div>

                </div>


                {/* ==============================================
                    EXPLANATIONS
                ============================================== */}

                {data.explanations
                  .slice(0, 5)
                  .map((item, index) => (

                    <div
                      className="human-explanation"
                      key={index}
                    >


                      {/* ========================================
                          RISK HEADER
                      ======================================== */}

                      <div className="explanation-main">

                        <div>

                          <div className="explanation-label">

                            {item.risk_level === "HIGH"
                              ? "HIGH FRAUD RISK"
                              : item.risk_level === "MEDIUM"
                                ? "MEDIUM FRAUD RISK"
                                : "LOW FRAUD RISK"}

                          </div>


                          <h4>
                            Transaction #
                            {item.transaction_index + 1}
                          </h4>

                        </div>


                        <div
                          className={`probability ${
                            item.risk_level?.toLowerCase()
                          }`}
                        >

                          {(
                            item.fraud_probability * 100
                          ).toFixed(2)}

                          %

                        </div>

                      </div>


                      {/* ========================================
                          OVERALL EXPLANATION
                      ======================================== */}

                      <div className="why-box">

                        <div className="why-icon">

                          <Brain size={20} />

                        </div>


                        <div>

                          <strong>
                            Why was this flagged?
                          </strong>

                          <p>
                            {item.overall_explanation}
                          </p>

                        </div>

                      </div>


                      {/* ========================================
                          KEY SIGNALS
                      ======================================== */}

                      <div className="signals">

                        <h4>
                          Key signals detected
                        </h4>


                        {item.top_factors?.map(
                          (factor, factorIndex) => (

                            <div
                              className="signal"
                              key={factorIndex}
                            >

                              <div
                                className={`signal-icon ${
                                  factor.impact > 0
                                    ? "signal-danger"
                                    : "signal-safe"
                                }`}
                              >

                                {factor.impact > 0
                                  ? <ArrowUp size={15} />
                                  : <ArrowDown size={15} />
                                }

                              </div>


                              <div className="signal-content">

                                <div className="signal-title">

                                  <strong>
                                    {factor.title}
                                  </strong>


                                  <span
                                    className={
                                      factor.impact > 0
                                        ? "risk-text"
                                        : "safe-text"
                                    }
                                  >

                                    {factor.impact > 0
                                      ? "Raises risk"
                                      : "Reduces risk"}

                                  </span>

                                </div>


                                <p>
                                  {factor.explanation}
                                </p>


                                {/* Technical detail */}
                                <small>
                                  Model signal:{" "}
                                  {factor.feature}
                                </small>

                              </div>

                            </div>

                          )
                        )}

                      </div>


                      {/* ========================================
                          RECOMMENDATION
                      ======================================== */}

                      <div
                        className={`recommendation ${
                          item.risk_level?.toLowerCase()
                        }`}
                      >

                        <div className="recommendation-icon">

                          {item.risk_level === "HIGH"
                            ? <AlertTriangle size={18} />
                            : item.risk_level === "MEDIUM"
                              ? <FileWarning size={18} />
                              : <CheckCircle size={18} />
                          }

                        </div>


                        <div>

                          <strong>
                            Recommended action
                          </strong>

                          <p>
                            {item.recommendation}
                          </p>

                        </div>

                      </div>

                    </div>

                  ))}

              </section>

            )}

          </>
        )}

      </main>


      {/* ======================================================
          FOOTER
      ====================================================== */}

      <footer>

        <p>
          Techeuilla • AI Fraud Intelligence Platform
        </p>

      </footer>

    </div>
  );
}



// ============================================================
// STAT CARD
// ============================================================

function StatCard({
  icon,
  title,
  value,
  danger,
  success,
}) {

  return (

    <div className="stat-card">

      <div
        className={`stat-icon ${
          danger
            ? "danger"
            : success
              ? "success"
              : ""
        }`}
      >

        {icon}

      </div>


      <div>

        <p>
          {title}
        </p>

        <h3>
          {value}
        </h3>

      </div>

    </div>

  );
}



// ============================================================
// RISK ROW
// ============================================================

function RiskRow({
  label,
  value,
  total,
  type,
}) {

  const percentage =
    total > 0
      ? ((value / total) * 100).toFixed(1)
      : 0;


  return (

    <div className="risk-row">

      <div className="risk-info">

        <span>
          {label}
        </span>

        <strong>
          {value}
        </strong>

      </div>


      <div className="progress">

        <div
          className={`progress-fill ${type}`}
          style={{
            width: `${percentage}%`,
          }}
        ></div>

      </div>


      <small>
        {percentage}%
      </small>

    </div>

  );
}


export default App;