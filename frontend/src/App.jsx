import { useState } from "react";
import axios from "axios";
import {
  ShieldCheck,
  Upload,
  AlertTriangle,
  CheckCircle,
  Activity,
  FileWarning,
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

  const summary = data?.summary;

  const chartData = summary
    ? [
        { name: "Low Risk", value: summary.low_risk },
        { name: "Medium Risk", value: summary.medium_risk },
        { name: "High Risk", value: summary.high_risk },
      ]
    : [];

  return (
    <div className="app">
      <header className="header">
        <div className="brand">
          <div className="logo">
            <ShieldCheck size={28} />
          </div>

          <div>
            <h1>Techeuilla</h1>
            <p>Financial Fraud Detection</p>
          </div>
        </div>

        <div className="status">
          <span className="status-dot"></span>
          AI Engine Online
        </div>
      </header>

      <main className="container">
        <section className="hero">
          <div>
            <p className="eyebrow">AI-POWERED TRANSACTION ANALYSIS</p>

            <h2>
              Detect suspicious transactions
              <span> before they become fraud.</span>
            </h2>

            <p className="hero-text">
              Upload transaction data and let our XGBoost fraud detection
              engine identify high-risk activity.
            </p>
          </div>
        </section>

        <section className="upload-card">
          <div className="upload-icon">
            <Upload size={30} />
          </div>

          <h3>Upload Transaction Data</h3>

          <p>
            Upload a CSV file containing engineered transaction features.
          </p>

          <label className="file-input">
            <input
              type="file"
              accept=".csv"
              onChange={(e) => setFile(e.target.files[0])}
            />

            <span>
              {file ? file.name : "Choose CSV file"}
            </span>
          </label>

          <button
            className="analyze-btn"
            onClick={analyzeFile}
            disabled={loading}
          >
            {loading ? "Analyzing..." : "Analyze Transactions"}
          </button>

          {error && <div className="error">{error}</div>}
        </section>

        {data && summary && (
          <>
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

            <section className="dashboard-grid">
              <div className="card chart-card">
                <div className="card-header">
                  <div>
                    <h3>Risk Distribution</h3>
                    <p>Transaction risk classification</p>
                  </div>
                </div>

                <div className="chart">
                  <ResponsiveContainer width="100%" height={280}>
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
                        {chartData.map((_, index) => (
                          <Cell key={index} />
                        ))}
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

              <div className="card risk-card">
                <div className="card-header">
                  <div>
                    <h3>Risk Overview</h3>
                    <p>Current threat levels</p>
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

            <section className="card table-card">
              <div className="card-header">
                <div>
                  <h3>Highest Risk Transactions</h3>
                  <p>Transactions requiring immediate attention</p>
                </div>
              </div>

              <div className="table-wrapper">
                <table>
                  <thead>
                    <tr>
                      <th>Transaction</th>
                      <th>Amount</th>
                      <th>Probability</th>
                      <th>Risk Score</th>
                      <th>Status</th>
                    </tr>
                  </thead>

                  <tbody>
                    {data.top_risk_transactions.map((transaction, index) => (
                      <tr key={index}>
                        <td>
                          {transaction.TransactionID || `TXN-${index + 1}`}
                        </td>

                        <td>
                          {transaction.TransactionAmt
                            ? `$${transaction.TransactionAmt}`
                            : "—"}
                        </td>

                        <td>
                          {(
                            Number(transaction["Fraud Probability"]) * 100
                          ).toFixed(2)}
                          %
                        </td>

                        <td>
                          {transaction["Risk Score"]}
                        </td>

                        <td>
                          <span
                            className={`badge ${String(
                              transaction["Risk Level"]
                            ).toLowerCase()}`}
                          >
                            {transaction["Risk Level"]}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
          </>
        )}
      </main>

      <footer>
        <p>Techeuilla • AI Fraud Intelligence Platform</p>
      </footer>
    </div>
  );
}

function StatCard({ icon, title, value, danger, success }) {
  return (
    <div className="stat-card">
      <div
        className={`stat-icon ${
          danger ? "danger" : success ? "success" : ""
        }`}
      >
        {icon}
      </div>

      <div>
        <p>{title}</p>
        <h3>{value}</h3>
      </div>
    </div>
  );
}

function RiskRow({ label, value, total, type }) {
  const percentage =
    total > 0 ? ((value / total) * 100).toFixed(1) : 0;

  return (
    <div className="risk-row">
      <div className="risk-info">
        <span>{label}</span>
        <strong>{value}</strong>
      </div>

      <div className="progress">
        <div
          className={`progress-fill ${type}`}
          style={{ width: `${percentage}%` }}
        ></div>
      </div>

      <small>{percentage}%</small>
    </div>
  );
}

export default App;