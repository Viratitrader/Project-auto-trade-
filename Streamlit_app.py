import streamlit as st
import requests
import gzip
import json
import re
import pandas as pd
from datetime import datetime, date, time
from zoneinfo import ZoneInfo
from concurrent.futures import ThreadPoolExecutor, as_completed
import time as time_lib

# =========================================================
# PAGE CONFIGURATION & MOBILE FRIENDLY CSS
# =========================================================
st.set_page_config(
    page_title="Project A Pro - Options Ratio Spread Scanner",
    page_icon="📊",
    layout="wide"
)

st.markdown("""
<style>
.block-container {
    padding-top: 0.4rem;
    padding-left: 0.5rem;
    padding-right: 0.5rem;
    max-width: 650px;
}
.header-box {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 6px;
}
.header-title {
    font-size: 1.25rem;
    font-weight: 800;
    color: #111;
    margin: 0;
}
.header-sub {
    font-size: 0.75rem;
    color: #555;
    margin: 0;
}
.live-pill {
    background: #e6f4ea;
    color: #137333;
    padding: 2px 7px;
    border-radius: 10px;
    font-size: 0.72rem;
    font-weight: bold;
}
.time-box {
    font-size: 0.75rem;
    background: #f1f3f4;
    padding: 3px 6px;
    border-radius: 5px;
    font-weight: 600;
}

/* CARDS EXACT MATCH TO SCREENSHOT */
.scanner-card-1 {
    background: #eafaf1;
    border: 1px solid #b7ebd0;
    border-radius: 8px;
    padding: 8px 10px;
    margin-bottom: 8px;
}
.scanner-card-2 {
    background: #fdebee;
    border: 1px solid #f9c5cb;
    border-radius: 8px;
    padding: 8px 10px;
    margin-bottom: 8px;
}
.scanner-card-3 {
    background: #fef8e7;
    border: 1px solid #fde7b2;
    border-radius: 8px;
    padding: 8px 10px;
    margin-bottom: 8px;
}
.card-header {
    font-size: 0.9rem;
    font-weight: 800;
    margin-bottom: 6px;
    color: #111;
}

/* COMPACT INPUT LABELS */
div[data-testid="stTextInput"] label, div[data-testid="stSelectbox"] label {
    font-size: 0.78rem !important;
    font-weight: 700 !important;
    margin-bottom: 1px !important;
}
.stButton button {
    height: 38px;
    font-size: 14px;
    font-weight: bold;
    border-radius: 6px;
}
</style>
""", unsafe_allow_html=True)

# =========================================================
# CONSTANTS & TIME HANDLING
# =========================================================
OPTION_CHAIN_URL = "https://api.upstox.com/v2/option/chain"
INSTRUMENT_URLS = [
    "https://assets.upstox.com/market-quote/instruments/exchange/complete.json.gz",
    "https://assets.upstox.com/market-quote/instruments/exchange/NSE.json.gz"
]

ist = ZoneInfo("Asia/Kolkata")
current_now = datetime.now(ist)
TODAY = current_now.date()
current_timestamp_str = current_now.strftime("%d %b %Y %H:%M:%S")

# =========================================================
# UPSTOX ACCESS TOKEN
# =========================================================
secret_token = st.secrets.get("UPSTOX_ACCESS_TOKEN", "")
if secret_token:
    access_token = str(secret_token).strip()
else:
    if "upstox_access_token" not in st.session_state:
        st.session_state.upstox_access_token = ""
    token_input = st.text_input("Upstox Access Token", type="password", key="upstox_token_input")
    if token_input.strip():
        st.session_state.upstox_access_token = token_input.strip()
    access_token = st.session_state.get("upstox_access_token", "")

# =========================================================
# F&O BAN LIST & RESULT CALENDAR (ROBUST ENGINE)
# =========================================================
@st.cache_data(ttl=1800)
def get_ban_and_result_calendar():
    # Placeholder for live F&O ban checks & events
    # Easily expandable via API or local cache
    ban_symbols = set()
    result_dates = {}
    return ban_symbols, result_dates

BAN_SYMBOLS, RESULT_DATES = get_ban_and_result_calendar()

