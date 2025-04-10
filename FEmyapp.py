
import streamlit as st
import pandas as pd
import altair as alt
import requests
import sys
import os
import json


sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.myapp import fetch_open_meteo_weather, geocode_location



# Set page configuration
st.set_page_config(page_title="AI-Powered Demand Forecasting", layout="wide")

# Initialize session state
if 'page' not in st.session_state:
    st.session_state.page = 'Home'

# Enhanced CSS with Mac OS-like hover animations
st.markdown("""
<style>
    .main-title {
        font-size: 40px;
        font-weight: 700;
        color: #4CAF50;
    }
    .subtitle {
        font-size: 20px;
        color: #b0b0b0;
        margin-bottom: 25px;
    }
    .card {
        padding: 20px;
        border-radius: 10px;
        background-color: #1e1e1e;
        box-shadow: 0 2px 4px rgba(0,0,0,0.2);
        margin-top: 20px;
    }
    .stButton > button {
        width: 100%;
        border-radius: 10px;
        border: none;
        background-color: #4CAF50;
        color: white;
        padding: 10px;
        font-size: 16px;
        transition: transform 0.2s ease-in-out, box-shadow 0.2s ease-in-out;
    }
    .stButton > button:hover {
        transform: translateY(-5px);
        box-shadow: 0 10px 20px rgba(76, 175, 80, 0.3);
    }
</style>
""", unsafe_allow_html=True)

# Navigation Bar
col1, col2, col3 = st.columns(3)
with col1:
    if st.button("🏠 Home"):
        st.session_state.page = "Home"
with col2:
    if st.button("📈 Forecasting"):
        st.session_state.page = "Forecasting"
with col3:
    if st.button("🔗 API Info"):
        st.session_state.page = "API Info"

# Display pages
page = st.session_state.page

if page == "Home":
    st.markdown('<p class="main-title">🔋 AI-Powered Demand Forecasting</p>', unsafe_allow_html=True)
    st.markdown('<p class="subtitle">Empowering grid management through AI-driven forecasting.</p>', unsafe_allow_html=True)

    st.markdown('''
    <div class="card">
        <ul>
            <li>📅 <strong>Upload historical substation/grid operational data.</strong></li>
            <li>🛠️ <strong>Adjust forecasts based on maintenance and grid events.</strong></li>
            <li>🌦️ <strong>Integrate detailed regional weather forecasts for precise adjustments.</strong></li>
            <li>📅 <strong>Account for economic & community events that influence demand.</strong></li>
        </ul>
    </div>
    ''', unsafe_allow_html=True)

    st.write("")
    if st.button("🚀 Go to Forecasting"):
        st.session_state.page = "Forecasting"

