import streamlit as st
import pandas as pd
import requests
import fitz
import json
import matplotlib.pyplot as plt

def geocode_location(location):
    url = "https://nominatim.openstreetmap.org/search"
    params = {
        "q": location,
        "format": "json",
        "limit": 1
    }
    headers = {"User-Agent": "streamlit-app"}  # Nominatim requires this

    try:
        response = requests.get(url, params=params, headers=headers, timeout=5)

        if response.status_code != 200:
            st.error(f"Geocoding failed with status code {response.status_code}")
            return None, None

        data = response.json()

        if not data:
            st.warning("No results found for this location.")
            return None, None

        return float(data[0]["lat"]), float(data[0]["lon"])

    except requests.exceptions.RequestException as e:
        st.error(f"Network error: {e}")
        return None, None

    except ValueError:
        st.error("Geocoding API returned invalid JSON.")
        return None, None

def fetch_weather_forecast(lat, lon):
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": "temperature_2m,relative_humidity_2m,cloudcover",
        "forecast_days": 7,
        "timezone": "auto"
    }
    response = requests.get(url, params=params)
    data = response.json()
    return data["hourly"]



st.set_page_config(page_title="AI-Powered Demand Forecasting", layout="wide")

# Initialize session state for page navigation
if 'page' not in st.session_state:
    st.session_state.page = 'Home'

col1, col2, col3 = st.columns(3)

with col1:
    if st.button("Home"):
        st.session_state.page = "Home"
with col2:
    if st.button("Forecasting"):
        st.session_state.page = "Forecasting"
with col3:
    if st.button("API Info"):
        st.session_state.page = "API Info"

page = st.session_state.page

if page == "Home":
    st.title("🔋 AI-Powered Demand Forecasting")
    st.write("""
    Welcome to the **AI-Powered Demand Forecasting System**.

    This tool helps predict **electricity and gas demand** using **AI models** for **better grid management**.

    - 📌 Upload your historical electricity and gas bill data (first four months).
    - 📌 Get AI-powered predictions for future bills (up to the end of the year).
    - 📌 Predict based on seasonal and time-based trends.

    Navigate to **Forecasting** to get started! 🚀
    """)

