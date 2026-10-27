"""
Automated Test Suite for SMS Spam Shield Flask Application
Tests routes, input validation, model loading, predictions, error handling,
and missing model resilience.
"""

import unittest
import json
import os
import sys

# Add parent directory to path so app can be imported
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

import app as flask_module
from app import app, MODEL_PATH


class TestSMSDefenseApp(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        self.client.testing = True

    def test_01_index_route(self):
        """Verify GET / returns 200 OK and contains brand text."""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertIn("SMS Spam Shield", html)
        self.assertIn("Know what's hiding in your messages.", html)
        self.assertIn("TF-IDF + Linear SVM", html)
        print("PASS: test_01_index_route")

    def test_02_health_endpoint(self):
        """Verify GET /api/health returns healthy and model_loaded status."""
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn("status", data)
        self.assertIn("model_loaded", data)
        self.assertTrue(data["model_loaded"])
        self.assertEqual(data["status"], "healthy")
        self.assertEqual(data["supported_labels"], ["spam", "ham"])
        print(f"PASS: test_02_health_endpoint (model_loaded={data['model_loaded']})")

    def test_03_empty_message_validation(self):
        """Verify POST /api/predict rejects empty or whitespace-only messages."""
        # Empty string
        res1 = self.client.post(
            "/api/predict",
            data=json.dumps({"message": ""}),
            content_type="application/json"
        )
        self.assertEqual(res1.status_code, 400)
        self.assertFalse(res1.get_json()["success"])

        # Whitespace only
        res2 = self.client.post(
            "/api/predict",
            data=json.dumps({"message": "   \n\t  "}),
            content_type="application/json"
        )
        self.assertEqual(res2.status_code, 400)
        self.assertFalse(res2.get_json()["success"])
        print("PASS: test_03_empty_message_validation")

    def test_04_missing_field_validation(self):
        """Verify POST /api/predict rejects missing 'message' field."""
        response = self.client.post(
            "/api/predict",
            data=json.dumps({"text": "Hello world"}),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 400)
        data = response.get_json()
        self.assertFalse(data["success"])
        self.assertIn("Missing required 'message' field", data["error"])
        print("PASS: test_04_missing_field_validation")

    def test_05_malformed_json_validation(self):
        """Verify POST /api/predict handles non-JSON or malformed payload safely."""
        # Missing Content-Type
        res1 = self.client.post(
            "/api/predict",
            data="Not JSON",
            content_type="text/plain"
        )
        self.assertEqual(res1.status_code, 400)

        # Broken JSON syntax
        res2 = self.client.post(
            "/api/predict",
            data='{"message": "Broken...',
            content_type="application/json"
        )
        self.assertEqual(res2.status_code, 400)
        print("PASS: test_05_malformed_json_validation")

    def test_06_spam_prediction(self):
        """Verify known spam message reaches real model and returns 'spam'."""
        spam_text = (
            "URGENT! You have won a 1-week family holiday to Florida. "
            "Call 09012345678 now to claim. T&Cs apply."
        )
        response = self.client.post(
            "/api/predict",
            data=json.dumps({"message": spam_text}),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data["success"])
        self.assertEqual(data["prediction"], "spam")
        self.assertEqual(data["message"], spam_text)
        self.assertIn("timestamp", data)
        print(f"PASS: test_06_spam_prediction -> label: {data['prediction']}")

    def test_07_ham_prediction(self):
        """Verify known legitimate message reaches real model and returns 'ham'."""
        ham_text = "Hey mate, are we still meeting for lunch today at 1?"
        response = self.client.post(
            "/api/predict",
            data=json.dumps({"message": ham_text}),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data["success"])
        self.assertEqual(data["prediction"], "ham")
        self.assertEqual(data["message"], ham_text)
        self.assertIn("timestamp", data)
        print(f"PASS: test_07_ham_prediction -> label: {data['prediction']}")

    def test_08_prediction_label_constraint(self):
        """Verify predictions are strictly restricted to 'spam' or 'ham'."""
        samples = [
            "WINNER!! As a valued customer you have been selected to receive a prize.",
            "Can you pick up milk on your way home?",
            "FREE ringtone! Reply YES to 80088 to activate subscription.",
            "I'm on my way, traffic is a bit heavy."
        ]
        for s in samples:
            resp = self.client.post(
                "/api/predict",
                data=json.dumps({"message": s}),
                content_type="application/json"
            )
            data = resp.get_json()
            self.assertIn(data["prediction"], ["spam", "ham"])
        print("PASS: test_08_prediction_label_constraint (all 4 samples returned valid labels)")

    def test_09_missing_model_resilience(self):
        """Verify app does not crash if model is None and returns 503 cleanly."""
        original_model = flask_module.model
        try:
            # Simulate missing model
            flask_module.model = None

            # Health route should report degraded
            health_res = self.client.get("/api/health")
            self.assertEqual(health_res.status_code, 200)
            self.assertFalse(health_res.get_json()["model_loaded"])

            # Predict route should return 503
            predict_res = self.client.post(
                "/api/predict",
                data=json.dumps({"message": "Test message"}),
                content_type="application/json"
            )
            self.assertEqual(predict_res.status_code, 503)
            self.assertFalse(predict_res.get_json()["success"])
            print("PASS: test_09_missing_model_resilience")
        finally:
            flask_module.model = original_model


if __name__ == "__main__":
    unittest.main()
