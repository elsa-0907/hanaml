"""
SMS Spam Shield - Flask Web Application
Production-style backend for SMS spam and threat detection using a trained
scikit-learn TF-IDF + LinearSVC pipeline.
"""

import os
import sys
import logging
from datetime import datetime, timezone
import warnings

from flask import Flask, render_template, request, jsonify
import joblib

# Suppress unpickling version warnings gracefully while keeping code operational
warnings.filterwarnings(
    "ignore",
    category=UserWarning,
    module="sklearn"
)

# Configure structured logging without logging sensitive message payloads
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("SMS-Spam-Shield")

app = Flask(__name__)

# Base path configuration
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_FILENAME = "spam_model.pkl"
MODEL_PATH = os.path.join(BASE_DIR, MODEL_FILENAME)

# Global model container loaded once at application startup
model = None
model_load_error = None


def load_model():
    """
    Loads the trained scikit-learn model pipeline from disk using joblib.
    Handles missing or incompatible model files gracefully without crashing the server.
    """
    global model, model_load_error

    if not os.path.exists(MODEL_PATH):
        model_load_error = f"Model file '{MODEL_FILENAME}' was not found at {MODEL_PATH}."
        logger.warning(model_load_error)
        model = None
        return False

    try:
        logger.info(f"Loading trained spam detection model from: {MODEL_PATH}")
        loaded = joblib.load(MODEL_PATH)

        # Validate that the loaded object exposes the predict interface
        if not hasattr(loaded, "predict"):
            raise TypeError("Loaded model object does not implement a 'predict' method.")

        model = loaded
        model_load_error = None
        logger.info("Spam detection model loaded successfully.")
        return True
    except Exception as exc:
        model = None
        model_load_error = f"Failed to load model: {type(exc).__name__}"
        logger.error(f"Error loading model from '{MODEL_FILENAME}': {exc}", exc_info=False)
        return False


# Attempt loading the model during application initialization
load_model()


@app.route("/", methods=["GET"])
def index():
    """Serves the primary web interface."""
    return render_template("index.html")


@app.route("/api/health", methods=["GET"])
def health():
    """
    Health check endpoint reporting application and model availability.
    Enables frontend UI to accurately reflect backend model state.
    """
    is_ready = model is not None
    response_data = {
        "status": "healthy" if is_ready else "degraded",
        "model_loaded": is_ready,
        "model_file": MODEL_FILENAME,
        "model_type": "TF-IDF + LinearSVC Pipeline" if is_ready else None,
        "supported_labels": ["spam", "ham"],
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

    if not is_ready:
        response_data["message"] = (
            "Model is currently unavailable. Place 'spam_model.pkl' in the project directory."
        )

    return jsonify(response_data), 200


@app.route("/api/predict", methods=["POST"])
def predict():
    """
    Classifies a submitted SMS message as 'spam' or 'ham'.
    Validates input and ensures predictions originate solely from the trained model.
    """
    # Validate Content-Type
    if not request.is_json:
        return jsonify({
            "success": False,
            "error": "Request body must be JSON with 'Content-Type: application/json'."
        }), 400

    payload = request.get_json(silent=True)
    if payload is None:
        return jsonify({
            "success": False,
            "error": "Malformed JSON payload."
        }), 400

    # Validate presence of message field
    if "message" not in payload:
        return jsonify({
            "success": False,
            "error": "Missing required 'message' field in request body."
        }), 400

    raw_message = payload.get("message")
    if not isinstance(raw_message, str):
        return jsonify({
            "success": False,
            "error": "The 'message' field must be a valid string."
        }), 400

    clean_message = raw_message.strip()
    if not clean_message:
        return jsonify({
            "success": False,
            "error": "Message text cannot be empty or whitespace only."
        }), 400

    if len(raw_message) > 5000:
        return jsonify({
            "success": False,
            "error": "Message exceeds maximum allowed length of 5,000 characters."
        }), 400

    # Check model readiness
    if model is None:
        logger.warning("Prediction requested but model is not available.")
        return jsonify({
            "success": False,
            "error": "Spam classification model is currently unavailable on the server. Please check system status."
        }), 503

    try:
        # Perform actual prediction using the loaded pipeline
        raw_pred = model.predict([clean_message])[0]
        prediction = str(raw_pred).strip().lower()

        # Enforce canonical 'spam' or 'ham' output
        if prediction not in ("spam", "ham"):
            if prediction in ("1", "true"):
                prediction = "spam"
            elif prediction in ("0", "false"):
                prediction = "ham"
            else:
                prediction = "spam" if "spam" in prediction else "ham"

        timestamp = datetime.now(timezone.utc).isoformat()
        logger.info(f"Classified message length={len(clean_message)} chars as '{prediction}'")

        return jsonify({
            "success": True,
            "prediction": prediction,
            "message": clean_message,
            "timestamp": timestamp
        }), 200

    except Exception as exc:
        logger.error(f"Error during model prediction: {type(exc).__name__}", exc_info=False)
        return jsonify({
            "success": False,
            "error": "An internal error occurred while analyzing the message."
        }), 500


@app.errorhandler(404)
def handle_404(e):
    if request.path.startswith("/api/"):
        return jsonify({"success": False, "error": "API endpoint not found."}), 404
    return render_template("index.html"), 404


@app.errorhandler(405)
def handle_405(e):
    return jsonify({"success": False, "error": "HTTP method not allowed."}), 405


@app.errorhandler(500)
def handle_500(e):
    return jsonify({"success": False, "error": "Internal server error."}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"\n=======================================================")
    print(f" SMS Spam Shield - AI Threat Detection Service")
    print(f" Model Status: {'LOADED' if model is not None else 'NOT FOUND'}")
    print(f" Running on: http://127.0.0.1:{port}")
    print(f"=======================================================\n")
    app.run(host="127.0.0.1", port=port, debug=False)
