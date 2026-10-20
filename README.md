
# FraudLens – Machine Learning-Based Financial Transaction Fraud Detection System

FraudLens is a machine learning-based financial transaction fraud detection prototype that scores transactions, estimates potential fraud risk, and provides an interactive dashboard for monitoring transaction activity. It combines an XGBoost classification model with behavioral feature engineering, a FastAPI backend, SQLite persistence, and a React dashboard, deployed on AWS.

The system supports manual transaction analysis and a replay stream that processes previously unseen test records through the same scoring and persistence workflow.

## Key Features

- **Machine Learning-Based Scoring:** Uses a trained XGBoost classifier to estimate the probability of a transaction being fraudulent.
- **Behavioral Feature Engineering:** Derives transaction, temporal, historical spending, velocity, device, and country-related features.
- **Risk Classification:** Maps model scores to `LOW`, `MEDIUM`, and `HIGH` risk categories using a configurable risk policy.
- **Interactive Dashboard:** Provides pages for overview statistics, transaction analysis, transaction history, user details, alerts, and system status.
- **Transaction Replay:** Processes unseen test records sequentially to simulate incoming transaction activity.
- **Persistent Storage:** Stores scored transactions, generated alerts, and replay progress in SQLite.
- **Cloud Deployment:** Hosts the application on Amazon EC2, with Nginx serving the frontend and routing API requests.
- **AWS Configuration Management:** Uses a private Amazon S3 bucket and an EC2 IAM role to retrieve the risk-policy configuration in the deployed environment.

## Technology Stack

| Component | Technology |
|---|---|
| Programming Language | Python |
| Machine Learning | XGBoost, scikit-learn |
| Backend API | FastAPI, Uvicorn |
| Frontend | React, Vite, JavaScript |
| Database | SQLite |
| Cloud Compute | Amazon EC2 |
| Object Storage | Amazon S3 |
| Access Management | AWS IAM |
| Web Server / Reverse Proxy | Nginx |
| Testing | pytest |

## System Architecture




The React frontend communicates with the FastAPI backend through HTTP requests. Nginx serves the built frontend and proxies API requests to the backend, which listens on the local interface.

The backend validates transaction inputs, constructs the required features, performs model inference, assigns a risk category, and persists the result. When a high-risk transaction meets the alerting policy, an alert is stored for review.

In the deployed environment, the backend can retrieve its risk-policy configuration from S3 using the EC2 instance's IAM role rather than hard-coded AWS credentials.

## Machine Learning Approach

### Model and Features

FraudLens uses a supervised XGBoost binary classification model. The model produces a fraud probability for each scored transaction.

The feature-engineering pipeline provides **27 model features**, covering areas such as:

- Transaction attributes, including amount, merchant category, country, and channel.
- Temporal gaps and rapid-transaction indicators.
- Previous transaction amounts and transaction counts.
- Historical spending statistics and spending deviations.
- Device, country, and merchant changes.
- Novelty indicators and transaction velocity signals.

The backend constructs the model inputs from transaction data and its available historical context. Raw high-cardinality identifiers are not directly treated as ordinary predictive features.

### Model Evaluation

The project uses a chronological validation approach in its documented model experiments to better reflect the challenge of predicting future transactions from historical data.

The tuned XGBoost experiment previously recorded the following validation metrics:

| Metric | Recorded Value |
|---|---:|
| ROC-AUC | 0.5263 |
| PR-AUC | 0.0212 |
| Precision at the selected operating point | 0.0336 |
| Recall at the selected operating point | 0.1081 |
| F1-score at the selected operating point | 0.0512 |

These are experimental validation results, not a guarantee of live performance. They indicate that the current model has substantial room for improvement. Fraud detection is also affected by severe class imbalance, so accuracy alone would not be an adequate evaluation measure.

The project prioritizes transparent evaluation and a working scoring workflow rather than claiming production-grade detection performance.

## Risk Classification

