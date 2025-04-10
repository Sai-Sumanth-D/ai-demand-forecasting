from flask import Flask, request, jsonify
from flask_cors import CORS
import logging
from groq import Groq
import json
import re
import requests

logging.basicConfig(level=logging.DEBUG)
app = Flask(__name__)
CORS(app)


groq_client = Groq(api_key='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')

#helper function to convert city to lat/lon
def geocode_location(location_name):
    url = "https://nominatim.openstreetmap.org/search"
    params = {"q": location_name, "format": "json", "limit": 1}
    headers = {"User-Agent": "ai-demand-app"}

    try:
        res = requests.get(url, params=params, headers=headers, timeout=5)
        data = res.json()
        if data:
            lat = float(data[0]["lat"])
            lon = float(data[0]["lon"])
            return lat, lon
        else:
            return None, None
    except Exception:
        return None, None

#helper function to fetch weather from Open-Meteo
def fetch_open_meteo_weather(lat, lon):
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": "temperature_2m,relative_humidity_2m,cloudcover",
        "forecast_days": 3,
        "timezone": "auto"
    }
    res = requests.get(url, params=params)
    data = res.json()
    if "hourly" not in data:
        return []
    
    # Format into records
    hourly = data["hourly"]
    return [
        {
            "datetime": hourly["time"][i],
            "temperature": hourly["temperature_2m"][i],
            "humidity": hourly["relative_humidity_2m"][i],
            "cloud_cover": hourly["cloudcover"][i]
        }
        for i in range(len(hourly["time"]))
    ]


# Helper function to extract JSON from LLM response
def extract_json(response_text):
    try:
        return json.loads(re.search(r"\{.*\}", response_text, re.DOTALL).group())
    except Exception as e:
        logging.error("Failed to parse JSON from LLM response.", exc_info=True)
        return {"error": "Failed to parse JSON from LLM response."}

# ---------- Route 1: Grid Historical Forecast ----------
@app.route("/forecast/grid", methods=["POST"])
def forecast_grid():
    try:
        records = request.get_json().get("historical_grid_data")
        if not records:
            return jsonify({"error": "Missing historical_grid_data"}), 400

        prompt = f"""
                You are an expert grid operations forecaster assisting a utility company.

                Based on the historical substation demand data provided below, generate a 7-day electricity demand forecast for each substation. Analyze recent patterns and fluctuations across substations.

                Input format:
                {records[:20]}

                Output Requirements:
                1. Return 7-day daily forecast for each substation in an array. 
                2. Each entry must include:
                    - "date" (YYYY-MM-DD format),
                    - "substation_id" (as in the input),
                    - "expected_demand" (numeric, MW).
                3. Return this data in a JSON array under key `"forecast"` that can be directly converted to a DataFrame.
                4. Also include a `"summary"` key with insights for grid managers:
                - Mention substations with high or unstable demand.
                - Speculate likely causes (e.g., heatwave, urban events).
                - Provide recommended operator actions.

                Respond ONLY in the following JSON structure:
                {{
                "forecast": [
                    {{"date": "2025-06-01", "substation_id": "Substation_A", "expected_demand": 145.8}},
                    ...
                ],
                "summary": "Substation B shows rising demand likely due to sustained heat. Prepare rerouting strategies and transformer load management."
                }}
                """
        response = groq_client.chat.completions.create(
            model="llama3-70b-8192",
            messages=[
                {"role": "system", "content": "Only respond with valid JSON."},
                {"role": "user", "content": prompt}
            ]
        )

        return jsonify(extract_json(response.choices[0].message.content.strip()))

    except Exception as e:
        logging.error("/forecast/grid error", exc_info=True)
        return jsonify({"error": "Internal Server Error"}), 500

