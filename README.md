# SMS Spam Shield — AI-Powered SMS Threat Detection

[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![Framework](https://img.shields.io/badge/framework-Flask-lightgrey.svg)](https://flask.palletsprojects.com/)
[![Machine Learning](https://img.shields.io/badge/ML-scikit--learn-orange.svg)](https://scikit-learn.org/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

**SMS Spam Shield** is a production-grade, cybersecurity-focused web application designed to classify mobile short messages (SMS) as either **Spam** or **Ham** (legitimate).

The application features a modern dark-navy SaaS interface inspired by Linear and Stripe, backed by a high-performance Flask API executing an uncalibrated maximum-margin Support Vector Machine pipeline (`LinearSVC` + `TfidfVectorizer`).

---

## Architecture Overview

```
                                      +--------------------------+
                                      |   Client Web Browser     |
                                      | (Vanilla JS + Fetch API) |
                                      +------------+-------------+
                                                   |
                                                   | HTTP POST /api/predict
                                                   v
+--------------------------------------------------+--------------------------------------------------+
| Flask Application (app.py)                                                                         |
|                                                                                                    |
|  [Input Validation] ---> [In-Memory TF-IDF Transform] ---> [LinearSVC Hyperplane] ---> [JSON Output] |
|                                                                                                    |
|  * Loaded once at startup via Joblib: spam_model.pkl (470 KB)                                      |
|  * In-memory inference only; zero database writes or message persistence                         |
+----------------------------------------------------------------------------------------------------+
```

### Machine Learning Specifications

The model pipeline is trained on standardized SMS threat datasets and serialized using `joblib`:
- **Vectorization**: `TfidfVectorizer` (sublinear term frequency scaling, unigram + bigram n-gram range `(1, 2)`, English stop words removed, maximum 10,000 features).
- **Classifier**: `LinearSVC(class_weight='balanced')` — finds the optimal hyperplane separating malicious and benign text.
- **Labels**: `spam`, `ham`.

---

## Directory Structure

```
SMS-Spam-Shield/
├── app.py                  # Core Flask server and API routes
├── spam_model.pkl          # Serialized scikit-learn ML pipeline
├── requirements.txt        # Pinned runtime dependencies
├── .gitignore              # Ignored files (caches, venvs, secrets)
├── README.md               # Project documentation and setup guide
├── templates/
│   └── index.html          # Semantic HTML5 user interface
└── static/
    ├── style.css           # Cybersecurity SaaS dark-mode CSS
    └── script.js           # Client-side validation and Fetch controller
```

---

## Model Placement

The application expects the pre-trained model file at:

```
./spam_model.pkl
```

Place `spam_model.pkl` directly in the project root directory alongside `app.py`. If the model is missing or fails to load, the server starts in a degraded state without crashing, and reports the error via `/api/health`.

---

## Installation & Local Execution

### 1. Prerequisites
- Python 3.10+ (compatible with Python 3.10, 3.11, 3.12, 3.13, 3.14)
- Git

### 2. Clone Repository
```bash
git clone https://github.com/elsa-0907/hanaml.git
cd hanaml
```

### 3. Create Virtual Environment (Optional but Recommended)
```bash
python -m venv .venv

# On Windows:
.venv\Scripts\activate

# On macOS/Linux:
source .venv/bin/activate
```

### 4. Install Dependencies
```bash
pip install -r requirements.txt
```

### 5. Launch the Application
```bash
python app.py
```

The server will start and print the local URL:
```
 * SMS Spam Shield running on http://127.0.0.1:5000
```

Open `http://127.0.0.1:5000` in your web browser.

---

## API Documentation

### 1. Health Status
Check if the service and machine learning model are operational.

- **URL**: `/api/health`
- **Method**: `GET`
- **Response `200 OK`**:
```json
{
  "status": "healthy",
  "model_loaded": true,
  "model_file": "spam_model.pkl",
  "model_type": "TF-IDF + LinearSVC Pipeline",
  "supported_labels": ["spam", "ham"],
  "timestamp": "2026-10-27T14:48:00.123456+00:00"
}
```

### 2. Predict Message Classification
Analyze an incoming SMS message.

- **URL**: `/api/predict`
- **Method**: `POST`
- **Headers**: `Content-Type: application/json`
- **Request Body**:
```json
{
  "message": "URGENT! You have won a 1-week family holiday to Florida. Call 09012345678 now to claim."
}
```

- **Success Response `200 OK`**:
```json
{
  "success": true,
  "prediction": "spam",
  "message": "URGENT! You have won a 1-week family holiday to Florida. Call 09012345678 now to claim.",
  "timestamp": "2026-10-27T14:48:05.123456+00:00"
}
```

- **Validation Error `400 Bad Request`**:
```json
{
  "success": false,
  "error": "Message text cannot be empty or whitespace only."
}
```

- **Service Unavailable `503 Service Unavailable`** (when model is missing):
```json
{
  "success": false,
  "error": "Spam classification model is currently unavailable on the server. Please check system status."
}
```

---

## Data Privacy & Security

- **In-Memory Classification**: Messages submitted to `/api/predict` are evaluated directly in RAM.
- **Zero Logging of Message Body**: SMS message payloads are omitted from system access logs to safeguard confidential information.
- **No Database Persistence**: The system does not write messages to disk or external databases.
- **Sanitized Frontend Rendering**: All user text is rendered safely using standard DOM property assignments (`textContent`), eliminating Cross-Site Scripting (XSS) vectors.

---

## Model Limitations & Result Integrity

1. **Linear Support Vector Classifier**: `LinearSVC` calculates decision boundaries using hyperplanes rather than calibrated probabilities. Therefore, artificial confidence percentages (e.g. "98.4% confident") are intentionally not shown or fabricated.
2. **Ham Is Not Guaranteed Safe**: A "Ham" prediction signifies that the model identified characteristics consistent with benign messages in its training distribution. It does not provide an absolute guarantee that a message is harmless.
3. **Evolving Attack Vectors**: Highly customized spear-phishing or novel obfuscation techniques may bypass static n-gram models. Always verify sensitive requests out-of-band.

---

## Production Deployment Considerations

- **WSGI / ASGI Server**: In production environments, run Flask behind a production WSGI server such as `Gunicorn` or `Waitress`:
  ```bash
  # Linux:
  gunicorn -w 4 -b 0.0.0.0:8000 app:app

  # Windows:
  waitress-serve --port=8000 app:app
  ```
- **Reverse Proxy**: Place the application behind Nginx or Cloudflare to handle SSL termination, rate-limiting, and DDoS protection.
- **Model Storage**: For Docker / Kubernetes deployments, package `spam_model.pkl` in the container image or fetch it from secure cloud storage (AWS S3, Google Cloud Storage) during container initialization.