FraudLens separates the model's estimated fraud probability from its human-readable risk category.

The deployed risk policy uses configurable score boundaries:

| Risk Level | Score Range | Intended Handling |
|---|---|---|
| `LOW` | Below 0.35 | Lower-risk transaction |
| `MEDIUM` | 0.35 to below 0.55 | Further verification may be appropriate |
| `HIGH` | 0.55 and above | Flag for alerting or analyst review |

The fraud decision threshold is configured separately from the risk-category boundaries. Risk categories describe the operational handling of a score; they are not proof that a transaction is fraudulent or legitimate.

These values describe the current configuration and may be adjusted as the model and policy evolve.

## Application Pages

### 1. Overview

Displays dashboard statistics and recent transaction activity. The replay controls allow the user to start, pause, or step through the prepared transaction stream.

### 2. Analyze

Accepts transaction details for direct scoring through the backend API and displays the resulting fraud-risk assessment.

### 3. Transactions

Provides transaction history with search, filtering, pagination, and transaction-level risk and decision information.

### 4. Users

Displays available user-level transaction statistics and related activity from persisted records.

### 5. Alerts

Lists alerts generated by the high-risk policy, supporting review of transactions that meet the configured alerting criteria.

### 6. System Status

Displays system information such as backend health, database connectivity, model information, risk-policy configuration, and replay progress.

## Backend API Reference

