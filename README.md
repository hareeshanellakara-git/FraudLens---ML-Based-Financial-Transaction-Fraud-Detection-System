# FraudLens – Financial Transaction Fraud Detection System

FraudLens is a machine learning-based application that analyzes financial transactions, estimates potential fraud risk, and presents the results through an interactive dashboard. It combines a machine learning model, backend services, and a web interface to support transaction risk analysis.

## Features

- **Overview Dashboard:** Displays transaction statistics, risk summaries, and recent activity.
- **Analyze Transactions:** Allows users to submit transaction details for fraud-risk analysis.
- **Transaction History:** Displays previously analyzed transactions and their risk information.
- **User Overview:** Provides a view of users and their associated transaction activity.
- **Alerts:** Highlights high-risk transactions and relevant alerts.
- **System Status:** Presents information about the application's operational status.
- **CSV Transaction Replay:** Supports analyzing prepared transaction records through the scoring API.

## How It Works

1. Transaction details are submitted through the dashboard or CSV replay workflow.
2. The backend validates the input and prepares the required features.
3. The machine learning model estimates the transaction's fraud probability.
4. Configured thresholds are used to determine the fraud decision and risk category.
5. Results are stored and displayed through the dashboard, with alerts generated where applicable.

## Technologies Used

- **Frontend:** React, Vite
- **Backend:** Python, FastAPI
- **Machine Learning:** XGBoost
- **Database:** SQLite
- **Cloud Platform:** AWS EC2, AWS S3, AWS IAM
- **Web Server:** Nginx

## Project Goal

FraudLens demonstrates how machine learning, backend services, and cloud deployment can be integrated into an application for financial transaction fraud-risk analysis.

---

**FraudLens** — *From transaction data to informed decisions.*