# =========================================================
# INSTRUMENTS & UNIVERSE LOADER
# =========================================================
@st.cache_data(ttl=3600)
def load_instruments():
    for url in INSTRUMENT_URLS:
        try:
            res = requests.get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
            res.raise_for_status()
            raw = gzip.decompress(res.content)
            data = json.loads(raw.decode("utf-8"))
            if isinstance(data, dict):
                data = data.get("data", list(data.values()))
            df = pd.DataFrame(data)
            if not df.empty:
                return df
        except Exception:
            continue
    return pd.DataFrame()

@st.cache_data(ttl=3600)
def build_universe():
    df = load_instruments()
    if df.empty:
        return pd.DataFrame()
    df = df[
        (df["segment"].astype(str) == "NSE_FO") &
        (df["underlying_type"].astype(str) == "EQUITY") &
        (df["underlying_key"].astype(str).str.startswith("NSE_EQ|"))
    ].copy()

    numeric_expiry = pd.to_numeric(df["expiry"], errors="coerce")
    text_expiry = pd.to_datetime(df["expiry"], errors="coerce")
    timestamp_expiry = pd.to_datetime(numeric_expiry, unit="ms", errors="coerce")
    df["expiry_dt"] = text_expiry
    mask = numeric_expiry.notna()
    df.loc[mask, "expiry_dt"] = timestamp_expiry[mask]
    df["expiry"] = df["expiry_dt"].dt.date
    df["lot_size"] = pd.to_numeric(df["lot_size"], errors="coerce")

    df = df[df["expiry"].notna() & (df["expiry"] >= TODAY) & (df["lot_size"] > 0)].copy()
    symbol_col = "underlying_symbol" if "underlying_symbol" in df.columns else ("trading_symbol" if "trading_symbol" in df.columns else None)

    if symbol_col:
        universe = df[["underlying_key", symbol_col, "expiry", "lot_size"]].drop_duplicates().copy()
        universe["symbol"] = universe[symbol_col].astype(str).str.strip()
    else:
        universe = df[["underlying_key", "expiry", "lot_size"]].drop_duplicates().copy()
        universe["symbol"] = universe["underlying_key"].astype(str).str.replace("NSE_EQ|", "", regex=False)
    return universe

universe = build_universe()

# =========================================================
# API OPTION CHAIN CALL
# =========================================================
def get_option_chain(underlying_key, expiry_date, token):
    headers = {"Accept": "application/json", "Authorization": f"Bearer {token}"}
    params = {"instrument_key": underlying_key, "expiry_date": expiry_date.isoformat()}
    try:
        res = requests.get(OPTION_CHAIN_URL, params=params, headers=headers, timeout=12)
        if res.status_code == 200:
            data = res.json().get("data", [])
            return data if isinstance(data, list) else []
    except Exception:
        pass
    return []

def extract_options(chain, side="CE"):
    opts = []
    key = "call_options" if side == "CE" else "put_options"
    for row in chain:
        try:
            strike = float(row.get("strike_price", 0) or 0)
            data = row.get(key, {}) or {}
            m = data.get("market_data", {}) or {}
            g = data.get("option_greeks", {}) or {}
            ltp = float(m.get("ltp", 0) or 0)
            delta = float(g.get("delta", 0) or 0)
            vol = float(m.get("volume", 0) or 0)
            spot = float(row.get("underlying_spot_price", 0) or 0)
            if strike > 0 and ltp > 0:
                opts.append({
                    "strike": strike, "ltp": ltp, "delta": delta,
                    "volume": vol, "spot": spot
                })
        except Exception:
            continue
    opts.sort(key=lambda x: x["strike"])
    return opts

# =========================================================
# HEADER DISPLAY
# =========================================================
h1, h2 = st.columns([5.6, 4.4])
with h1:
    st.markdown('<p class="header-title">📊 Project A Pro</p>', unsafe_allow_html=True)
    st.markdown('<p class="header-sub">Options Ratio Spread Scanner</p>', unsafe_allow_html=True)
with h2:
    st.markdown(
        f'<div style="text-align:right;">'
        f'<span class="live-pill">● Live Scan</span> '
        f'<span class="time-box">{current_timestamp_str}</span>'
        f'</div>', 
        unsafe_allow_html=True
    )

st.write("")