The FastAPI backend exposes the following endpoints:

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/health` | Basic backend health check |
| `GET` | `/system/status` | Model, database, and replay status |
| `POST` | `/score` | Score a manually submitted transaction |
| `POST` | `/stream/next` | Process the next unseen replay record |
| `GET` | `/stream/status` | Retrieve replay progress |
| `GET` | `/dashboard/overview` | Retrieve dashboard summary data |
| `GET` | `/transactions` | List transactions with pagination and filters |
| `GET` | `/transactions/{id}` | Retrieve a transaction record |
| `GET` | `/users` | List users |
| `GET` | `/users/{id}` | Retrieve user details |
| `GET` | `/alerts` | List alerts with available filters |
| `GET` | `/alerts/{id}` | Retrieve an alert record |

Interactive API documentation is available through FastAPI's Swagger UI when the deployment exposes the `/docs` route.

## Database and Persistence

FraudLens uses SQLite for local application persistence.

The database contains three principal tables:

- **`transactions`** — Stores scored transaction details, model scores, risk categories, decisions, and available feature data.
- **`alerts`** — Stores alert records associated with transactions that meet the alerting policy.
- **`stream_state`** — Stores replay progress and cursor information.

The backend initializes the database and reconstructs the available application state at startup. Transaction persistence and replay progress allow the application to resume from stored state rather than treating every request as an isolated operation.

SQLite is appropriate for this prototype, but its concurrency and scaling characteristics limit its suitability for a high-volume production payment system.

## AWS Deployment

FraudLens is deployed on an Amazon EC2 Linux instance in the Mumbai AWS region.

### Amazon EC2

Hosts the backend and deployed application files.

### Nginx

Serves the built React frontend and forwards API requests to the FastAPI backend running on the local interface.

### Amazon S3

Stores the risk-policy configuration separately from application code. The deployed backend retrieves the configuration during startup and supports a local fallback.

### AWS IAM

An IAM role attached to the EC2 instance authorizes the backend's required S3 operations without embedding long-term AWS access keys in the application.

This arrangement demonstrates a basic cloud deployment and a safer approach to application configuration access.

**Security note:** The repository documentation intentionally excludes the AWS account ID, public IP address, public DNS hostname, private key, and credentials. The application is an educational prototype and should not be considered production-ready for financial transactions.

## Local Setup

### Prerequisites

- Python and pip
- Node.js and npm
- Git

### 1. Clone the Repository

```bash
git clone https://github.com/hareesh-n/FraudLens.git
cd FraudLens
```

### 2. Create a Python Environment

```bash
python -m venv .venv
```

Activate the environment on Windows:

```powershell
.\.venv\Scripts\Activate.ps1
```

On Linux or macOS:

```bash
source .venv/bin/activate
```

Install the Python dependencies:

```bash
pip install -r requirements.txt
```

### 3. Prepare the Model and Data

The model artifacts and datasets are maintained separately from the Git-tracked application source. Ensure that the required training or inference files are available in the expected local paths before running the application.

Refer to the training scripts under `src/` for the model-training workflow.

### 4. Start the Backend

From the project root, run:

```bash
uvicorn src.api:app --reload
```

The API will normally be available at:

```text
http://127.0.0.1:8000
```

Check backend health at [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health).

### 5. Start the Frontend

Open a second terminal and run:

```bash
cd frontend
npm install
npm run dev
```

Open the local URL printed by Vite in the terminal. The frontend development server uses the configured API proxy to communicate with FastAPI.

**Note:** Local execution requires the expected model and dataset artifacts. AWS-hosted configuration access additionally depends on the deployed environment's IAM permissions and configuration setup.

## Testing

The project includes a pytest suite for backend functionality. Tests cover areas such as:

- API health and system status.
- Manual and replay-based transaction scoring.
- Database persistence and CRUD operations.
- Replay progress and end-of-stream handling.

Run the available tests from the project root:

```bash
pytest
```

The test suite should be run in the environment configured with the project's required dependencies and test fixtures.

## Limitations and Future Improvements

FraudLens demonstrates an end-to-end prototype, but several improvements are necessary before real financial use:

- **Model quality:** Improve discrimination, precision, and recall through better features, data quality, calibration, and further evaluation.
- **Authentication and authorization:** Protect API endpoints from unauthorized access.
- **Transport security:** Configure HTTPS and appropriate security headers.
- **Database scalability:** Consider PostgreSQL or another managed relational database for higher concurrency and operational reliability.
- **Monitoring:** Add structured application logs, metrics, and CloudWatch integration.
- **Service reliability:** Configure supervised backend startup, recovery, and deployment automation.
- **Data ingestion:** Replace the prepared CSV replay with an integration to a real event source if appropriate.
- **Model lifecycle:** Establish reproducible training, evaluation, versioning, and deployment procedures.
- **Behavioral state management:** Improve efficient incremental state updates and handling of previously unseen users or devices.
- **Testing:** Expand automated tests, security checks, and deployment validation.

The current replay stream uses prepared test records to simulate incoming transactions. It is not a connection to a live payment gateway or banking system.

## Project Structure

```text
FraudLens/
├── src/
│   ├── api.py
│   ├── scoring.py
│   ├── persistence.py
│   ├── stream.py
│   ├── feature_engineering.py
│   ├── realtime_feature_engine.py
│   ├── train.py
│   └── tune_xgboost.py
├── frontend/
│   ├── src/
│   │   ├── pages/
│   │   ├── components/
│   │   └── api/
│   ├── package.json
│   └── vite.config.js
├── tests/
├── requirements.txt
├── .gitignore
└── README.md
```

Datasets, trained model artifacts, virtual environments, local databases, and frontend build outputs are excluded from version control where configured in `.gitignore`.

## Key Learnings

Building FraudLens brought together several areas of software engineering and machine learning:

- Designing a feature-engineering pipeline for behavioral transaction analysis.
- Integrating an ML classifier into a REST API.
- Persisting scoring results and replay progress in a database.
- Building a React dashboard around backend APIs.
- Deploying an application on EC2 with Nginx.
- Using IAM roles and private S3 storage for cloud-based configuration access.
- Evaluating model performance under class imbalance and documenting limitations honestly.

## Conclusion

FraudLens demonstrates how machine learning, backend engineering, frontend development, database persistence, and AWS services can be combined into a cloud-hosted financial fraud detection prototype.

It provides a foundation for further work in model quality, secure API design, scalable data processing, and reliable cloud operations.
