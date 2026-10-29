
import os
import streamlit as st
import requests
import pandas as pd
import datetime

# Page Configuration
st.set_page_config(page_title="Auto-Trade Scanner", layout="wide")

st.title("📈 Auto-Trade Scanner Dashboard")
st.caption("Live Market Scanner powered by Upstox API")

# Sidebar for Configuration
st.sidebar.header("Configuration")

# Fetch token from Environment Variables (set in Render) or manual input
env_token = os.getenv("ACCESS_TOKEN", "")
access_token = st.sidebar.text_input(
    "Access Token",
    value=env_token,
    type="password",
    help="Your Upstox Access Token"
)

# Instrument & Watchlist Selection
selected_indices = st.sidebar.multiselect(
    "Select Watchlist / Indices",
    options=["NSE_INDEX|Nifty 50", "NSE_INDEX|Nifty Bank", "NSE_EQ|INE002A01018 (RELIANCE)", "NSE_EQ|INE040A01034 (HDFCBANK)"],
    default=["NSE_INDEX|Nifty 50", "NSE_INDEX|Nifty Bank"]
)

refresh_btn = st.sidebar.button("🔄 Refresh Data")

# Helper function to fetch live quotes from Upstox
def get_market_quote(symbols, token):
    if not token:
        st.error("Access Token is missing! Please set ACCESS_TOKEN in Render or enter it in the sidebar.")
        return None
    
    url = "https://api.upstox.com/v2/market-quote/quotes"
    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {token}"
    }
    params = {
        "instrument_key": ",".join(symbols)
    }
    
    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 401:
            st.error("Token Expired or Invalid. Please generate a new access token.")
            return None
        else:
            st.error(f"Error {response.status_code}: {response.text}")
            return None
    except Exception as e:
        st.error(f"Request failed: {e}")
        return None

# Main Dashboard View
if access_token:
    if selected_indices:
        data = get_market_quote(selected_indices, access_token)
        
        if data and "data" in data:
            records = []
            for key, val in data["data"].items():
                ltp = val.get("last_price", 0.0)
                net_change = val.get("net_change", 0.0)
                ohlc = val.get("ohlc", {})
                open_price = ohlc.get("open", 0.0)
                high_price = ohlc.get("high", 0.0)
                low_price = ohlc.get("low", 0.0)
                close_price = ohlc.get("close", 0.0)
                
                # Scanner Signal Logic Example: Open = Low (Bullish) / Open = High (Bearish)
                signal = "NEUTRAL"
                if open_price > 0:
                    if open_price == low_price:
                        signal = "BUY (Open=Low)"
                    elif open_price == high_price:
                        signal = "SELL (Open=High)"
                
                records.append({
                    "Symbol": val.get("symbol", key),
                    "LTP": ltp,
                    "Change": net_change,
                    "Open": open_price,
                    "High": high_price,
                    "Low": low_price,
                    "Prev Close": close_price,
                    "Signal": signal
                })
            
            df = pd.DataFrame(records)
            
            # Display Metric Cards
            col1, col2, col3 = st.columns(3)
            col1.metric("Total Instruments", len(df))
            col2.metric("Bullish Signals", len(df[df["Signal"].str.contains("BUY")]))
            col3.metric("Last Updated", datetime.datetime.now().strftime("%H:%M:%S"))
            
            st.subheader("Live Scanner Table")
            st.dataframe(df, use_container_width=True)
        else:
            st.info("No data returned. Click 'Refresh Data' or verify instrument keys.")
    else:
        st.warning("Please select at least one instrument from the sidebar.")
else:
    st.info("👈 Enter your Upstox Access Token in the sidebar to start scanning.")