# =========================================================
# 5 TOP INPUT CONTROLS
# =========================================================
p1, p2, p3, p4, p5 = st.columns(5)
with p1:
    top_delta = st.text_input("Delta", value="20-25", key="top_delta_inp")
with p2:
    top_ratio = st.selectbox("Ratio", ["1:3", "3:10", "1:4", "2:7"], key="top_ratio_inp")
with p3:
    top_side = st.selectbox("Option Type", ["CE", "PE"], key="top_side_inp")
with p4:
    avail_expiries = sorted(universe["expiry"].dropna().unique()) if not universe.empty else [TODAY]
    top_expiry = st.selectbox("Expiry", avail_expiries, format_func=lambda x: x.strftime("%d-%b-%Y"), key="top_exp_inp")
with p5:
    top_min_figures = st.text_input("Result", value="0", help="Figures / Minimum Profit", key="top_result_inp")

st.caption("**Spread Cost (₹)**")
c1, c2 = st.columns(2)
with c1:
    top_debit = st.text_input("Debit", value="0", placeholder="e.g. 500", key="top_debit_inp")
with c2:
    top_credit = st.text_input("Credit", value="0", placeholder="e.g. 500", key="top_credit_inp")

# =========================================================
# SESSION STATE INITIALIZATION
# =========================================================
if "auto_scan_active" not in st.session_state:
    st.session_state.auto_scan_active = False
if "active_scan_mode" not in st.session_state:
    st.session_state.active_scan_mode = "NONE"
if "scan_results_df" not in st.session_state:
    st.session_state.scan_results_df = pd.DataFrame()

# =========================================================
# 1. DEBIT ₹0 SCANNER CARD (GREEN)
# =========================================================
st.markdown('<div class="scanner-card-1"><div class="card-header">1. Debit ₹0 Scanner</div>', unsafe_allow_html=True)
b1, b2, b3 = st.columns([1, 1, 1.2])
with b1:
    is_auto_1 = st.session_state.auto_scan_active and st.session_state.active_scan_mode == "DEBIT0"
    auto_lbl_1 = "⏹ Stop" if is_auto_1 else "Auto"
    if st.button(auto_lbl_1, key="btn_auto_1", type="primary" if is_auto_1 else "secondary"):
        st.session_state.auto_scan_active = not is_auto_1
        st.session_state.active_scan_mode = "DEBIT0" if st.session_state.auto_scan_active else "NONE"
        st.rerun()
with b2:
    btn_man_1 = st.button("Manual", key="btn_man_1")
with b3:
    btn_scan_1 = st.button("Scan", key="btn_scan_1", type="primary")
st.markdown('</div>', unsafe_allow_html=True)

# =========================================================
# 2. % GAP SCANNER CARD (PINK)
# =========================================================
st.markdown('<div class="scanner-card-2"><div class="card-header">2. % Gap Scanner</div>', unsafe_allow_html=True)
g1, g2, g3, g4 = st.columns([1.2, 1, 1, 1.2])
with g1:
    gap_pct_val = st.text_input("%", value="5", label_visibility="collapsed", key="gap_pct_input")
with g2:
    is_auto_2 = st.session_state.auto_scan_active and st.session_state.active_scan_mode == "GAP"
    auto_lbl_2 = "⏹ Stop" if is_auto_2 else "Auto"
    if st.button(auto_lbl_2, key="btn_auto_2", type="primary" if is_auto_2 else "secondary"):
        st.session_state.auto_scan_active = not is_auto_2
        st.session_state.active_scan_mode = "GAP" if st.session_state.auto_scan_active else "NONE"
        st.rerun()
with g3:
    btn_man_2 = st.button("Manual", key="btn_man_2")
with g4:
    btn_scan_2 = st.button("Scan", key="btn_scan_2", type="primary")
st.markdown('</div>', unsafe_allow_html=True)

# =========================================================
# 3. OPTION PREMIUM SPIKE CARD (YELLOW)
# =========================================================
st.markdown('<div class="scanner-card-3"><div class="card-header">3. Option Premium Spike (UP / DOWN)</div>', unsafe_allow_html=True)
s1, s2, s3, s4 = st.columns([1.2, 1, 1, 1.2])
with s1:
    spike_pct_val = st.text_input("%", value="5", label_visibility="collapsed", key="spike_pct_input")