elif page == "Forecasting":
    st.title("📊 Demand Forecasting")
    st.write("Upload your electricity and gas bill data.")
    
    #User has to enter the location
    location = st.text_input("Enter your location (e.g., San Diego, CA):", key="user_location")
    
    #providing user to select an option
    if location.strip():
        st.markdown("### Choose Forecasting Method:")
        method = st.radio(
        "Select a method:",
        [
            "🌦️ AI Forecast ( Based on Weather)",
            "📄 Upload My Usage Data for Forecasting"
        ]
        )
        if method == "🌦️ AI Forecast ( Based on Weather)":
            st.markdown("#### Forecast will be generated based on real-time weather data using Gen AI.")
            if st.button("🔍 Generate Forecast Based on Weather"):
                lat, lon = geocode_location(location)
                if lat is None:
                    st.error("Could not find location. Please try a more specific city.")
                else:
                    st.success(f"Location found: {lat}, {lon}")
                    hourly_weather = fetch_weather_forecast(lat, lon)

                    weather_input = []
                    for i in range(len(hourly_weather["time"])):
                        weather_input.append({
                        "hour": hourly_weather["time"][i],
                        "temp": hourly_weather["temperature_2m"][i],
                        "humidity": hourly_weather["relative_humidity_2m"][i],
                        "cloud": hourly_weather["cloudcover"][i]
                    })

                    # Format for LLM input — we’ll use this in Phase 3
                    data_for_llm = {
                    "location": location,
                    "season": "Spring",
                    "day_type": "Weekday",
                    "date": str(hourly_weather["time"][0][:10]),
                    "weather": weather_input[:24],  # First 24 hours only
                    "past_demand": []  # Optional for now
    }

                    try:
                        response = requests.post("http://127.0.0.1:5000/forecast/weather", json=data_for_llm)

                        if response.status_code == 200:
                            result = response.json()
                            forecast_data = result.get("forecast", [])
                            summary = result.get("summary", "No explanation provided.")

                            if forecast_data:

                                # Convert to DataFrame
                                forecast_df = pd.DataFrame(forecast_data)
                                forecast_df["hour"] = pd.to_datetime(forecast_df["hour"]).dt.strftime("%H:%M")
                                
                                with st.expander("📋 Show Forecast Table"):
                                        st.dataframe(forecast_df)
                                st.write("### 📊 24-Hour Forecast (Electricity & Gas)")


                                # Plotting
                                fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(6, 5), sharex=True)  
                                                              
                                x = range(len(forecast_df))
                            
                               #check this 
                                # Electricity Demand Chart
                                ax1.bar(x, forecast_df["electricity_demand"], color="#1f77b4")
                                ax1.set_title(" Forecasted Electricity Demand")
                                ax1.set_ylabel("kWh")
                                
                                ax1.grid(True, linestyle='--', alpha=0.3)
                                
                                #Gas Demand Chart
                                ax2.bar(x, forecast_df["gas_demand"], color="#ff7f0e")
                                ax2.set_title("Forecasted Gas Demand")
                                ax2.set_ylabel("Therms")
                                ax2.set_xticks(x)
                                ax2.set_xticklabels(forecast_df["hour"], rotation=30)
                                ax2.grid(True, linestyle='--', alpha=0.3)
                                plt.tight_layout()
                                st.pyplot(fig)  

                            else:
                                st.warning("No forecast data received from the LLM.")
                        else:
                            st.error(f"LLM Forecast failed. Status code: {response.status_code}")

                    except Exception as e:
                         st.error(f"Error contacting backend: {e}")
            
                
        elif method == "📄 Upload My Usage Data for Forecasting":
            uploaded_file = st.file_uploader("Upload your electricity and gas bill", type=["csv", "xlsx", "json", "pdf"])
            st.markdown("### Upload File")
            
            if uploaded_file:
                try:
                    file_extension = uploaded_file.name.split('.')[-1].lower()
                    df = None

                    if file_extension == 'csv':
                        df = pd.read_csv(uploaded_file)

                    elif file_extension in ['xlsx', 'xls']:
                        df = pd.read_excel(uploaded_file)

                    elif file_extension == 'json':
                        data = json.load(uploaded_file)
                        df = pd.DataFrame(data)

                    elif file_extension == 'pdf':
                        doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
                        text = "\n".join(page.get_text() for page in doc)
                        st.write("PDF Extracted Text Preview:", text[:1000] + "...")

                    if df is not None:
                        df.columns = df.columns.str.strip().str.lower()
                        required_columns = {"date", "hour_of_day", "temperature", "electricity_demand", "gas_demand"}
                        missing_columns = required_columns - set(df.columns)

                        if missing_columns:
                            st.error(f"Missing required columns: {missing_columns}")
                        else:
                            df["date"] = pd.to_datetime(df["date"], errors="coerce")
                            df.dropna(subset=["date"], inplace=True)
                            df = df[df["date"].dt.month.isin([1, 2, 3, 4])]

                            grouped = df.groupby(df["date"].dt.month)
                            historical_data = []
                            payload = {
                            "historical_data": historical_data,
                            "location": location
                            }

                            for month, group in grouped:
                                record = {
                                    "month": month,
                                    "temperature": group["temperature"].mean(),
                                    "electricity_demand": group["electricity_demand"].mean(),
                                    "gas_demand": group["gas_demand"].mean()
                                }
                                historical_data.append(record)

                            payload = {"historical_data": historical_data}

                            response = requests.post("http://127.0.0.1:5000/forecast", json=payload)

                            if response.status_code == 200:
                                result = response.json()
                                dominant_usage = result.get("dominant_usage")
                                usage_reason = result.get("usage_reason")
                                insight = result.get("insight")
                                narrative = result.get("narrative_summary")
                                forecast = result.get("forecast")
                                tips = result.get("tips")

                                if forecast and isinstance(forecast, dict):
                                    months = []
                                    electricity = []
                                    gas = []

                                    for month, values in forecast.items():
                                        months.append(month)
                                        electricity.append(values.get("electricity_demand", 0))
                                        gas.append(values.get("gas_demand", 0))

                                    forecast_df = pd.DataFrame({
                                        "Month": months,
                                        "Electricity Demand": electricity,
                                        "Gas Demand": gas
                                    })
                                    # Define the correct month order
                                    month_order = ["May", "June", "July", "August", "September", "October", "November", "December"]
                                    months = [month for month in month_order if month in forecast]
                                    electricity = [forecast[month]["electricity_demand"] for month in months]
                                    gas = [forecast[month]["gas_demand"] for month in months]
                                    
                                    # Set categorical month order
                                    forecast_df["Month"] = pd.Categorical(forecast_df["Month"], categories=month_order, ordered=True)
                                    forecast_df = forecast_df.sort_values("Month")

                                    # Adds formatted label like "May '25"
                                    forecast_df["MonthLabel"] = forecast_df["Month"].apply(lambda m: f"{m} '25")

                                    with st.expander("📋 Show Forecast Table"):
                                        st.dataframe(forecast_df)
                                    st.write("## 📊 Forecasted Electricity & Gas Demand")

                                    # Create a smaller figure
                                    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(6, 2), sharex=True)
                                    x = range(len(forecast_df))

                                    # Plot bars
                                    # Electricity chart
                                    ax1.bar(x, forecast_df["Electricity Demand"], color="#1f77b4")
                                    ax1.set_ylabel("kWh")
                                    ax1.set_title("📈 Electricity Demand")
                                    ax1.grid(True, linestyle='--', alpha=0.3)

                                    # Gas chart
                                    ax2.bar(x, forecast_df["Gas Demand"], color="#ff7f0e")
                                    ax2.set_ylabel("Therms")
                                    ax2.set_title("🔥 Gas Demand")
                                    ax2.set_xticks(x)
                                    ax2.set_xticklabels(forecast_df["MonthLabel"], rotation=30)
                                    ax2.grid(True, linestyle='--', alpha=0.3)

                                    plt.tight_layout()
                                    st.pyplot(fig)
        
                                    
                                st.write(f"⚡ Dominant Usage: {dominant_usage}")
                                st.write(f"💡 Reason: {usage_reason}")
                                st.write("📘 Summary:")
                                st.markdown(narrative)
                                st.write("### 💡 Saving Tips:")
                                for tip in tips:
                                    st.write(f"- {tip}")
                                st.write("### 🌟 Insights:")
                                st.info(insight)
                            else:
                                st.error(f"Error fetching forecast. Status Code: {response.status_code} - {response.text}")
                except Exception as e:
                    st.error(f"Error processing file: {e}")
                    
                    
            if uploaded_file is None:
                st.info("📂 No file uploaded.")
                st.markdown("Or... you can generate a forecast based on your location and season without uploading any data!")
                if st.button("🔮 Generate General Forecast (No Data Upload)"):
                    st.info("Sending request to AI...")
                    try:
                        # Build a simple data payload
                        payload = {
                        "location": location,
                        "season": "Spring",
                        "day_type": "Weekday"
                        }
                        response = requests.post("http://127.0.0.1:5000/forecast/nodata", json=payload)
                        if response.status_code == 200:
                            result = response.json()
                            forecast = result.get("forecast")
                            summary = result.get("summary")

                            # Display results
                            st.success("✅ Forecast received successfully!")
                            st.write("### Forecast Summary")
                            st.markdown(summary)
                            st.write("### Monthly Forecast")
                            if forecast:
                                # Convert forecast dict to DataFrame
                                months = list(forecast.keys())
                                electricity = [forecast[m]["electricity_demand"] for m in months]
                                gas = [forecast[m]["gas_demand"] for m in months]

                                df = pd.DataFrame({
                                "Month": months,
                                "Electricity Demand": electricity,
                                "Gas Demand": gas
                                })

                                # Ensure months are in correct order
                                month_order = ["May", "June", "July", "August", "September", "October", "November", "December"]
                                months = [month for month in month_order if month in forecast]
                                df = df.sort_values("Month")
                                
                                df["Month"] = pd.Categorical(df["Month"], categories=month_order, ordered=True)
                                df = df.sort_values("Month")
                                df["MonthLabel"] = df["Month"].apply(lambda m: f"{m} '25")                                

                                # Show table
                                st.write("### 📋 Monthly Forecast Table")
                                with st.expander("📋 Show Forecast Table"):
                                        st.dataframe(df)
                                st.write("## Forecasted Electricity & Gas Demand")

                                # Plot bar chart
                                st.write("### 📊 Monthly Electricity & Gas Demand")
                                fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(6, 5), sharex=True)  
                                                              
                                x = range(len(df))
                                bar_width = 0.35
                                
                                # Electricity Demand Chart
                                ax1.bar(x, df["Electricity Demand"], color="#1f77b4")
                                ax1.set_title(" Forecasted Electricity Demand")
                                ax1.set_ylabel("kWh")
                                ax1.grid(True, linestyle='--', alpha=0.3)
                                
                                
                                ax2.bar(x, df["Gas Demand"], color="#ff7f0e")
                                ax2.set_title(" Forecasted Gas Demand")
                                ax2.set_ylabel("Therms")
                                ax2.set_xticks(x)
                                ax2.set_xticklabels(df["MonthLabel"], rotation=30)
                                ax2.grid(True, linestyle='--', alpha=0.3)
                                
                                plt.tight_layout()
                                st.pyplot(fig)  

                        else:
                            st.error("Failed to get forecast from server.")
                    except Exception as e:
                        st.error(f"Error: {e}")

