from __future__ import annotations

from datetime import date, timedelta
import importlib.util
import os
from pathlib import Path
import random
from typing import Any
import subprocess
import sys

import joblib
import pandas as pd
from flask import Flask, jsonify, request

BASE_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BASE_DIR.parent
DATA_PATH = BASE_DIR / "data" / "training_data.csv"
MODEL_PATH = BASE_DIR / "model" / "irrigation_model.pkl"
FEATURES_PATH = BASE_DIR / "model" / "features.pkl"
GENERATE_SCRIPT = BASE_DIR / "data" / "generate_data.py"
TRAIN_SCRIPT = BASE_DIR / "model" / "train_model.py"
WEATHER_SCRIPT = PROJECT_ROOT / "backend" / "weatherapi.py"

app = Flask(__name__)

model: Any = None
features: list[str] = []


def load_model_artifacts() -> None:
    """Load model + feature list from disk."""
    global model, features
    model = joblib.load(MODEL_PATH)
    loaded_features = joblib.load(FEATURES_PATH)
    features = list(loaded_features)


def ensure_model_artifacts_loaded() -> tuple[bool, str]:
    """Try lazy-loading model artifacts for non-__main__ server starts."""
    global model, features
    if model is not None and features:
        return True, ""

    if not MODEL_PATH.exists() or not FEATURES_PATH.exists():
        return False, "Model files not found. Run /train-model first."

    try:
        load_model_artifacts()
        return True, ""
    except Exception as exc:
        return False, f"Failed to load model artifacts: {exc}"


def _to_float_payload(payload: dict[str, Any]) -> tuple[dict[str, float] | None, list[str]]:
    missing = [name for name in features if name not in payload]
    if missing:
        return None, missing

    converted: dict[str, float] = {}
    for name in features:
        try:
            converted[name] = float(payload[name])
        except (TypeError, ValueError):
            raise ValueError(f"Invalid numeric value for '{name}'")

    return converted, []


def _predict_liters(input_payload: dict[str, float]) -> float:
    input_frame = pd.DataFrame([input_payload], columns=features)
    prediction = float(model.predict(input_frame)[0])
    return max(0.0, round(prediction, 2))


def _create_schedule_response(day_inputs: list[dict[str, float]], schedule_start: date) -> dict[str, Any]:
    schedule = []
    total_liters = 0.0
    for i, day_input in enumerate(day_inputs):
        prediction = _predict_liters(day_input)
        total_liters += prediction
        schedule.append(
            {
                "day": i + 1,
                "date": (schedule_start + timedelta(days=i)).isoformat(),
                "water_required_liters": prediction,
                "water_required_cubic_meters": round(prediction / 1000.0, 3),
                "input": day_input,
            }
        )

    return {
        "schedule_days": 7,
        "total_water_liters": round(total_liters, 2),
        "total_water_cubic_meters": round(total_liters / 1000.0, 3),
        "average_daily_liters": round(total_liters / 7.0, 2),
        "schedule": schedule,
    }


def _build_seven_day_inputs(payload: dict[str, Any]) -> list[dict[str, float]]:
    if "daily_inputs" in payload:
        daily_inputs = payload["daily_inputs"]
        if not isinstance(daily_inputs, list):
            raise ValueError("'daily_inputs' must be a list of 7 objects.")
        if len(daily_inputs) != 7:
            raise ValueError("'daily_inputs' must contain exactly 7 items.")

        validated_days: list[dict[str, float]] = []
        for day_payload in daily_inputs:
            if not isinstance(day_payload, dict):
                raise ValueError("Each entry in 'daily_inputs' must be a JSON object.")
            converted, missing = _to_float_payload(day_payload)
            if missing:
                raise ValueError(f"Missing fields in one daily input: {missing}")
            validated_days.append(converted)
        return validated_days

    base_input = payload.get("base_input")
    if not isinstance(base_input, dict):
        raise ValueError("Provide either 'daily_inputs' or a valid 'base_input' object.")

    converted_base, missing = _to_float_payload(base_input)
    if missing:
        raise ValueError(f"Missing fields in 'base_input': {missing}")

    daily_overrides = payload.get("daily_overrides", [])
    if not isinstance(daily_overrides, list):
        raise ValueError("'daily_overrides' must be a list when provided.")
    if len(daily_overrides) > 7:
        raise ValueError("'daily_overrides' can have at most 7 items.")

    seven_days: list[dict[str, float]] = []
    for i in range(7):
        day_input = dict(converted_base)
        if i < len(daily_overrides):
            override_payload = daily_overrides[i]
            if not isinstance(override_payload, dict):
                raise ValueError("Each daily override must be a JSON object.")
            for key, value in override_payload.items():
                if key not in day_input:
                    raise ValueError(f"Unknown feature in daily_overrides[{i}]: '{key}'")
                try:
                    day_input[key] = float(value)
                except (TypeError, ValueError):
                    raise ValueError(f"Invalid numeric value for '{key}' in daily_overrides[{i}]")
        seven_days.append(day_input)

    return seven_days