elif page == "Forecasting":
    st.markdown('<p class="main-title">📈 Upload & Forecasting Modules</p>', unsafe_allow_html=True)

    forecast_type = st.selectbox(
        "Select the Forecasting Option:",
        [
            "-- Select Option --",
            "1️⃣ Historical Substation/Grid Data",
            "2️⃣ Maintenance & Grid Events",
            "3️⃣ Regional Weather Forecast",
            "4️⃣ Economic/Community Events"
        ]
    )

    if forecast_type == "1️⃣ Historical Substation/Grid Data":
        st.subheader("📘 Upload Historical Substation/Grid Data")
        uploaded_file = st.file_uploader("Upload CSV or Excel:", type=["csv", "xlsx"], key="grid_data")

        if uploaded_file:
            try:
                df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('csv') else pd.read_excel(uploaded_file)
                st.dataframe(df.head())  # Show preview

                if st.button("Generate Forecast with AI"):
                    records = df.to_dict(orient="records")
                    payload = {"historical_grid_data": records}

                    res = requests.post("http://127.0.0.1:5000/forecast/grid", json=payload)
                    if res.status_code == 200:
                        result = res.json()
                        st.success("Forecast Generated with LLM")
                        st.info(result.get("summary"))

                        forecast_df = pd.DataFrame(result["forecast"])

                        st.markdown("### 📊 Forecast Visualization")
                        chart = (
                            alt.Chart(forecast_df)
                            .mark_bar()
                            .encode(
                                x=alt.X("date:N", title="Date", axis=alt.Axis(labelAngle=-45)),
                                y=alt.Y("expected_demand:Q", title="Electricity Demand (MW)"),
                                color=alt.Color("substation_id:N", title="Substation"),
                                tooltip=["date", "substation_id", "expected_demand"]
                            )
                            .properties(
                                width=600,
                                height=400
                            )
                        )
                        st.altair_chart(chart, use_container_width=True)
                    else:
                        st.error("Forecast generation failed.")
            except Exception as e:
                st.error(f"Error processing file: {e}")
            
            
    elif forecast_type == "2️⃣ Maintenance & Grid Events":
        st.subheader("🛠️ Upload Maintenance & Grid Events")
        event_file = st.file_uploader("Upload Grid Event Schedule (CSV/Excel):", type=["csv", "xlsx"], key="events")
        if event_file:
            try:
                df = pd.read_csv(event_file) if event_file.name.endswith('csv') else pd.read_excel(event_file)
                st.dataframe(df.head())
                required = {"event_id", "substation_id", "event_type", "start_datetime", "end_datetime"}
                if required.issubset(df.columns):
                    if st.button("Generate Event-Adjusted Forecast"):
                        payload = {"grid_event_schedule": df.to_dict(orient="records")}
                        res = requests.post("http://127.0.0.1:5000/forecast/events", json=payload)
                        if res.status_code == 200:
                            result = res.json()
                            st.success("Event-adjusted forecast ready")
                            st.info(result.get("summary"))
                            forecast_data = result.get("adjusted_forecast", [])
                            if forecast_data:
                                chart_df = pd.DataFrame(forecast_data)

                                chart = (
                                    alt.Chart(chart_df)
                                    .mark_bar()
                                    .encode(
                                        x=alt.X('date:N', title='Date'),
                                        y=alt.Y('demand:Q', title='Electricity Demand (MW)'),
                                        color=alt.Color('type:N', title='Forecast Type'),
                                        xOffset='substation_id:N',
                                        tooltip=['date', 'substation_id', 'type', 'demand']
                                    )
                                    .properties(
                                        width=600,
                                        height=400,
                                        title="Maintenance Impact Forecast (Grouped by Substation & Type)"
                                    )
                                )
                                st.altair_chart(chart, use_container_width=True)
                        else:
                            st.error(f"Event forecast failed: {res.status_code}")
                else:
                    st.error("Missing required event columns")
            except Exception as e:
                st.error(f"Error: {e}")

    elif forecast_type == "3️⃣ Regional Weather Forecast":
        st.subheader("🌍 Get Weather Forecast for Your Region")
        location_name = st.text_input("Enter your location (e.g., Phoenix, AZ):")
        if location_name.strip():
            if st.button("Fetch & Forecast"):
                lat, lon = geocode_location(location_name)
                if not lat:
                    st.error("Could not find location.")
                else:
                    st.success(f"Location found: {lat}, {lon}")
                    weather_data = fetch_open_meteo_weather(lat, lon)

                    if not weather_data:
                        st.error("No weather data returned.")
                    else:
                        st.info("Weather data fetched! Sending to LLM for forecast...")
                        payload = {"regional_weather_data": weather_data}
                        res = requests.post("http://127.0.0.1:5000/forecast/weather", json=payload)
                        if res.status_code == 200:
                            result = res.json()
                            st.success("Forecast complete.")
                            st.info(result.get("summary"))

                            chart_df = pd.DataFrame(result["weather_adjusted_forecast"])
                           # st.write("📋 Available columns:", chart_df.columns.tolist())

                            
                            # Check available columns first
                            #st.write("📋 Columns from LLM Forecast:", chart_df.columns.tolist())

                            # Try detecting a datetime column
                            possible_time_cols = ["datetime", "timestamp", "time", "date", "hour"]
                            datetime_col = next((col for col in chart_df.columns if str(col).lower() in possible_time_cols), None)
                            
                            if not datetime_col:
                                st.error("No datetime column found in the forecast data.")
                                st.stop()

                            
                            chart_df[datetime_col] = pd.to_datetime(chart_df[datetime_col])

                            # Electricity chart
                            st.markdown("### ⚡ Electricity Demand Forecast")
                            ele_bar = (
                                alt.Chart(chart_df)
                                .mark_bar(color="steelblue")
                                .encode(
                                    x=alt.X(f"{datetime_col}:T", title="Datetime"),
                                    y=alt.Y("electricity_demand:Q", title="Electricity Demand (kWh)"),
                                    tooltip=[datetime_col, "electricity_demand:Q"]
                                )
                                .properties(height=300)
                            )
                            st.altair_chart(ele_bar, use_container_width=True)

                            # Gas chart
                            st.markdown("### 🔥 Gas Demand Forecast")
                            gas_bar = (
                                alt.Chart(chart_df)
                                .mark_bar(color="orange")
                                .encode(
                                    x=alt.X(f"{datetime_col}:T", title="Datetime"),
                                    y=alt.Y("gas_demand:Q", title="Gas Demand (Therms)"),
                                    tooltip=[datetime_col, "gas_demand:Q"]
                                )
                                .properties(height=300)
                            )
                            st.altair_chart(gas_bar, use_container_width=True)
                        else:
                            st.error("Forecast request failed.")

    if forecast_type == "4️⃣ Economic/Community Events":
        st.subheader("📅 Upload Economic/Community Event Forecasts")
        community_file = st.file_uploader("Upload Community Events (CSV/Excel):", type=["csv", "xlsx"], key="community")

        if community_file:
            try:
                df = pd.read_csv(community_file) if community_file.name.endswith('csv') else pd.read_excel(community_file)
                st.dataframe(df.head())

                if st.button("Generate Community-Aware Forecast"):
                    records = df.to_dict(orient="records")
                    payload = {"community_events": records}

                    res = requests.post("http://127.0.0.1:5000/forecast/community", json=payload)
                    if res.status_code == 200:
                        result = res.json()
                        st.success("Community-aware forecast ready")
                        if "summary" in result:
                            st.info(result["summary"])
                        else:
                            st.warning("⚠️ No summary returned from the forecast.")

                        if "forecast" in result:
                            forecast_df = pd.DataFrame(result["forecast"])
                            st.markdown("### ⚡ Electricity Demand Impact (%)")
                            ele_chart = alt.Chart(forecast_df).mark_bar().encode(
                                x=alt.X("date:N", title="Date"),
                                y=alt.Y("electricity_change_pct:Q", title="Electricity Demand Change (%)"),
                                color=alt.Color("location:N", title="Location"),
                                tooltip=["date", "location", "electricity_change_pct"]
                            ).properties(height=300)
                            st.altair_chart(ele_chart, use_container_width=True)

                            st.markdown("### 🔥 Gas Demand Impact (%)")
                            gas_chart = alt.Chart(forecast_df).mark_bar().encode(
                                x=alt.X("date:N", title="Date"),
                                y=alt.Y("gas_change_pct:Q", title="Gas Demand Change (%)"),
                                color=alt.Color("location:N", title="Location"),
                                tooltip=["date", "location", "gas_change_pct"]
                            ).properties(height=300)
                            st.altair_chart(gas_chart, use_container_width=True)

                            with st.expander("View Full Forecast Data"):
                                st.dataframe(forecast_df)
                        else:
                            st.warning("⚠️ Forecast data not found in the LLM response. Only summary was returned.")
                            
                    else:
                        st.error(f"Community forecast failed: {res.status_code}")
            except Exception as e:
                st.error(f"Error: {e}")

elif page == "API Info":
    st.markdown('<p class="main-title">🔗 API Reference</p>', unsafe_allow_html=True)
    st.markdown('''
    **Endpoints for AI Demand Forecasting:**

    - `/forecast/grid` - Forecasts based on uploaded substation/grid historical data.
    - `/forecast/events` - Forecasts adjusted based on maintenance and grid events.
    - `/forecast/weather` - Forecasts adjusted based on regional weather data.
    - `/forecast/community` - Forecasts adjusted based on economic/community events.

    **Powered by:**
    - 🌐 [Groq API](https://groq.com)
    - ☀️ [Open-Meteo](https://open-meteo.com)
    - 🗺️ [OpenStreetMap Nominatim](https://nominatim.org)

    *No authentication required—entirely free APIs.*
    ''')