elif page == "API Info":
    st.title("🔗 API Information")
    st.markdown(
    '''
Welcome to the **API Reference** for the AI-Powered Demand Forecasting System.  
This app is built using **Python, Streamlit, and Gen AI (Groq API)** to offer real-time, intelligent energy forecasting.

---

### 📥 Available API Endpoints

---

#### 1. `/forecast`
- **Method:** `POST`  
- **Purpose:** Forecast energy usage based on uploaded file  
- **Input:**

\`\`\`json
{
  "location": "San Diego, CA",
  "historical_data": [
    {"month": 1, "temperature": 64, "electricity_demand": 420, "gas_demand": 210},
    {"month": 2, "temperature": 62, "electricity_demand": 405, "gas_demand": 230}
  ]
}
\`\`\`

- **Output:**  
  Forecast from May–December with:
  - Monthly electricity and gas usage
  - Peak month insights
  - AI-generated summary
  - Energy-saving tips

---

#### 2. `/forecast/weather`
- **Method:** `POST`  
- **Purpose:** 24-hour forecast based on live weather data  
- **Input:**

\`\`\`json
{
  "location": "San Diego",
  "date": "2025-03-27",
  "season": "Spring",
  "day_type": "Weekday",
  "weather": [
    {"hour": "00:00", "temp": 65, "humidity": 60, "cloud": 30},
    {"hour": "01:00", "temp": 64, "humidity": 62, "cloud": 35}
  ]
}
\`\`\`

- **Output:**  
  Hour-by-hour forecast for electricity and gas demand with a smart LLM-generated explanation.

---

#### 3. `/forecast/nodata`
- **Method:** `POST`  
- **Purpose:** Forecast usage **without uploading any data**  
- **Input:**

\`\`\`json
{
  "location": "San Diego",
  "season": "Spring",
  "day_type": "Weekday"
}
\`\`\`

- **Output:**  
  Monthly forecast from May to December based on seasonal and regional patterns.

---

### 🧠 Powered By

- **[Groq API](https://groq.com):** Fast, free access to LLaMA 3-70B for Gen AI forecasting  
- **[Open-Meteo](https://open-meteo.com):** Free weather forecast API  
- **[Nominatim (OpenStreetMap)](https://nominatim.org):** Converts user location to lat/lon  

---

📘 *This system runs entirely on free services and APIs. No logins, tokens, or keys are required on the frontend.*
'''
    )