with s2:
    is_auto_3 = st.session_state.auto_scan_active and st.session_state.active_scan_mode == "SPIKE"
    auto_lbl_3 = "⏹ Stop" if is_auto_3 else "Auto"
    if st.button(auto_lbl_3, key="btn_auto_3", type="primary" if is_auto_3 else "secondary"):
        st.session_state.auto_scan_active = not is_auto_3
        st.session_state.active_scan_mode = "SPIKE" if st.session_state.auto_scan_active else "NONE"
        st.rerun()
with s3:
    btn_man_3 = st.button("Manual", key="btn_man_3")
with s4:
    btn_scan_3 = st.button("Scan", key="btn_scan_3", type="primary")
st.markdown('</div>', unsafe_allow_html=True)

# =========================================================
# PARSERS & RATIO SETUP
# =========================================================
RATIO_MAP = {"1:3": (1, 3), "3:10": (3, 10), "1:4": (1, 4), "2:7": (2, 7)}
buy_qty, sell_qty = RATIO_MAP[top_ratio]

def parse_delta_filter(text):
    text = str(text).strip()
    if "-" in text:
        parts = text.split("-")
        return float(parts[0]), float(parts[1])
    val = float(text)
    return (0.0, val)

delta_min, delta_max = 0.0, 100.0
try:
    delta_min, delta_max = parse_delta_filter(top_delta)
except Exception:
    pass

# =========================================================
# SCANNER LOGIC WORKER
# =========================================================
def scan_single_stock(item):
    symbol = str(item["symbol"])
    underlying_key = item["underlying_key"]
    lot_size = int(item["lot_size"])
    if lot_size <= 0:
        return []

    chain = get_option_chain(underlying_key, top_expiry, access_token)
    if not chain:
        return []

    options = extract_options(chain, top_side)
    if len(options) < 4:
        return []

    results = []
    for b in options:
        b_strike = b["strike"]
        b_ltp = b["ltp"]
        b_delta = abs(b["delta"]) * 100

        if not (delta_min <= b_delta <= delta_max):
            continue

        # Target sells
        sells = [x for x in options if x["strike"] > b_strike] if top_side == "CE" else [x for x in options if x["strike"] < b_strike]
        for c in sells:
            gap = abs(c["strike"] - b_strike)
            net_points = (sell_qty * c["ltp"]) - (buy_qty * b_ltp)
            total_amount = net_points * lot_size

            # Debit ₹0 condition: Net profit >= 0
            if total_amount < 0:
                continue

            # Supporting Spread R1 (Base)
            a_strike = b_strike - gap if top_side == "CE" else b_strike + gap
            a_opt = next((x for x in options if abs(x["strike"] - a_strike) < 0.01), None)
            
            r1_buy_strike = a_strike if a_opt else 0
            r1_sell_strike = b_strike
            r1_profit = ((sell_qty * b_ltp) - (buy_qty * (a_opt["ltp"] if a_opt else 0))) * lot_size

            # Supporting Spread R2 (Previous)
            p_strike = a_strike - gap if top_side == "CE" else a_strike + gap
            p_opt = next((x for x in options if abs(x["strike"] - p_strike) < 0.01), None)
            r2_buy_strike = p_strike if p_opt else 0
            r2_profit = ((sell_qty * (a_opt["ltp"] if a_opt else 0)) - (buy_qty * (p_opt["ltp"] if p_opt else 0))) * lot_size

            results.append({
                "symbol": symbol,
                "delta": b_delta,
                "buy_strike": b_strike,
                "sell_strike": c["strike"],
                "buy_ltp": b_ltp,
                "sell_ltp": c["ltp"],
                "profit": total_amount,
                "r1_buy": r1_buy_strike,
                "r1_sell": r1_sell_strike,
                "r1_buy_ltp": a_opt["ltp"] if a_opt else 0.0,
                "r1_sell_ltp": b_ltp,
                "r1_profit": r1_profit,
                "r2_buy": r2_buy_strike,
                "r2_sell": a_strike,
                "r2_buy_ltp": p_opt["ltp"] if p_opt else 0.0,
                "r2_sell_ltp": a_opt["ltp"] if a_opt else 0.0,
                "r2_profit": r2_profit,
            })
            break
    return results