# ---------- Route 2: Maintenance & Grid Events ----------
@app.route("/forecast/events", methods=["POST"])
def forecast_events():
    try:
        records = request.get_json().get("grid_event_schedule")
        if not records:
            return jsonify({"error": "Missing grid_event_schedule"}), 400

        prompt = f"""
                You are a smart grid AI.
                Based on these maintenance and grid events:
                {records[:10]}
                Simulate their impact on daily electricity demand per substation.

                Compare each day's original forecast vs adjusted forecast:
                Return in this format:
                {{
                "adjusted_forecast": [
                    {{
                    "date": "2025-06-02",
                    "substation_id": "Substation_A",
                    "type": "Baseline",
                    "demand": 120.5
                    }},
                    {{
                    "date": "2025-06-02",
                    "substation_id": "Substation_A",
                    "type": "After_Event",
                    "demand": 104.8
                    }},
                    ...
                ],
                "summary": "Summarize how demand shifts due to maintenance."
                }}
                """

        response = groq_client.chat.completions.create(
            model="llama3-70b-8192",
            messages=[
                {"role": "system", "content": "Only return valid JSON."},
                {"role": "user", "content": prompt}
            ]
        )

        return jsonify(extract_json(response.choices[0].message.content.strip()))

    except Exception as e:
        logging.error("/forecast/events error", exc_info=True)
        return jsonify({"error": "Internal Server Error"}), 500

# ---------- Route 3: Regional Weather Forecast ----------
@app.route("/forecast/weather", methods=["POST"])
def forecast_weather():
    try:
        records = request.get_json().get("regional_weather_data")
        if not records:
            return jsonify({"error": "Missing regional_weather_data"}), 400

        prompt = f"""
        You are forecasting 72-hour demand using this weather data:
        
        {records[:24]}
        Forecast hourly electricity and gas demand. 
        Also include a `"summary"` key with insights for grid managers:
                - Mention substations with high or unstable demand.
                - Speculate likely causes (e.g., heatwave, urban events).
                - Provide recommended operator actions.
        Format: {{"weather_adjusted_forecast": [...], "summary": "..."}}
        """

        response = groq_client.chat.completions.create(
            model="llama3-70b-8192",
            messages=[
                {"role": "system", "content": "Return valid structured JSON only."},
                {"role": "user", "content": prompt}
            ]
        )

        return jsonify(extract_json(response.choices[0].message.content.strip()))

    except Exception as e:
        logging.error("/forecast/weather error", exc_info=True)
        return jsonify({"error": "Internal Server Error"}), 500

# ---------- Route 4: Economic/Community Events ----------
@app.route("/forecast/community", methods=["POST"])
def forecast_community():
    try:
        records = request.get_json().get("community_events")
        if not records:
            return jsonify({"error": "Missing community_events"}), 400

        prompt = f"""
            You are an expert energy forecaster for utility grid operations.

            Based on the following economic/community events, forecast how electricity and gas demand will change (in percentage) over the next 7 days.

            Event Format:
            {records[:10]}

            Instructions:
            1. Predict % change in electricity and gas demand for each event, region, and day.
            2. Highlight spikes or drops caused by events.
            3. Provide a short strategic summary for grid operators.

            Respond in this JSON format:
            {{
            "forecast": [
                {{"date": "2025-06-27", "location": "Phoenix", "electricity_change_pct": 35.0, "gas_change_pct": 10.0}},
                ...
            ],
            "summary": "Phoenix expects a 35% spike in electricity demand due to a tech expo and local marathon. Operators should ensure backup supply and increase evening monitoring."
            }}
            """

        response = groq_client.chat.completions.create(
            model="llama3-70b-8192",
            messages=[
                {"role": "system", "content": "Return only clean JSON."},
                {"role": "user", "content": prompt}
            ]
        )

        return jsonify(extract_json(response.choices[0].message.content.strip()))

    except Exception as e:
        logging.error("/forecast/community error", exc_info=True)
        return jsonify({"error": "Internal Server Error"}), 500

if __name__ == '__main__':
    app.run(debug=True)