def _load_weather_daily_dataframe() -> pd.DataFrame:
    if not WEATHER_SCRIPT.exists():
        raise FileNotFoundError(f"Weather script not found: {WEATHER_SCRIPT}")

    spec = importlib.util.spec_from_file_location("krishineer_weatherapi", WEATHER_SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError("Failed to load weather script module.")

    weather_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(weather_module)

    daily_df = getattr(weather_module, "daily_dataframe", None)
    if not isinstance(daily_df, pd.DataFrame):
        raise ValueError("weatherapi.py did not expose a pandas DataFrame named 'daily_dataframe'.")
    if daily_df.empty:
        raise ValueError("Weather data is empty.")

    return daily_df.copy()


def _to_float_in_range(payload: dict[str, Any], key: str, low: float, high: float, default: float) -> float:
    value = payload.get(key, default)
    try:
        as_float = float(value)
    except (TypeError, ValueError):
        raise ValueError(f"Invalid numeric value for '{key}'")
    return min(high, max(low, as_float))


def _build_weather_based_inputs(payload: dict[str, Any], weather_df: pd.DataFrame) -> tuple[list[dict[str, float]], date]:
    required_weather_cols = [
        "date",
        "sunshine_duration",
        "rain_sum",
        "wind_speed_10m_max",
        "relative_humidity_2m_mean",
        "temperature_2m_mean",
    ]
    missing_cols = [col for col in required_weather_cols if col not in weather_df.columns]
    if missing_cols:
        raise ValueError(f"weatherapi.py missing required columns: {missing_cols}")

    if len(weather_df) < 7:
        raise ValueError("Weather API returned less than 7 daily rows.")

    stage = _to_float_in_range(payload, "growth_stage", 1, 4, 3)
    crop = _to_float_in_range(payload, "crop_type", 0, 4, 2)
    area = _to_float_in_range(payload, "field_area", 0.5, 1000, 2.0)

    min_sm = _to_float_in_range(payload, "soil_moisture_min", 0, 100, 25)
    max_sm = _to_float_in_range(payload, "soil_moisture_max", 0, 100, 55)
    if max_sm < min_sm:
        min_sm, max_sm = max_sm, min_sm

    seed = payload.get("soil_moisture_seed")
    rng = random.Random(seed) if seed is not None else random.Random()

    first_date = pd.to_datetime(weather_df.iloc[0]["date"]).date()
    day_inputs: list[dict[str, float]] = []
    for i in range(7):
        row = weather_df.iloc[i]
        sunshine_hours = float(row["sunshine_duration"]) / 3600.0
        day_inputs.append(
            {
                "soil_moisture": round(rng.uniform(min_sm, max_sm), 2),
                "temperature": float(row["temperature_2m_mean"]),
                "humidity": float(row["relative_humidity_2m_mean"]),
                "rainfall_forecast": float(row["rain_sum"]),
                "wind_speed": float(row["wind_speed_10m_max"]),
                "sunshine_hours": round(sunshine_hours, 2),
                "growth_stage": stage,
                "crop_type": crop,
                "field_area": area,
            }
        )

    return day_inputs, first_date


@app.after_request
def add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET,POST,OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type,Authorization"
    return response


@app.route("/", methods=["GET"])
def root():
    return jsonify(
        {
            "message": "KrishiNeer irrigation API is running",
            "endpoints": [
                "/health",
                "/features",
                "/predict",
                "/schedule-7-days",
                "/schedule-7-days-weather",
                "/generate-data",
                "/train-model",
            ],
        }
    )


@app.route("/health", methods=["GET"])
def health():
    loaded, message = ensure_model_artifacts_loaded()
    return jsonify(
        {
            "status": "ok" if loaded else "degraded",
            "model_loaded": loaded,
            "feature_count": len(features),
            "data_exists": DATA_PATH.exists(),
            "model_exists": MODEL_PATH.exists(),
            "features_exists": FEATURES_PATH.exists(),
            "message": message,
        }
    )


@app.route("/features", methods=["GET"])
def get_features():
    return jsonify({"features": features})


@app.route("/predict", methods=["POST", "OPTIONS"])
def predict():
    if request.method == "OPTIONS":
        return ("", 204)

    loaded, message = ensure_model_artifacts_loaded()
    if not loaded:
        return jsonify({"error": message}), 500

    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify({"error": "Request body must be a JSON object."}), 400

    try:
        converted, missing = _to_float_payload(payload)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    if missing:
        return jsonify({"error": "Missing required fields.", "missing_fields": missing}), 400

    prediction = _predict_liters(converted)

    return jsonify(
        {
            "water_required_liters": prediction,
            "input": converted,
        }
    )


@app.route("/schedule-7-days", methods=["POST", "OPTIONS"])
def schedule_seven_days():
    if request.method == "OPTIONS":
        return ("", 204)

    loaded, message = ensure_model_artifacts_loaded()
    if not loaded:
        return jsonify({"error": message}), 500

    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify({"error": "Request body must be a JSON object."}), 400

    try:
        day_inputs = _build_seven_day_inputs(payload)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    start_date_raw = payload.get("start_date")
    try:
        schedule_start = date.fromisoformat(start_date_raw) if start_date_raw else date.today()
    except ValueError:
        return jsonify({"error": "Invalid 'start_date'. Use ISO format: YYYY-MM-DD."}), 400

    return jsonify(_create_schedule_response(day_inputs, schedule_start))


@app.route("/schedule-7-days-weather", methods=["POST", "OPTIONS"])
def schedule_seven_days_weather():
    if request.method == "OPTIONS":
        return ("", 204)

    loaded, message = ensure_model_artifacts_loaded()
    if not loaded:
        return jsonify({"error": message}), 500

    payload = request.get_json(silent=True)
    if payload is None:
        payload = {}
    if not isinstance(payload, dict):
        return jsonify({"error": "Request body must be a JSON object."}), 400

    try:
        weather_df = _load_weather_daily_dataframe()
        day_inputs, first_date = _build_weather_based_inputs(payload, weather_df)
    except Exception as exc:
        return jsonify({"error": f"Failed to build weather schedule: {exc}"}), 500

    response = _create_schedule_response(day_inputs, first_date)
    response["source"] = "backend/weatherapi.py"
    return jsonify(response)


@app.route("/generate-data", methods=["POST"])
def generate_data():
    result = subprocess.run(
        [sys.executable, str(GENERATE_SCRIPT)],
        cwd=str(BASE_DIR),
        capture_output=True,
        text=True,
        check=False,
    )

    return jsonify(
        {
            "success": result.returncode == 0,
            "return_code": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "data_path": str(DATA_PATH),
        }
    ), (200 if result.returncode == 0 else 500)


@app.route("/train-model", methods=["POST"])
def train_model():
    result = subprocess.run(
        [sys.executable, str(TRAIN_SCRIPT)],
        cwd=str(BASE_DIR),
        capture_output=True,
        text=True,
        check=False,
    )

    if result.returncode == 0:
        load_model_artifacts()

    return jsonify(
        {
            "success": result.returncode == 0,
            "return_code": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "model_path": str(MODEL_PATH),
            "features_path": str(FEATURES_PATH),
        }
    ), (200 if result.returncode == 0 else 500)


if __name__ == "__main__":
    ensure_model_artifacts_loaded()
    host = os.getenv("ML_API_HOST", "0.0.0.0")
    port = int(os.getenv("ML_API_PORT", "5000"))
    debug = os.getenv("ML_API_DEBUG", "true").lower() == "true"
    app.run(host=host, port=port, debug=debug)