# =========================================================
# TRIGGER SCANNING RUN
# =========================================================
should_run = (
    btn_scan_1 or btn_man_1 or 
    btn_scan_2 or btn_man_2 or 
    btn_scan_3 or btn_man_3 or 
    st.session_state.auto_scan_active
)

if should_run:
    if not access_token:
        st.error("કૃપા કરીને Upstox Access Token દાખલ કરો.")
    else:
        scan_univ = universe[universe["expiry"] == top_expiry].drop_duplicates(subset=["underlying_key"]).reset_index(drop=True)
        raw_list = []
        with st.spinner("સ્કેનિંગ ચાલુ છે..."):
            with ThreadPoolExecutor(max_workers=5) as executor:
                futures = {executor.submit(scan_single_stock, row): row["symbol"] for _, row in scan_univ.iterrows()}
                for f in as_completed(futures):
                    try:
                        res = f.result()
                        if res:
                            raw_list.extend(res)
                    except Exception:
                        pass

        # Sort: Highest Profit/Credit first
        raw_list.sort(key=lambda x: x["profit"], reverse=True)

        # Build clean Excel table
        final_rows = []
        for i, r in enumerate(raw_list, 1):
            ban_tag = " [BAN]" if r["symbol"] in BAN_SYMBOLS else ""
            res_date = RESULT_DATES.get(r["symbol"], "-")

            final_rows.append({
                "#": i,
                "Company - delta value": f"{r['symbol']}{ban_tag} ({r['delta']:.1f})",
                "strike buy/sale": f"{r['buy_strike']:g} / {r['sell_strike']:g}",
                "price/price": f"{r['buy_ltp']:.2f} / {r['sell_ltp']:.2f}",
                "R1 buystrike/sale": f"{r['r1_buy']:g} / {r['r1_sell']:g}" if r['r1_buy'] > 0 else "-",
                "R1 (price/price)": f"{r['r1_buy_ltp']:.2f} / {r['r1_sell_ltp']:.2f}" if r['r1_buy'] > 0 else "-",
                "R1 (profit)": f"₹{r['r1_profit']:,.0f}" if r['r1_buy'] > 0 else "-",
                "R2 buystrike/sale": f"{r['r2_buy']:g} / {r['r2_sell']:g}" if r['r2_buy'] > 0 else "-",
                "R2 (price/price)": f"{r['r2_buy_ltp']:.2f} / {r['r2_sell_ltp']:.2f}" if r['r2_buy'] > 0 else "-",
                "R2 (profit)": f"₹{r['r2_profit']:,.0f}" if r['r2_buy'] > 0 else "-",
                "Result date": res_date
            })
        st.session_state.scan_results_df = pd.DataFrame(final_rows)

# =========================================================
# SCAN RESULTS LIVE (EXCEL TABLE VIEW)
# =========================================================
st.markdown("---")
r_col1, r_col2 = st.columns([5.5, 4.5])
with r_col1:
    st.markdown("### 🎯 Scan Results (Live)")
with r_col2:
    search_txt = st.text_input("Search", placeholder="Search symbol...", label_visibility="collapsed", key="search_query_box")

disp_df = st.session_state.scan_results_df

if not disp_df.empty:
    if search_txt.strip():
        disp_df = disp_df[disp_df["Company - delta value"].str.contains(search_txt.strip(), case=False, na=False)]
    
    st.caption(f"**Total Results:** {len(disp_df)}")
    st.dataframe(disp_df, use_container_width=True, hide_index=True)
else:
    empty_cols = [
        "#", "Company - delta value", "strike buy/sale", "price/price",
        "R1 buystrike/sale", "R1 (price/price)", "R1 (profit)",
        "R2 buystrike/sale", "R2 (price/price)", "R2 (profit)", "Result date"
    ]
    st.caption("**Total Results:** 0")
    st.dataframe(pd.DataFrame(columns=empty_cols), use_container_width=True, hide_index=True)

# Auto Scan loop handling (Refreshes automatically)
if st.session_state.auto_scan_active:
    st.info(f"🔄 **Auto Scan ચાલુ છે ({st.session_state.active_scan_mode})** — દર 45 સેકન્ડે ડેટા લાઈવ રીફ્રેશ થશે.")
    time_lib.sleep(45)
    st.rerun()
