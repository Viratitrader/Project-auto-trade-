import os
import re
import gzip
import json
import requests
import pandas as pd
from datetime import date
from concurrent.futures import ThreadPoolExecutor, as_completed
import streamlit as st
import streamlit.components.v1 as components

# =========================================================
# PAGE CONFIG
# =========================================================
st.set_page_config(
    page_title="Project A Pro",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
    .block-container {
        padding: 0px !important;
        margin: 0px !important;
        max-width: 100% !important;
    }
    #MainMenu, header, footer { display: none !important; visibility: hidden; }
</style>
""", unsafe_allow_html=True)

# =========================================================
# CONSTANTS & UPSTOX AUTH
# =========================================================
OPTION_CHAIN_URL = "https://api.upstox.com/v2/option/chain"
INSTRUMENT_URLS = [
    "https://assets.upstox.com/market-quote/instruments/exchange/complete.json.gz",
    "https://assets.upstox.com/market-quote/instruments/exchange/NSE.json.gz"
]
TODAY = date.today()

access_token = str(st.secrets.get("UPSTOX_ACCESS_TOKEN", "")).strip()

# =========================================================
# SESSION STATE INITIALIZATION
# =========================================================
if "scan_results" not in st.session_state:
    st.session_state.scan_results = []
if "auto_scan_active" not in st.session_state:
    st.session_state.auto_scan_active = False

# =========================================================
# DATA LOADERS & PARSERS
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
        (df["instrument_type"].astype(str).isin(["CE", "PE"])) &
        (df["underlying_type"].astype(str) == "EQUITY") &
        (df["underlying_key"].astype(str).str.startswith("NSE_EQ|"))
    ].copy()

    df["expiry_dt"] = pd.to_datetime(df["expiry"], errors="coerce")
    df["expiry"] = df["expiry_dt"].dt.date
    df["lot_size"] = pd.to_numeric(df["lot_size"], errors="coerce")
    df = df[df["expiry"].notna() & (df["expiry"] >= TODAY) & (df["lot_size"] > 0)].copy()

    sym_col = next((c for c in ["underlying_symbol", "trading_symbol"] if c in df.columns), None)
    if sym_col:
        universe = df[["underlying_key", sym_col, "expiry", "lot_size"]].drop_duplicates().copy()
        universe["symbol"] = universe[sym_col].astype(str).str.strip()
    else:
        universe = df[["underlying_key", "expiry", "lot_size"]].drop_duplicates().copy()
        universe["symbol"] = universe["underlying_key"].astype(str).str.replace("NSE_EQ|", "", regex=False)

    return universe

universe = build_universe()
available_expiries = sorted(universe["expiry"].dropna().unique()) if not universe.empty else [TODAY]

def parse_delta_range(text):
    text = str(text).strip().replace(" ", "")
    if "-" in text:
        a, b = text.split("-")
        low, high = float(a), float(b)
        if high <= 1.0:
            low *= 100
            high *= 100
        return min(low, high), max(low, high)
    val = float(text)
    if val <= 1.0:
        val *= 100
    return 0.0, val

def parse_amount_range(text):
    text = str(text).strip().replace(",", "")
    if "-" in text:
        a, b = text.split("-")
        return float(a), float(b)
    val = float(text) if text else 5000.0
    return 0.0, val

def get_option_chain(underlying_key, exp_date, token):
    headers = {"Accept": "application/json", "Authorization": f"Bearer {token}"}
    params = {"instrument_key": underlying_key, "expiry_date": exp_date.isoformat()}
    try:
        r = requests.get(OPTION_CHAIN_URL, params=params, headers=headers, timeout=12)
        if r.status_code == 200:
            return r.json().get("data", [])
    except Exception:
        pass
    return []

def extract_side_options(chain, opt_type):
    key = "call_options" if opt_type == "CE" else "put_options"
    items = []
    spot_price = 0.0
    for row in chain:
        try:
            spot = float(row.get("underlying_spot_price", 0) or 0)
            if spot > 0 and spot_price == 0:
                spot_price = spot
            strike = float(row.get("strike_price", 0) or 0)
            opt = row.get(key, {}) or {}
            mdata = opt.get("market_data", {}) or {}
            greeks = opt.get("option_greeks", {}) or {}
            ltp = float(mdata.get("ltp", 0) or 0)
            delta = abs(float(greeks.get("delta", 0) or 0)) * 100
            if strike > 0 and ltp > 0:
                items.append({"strike": strike, "ltp": ltp, "delta": delta})
        except Exception:
            continue
    items.sort(key=lambda x: x["strike"])
    return items, spot_price

# =========================================================
# SCAN LOGIC (% GAP)
# =========================================================
def scan_stock_pg(item, exp_val, opt_type, delta_low, delta_high, gap_pct, b_qty, s_qty, deb_range, cred_range, min_pft):
    try:
        chain = get_option_chain(item["underlying_key"], exp_val, access_token)
        if not chain:
            return None

        options, spot_price = extract_side_options(chain, opt_type)
        if len(options) < 3 or spot_price <= 0:
            return None

        # 1. Base Strike by Delta
        delta_matches = [x for x in options if delta_low <= x["delta"] <= delta_high]
        if not delta_matches:
            return None
        mid_delta = (delta_low + delta_high) / 2
        delta_matches.sort(key=lambda x: abs(x["delta"] - mid_delta))
        base_opt = delta_matches[0]
        base_strike = base_opt["strike"]
        base_ltp = base_opt["ltp"]
        lot = int(item["lot_size"])

        # 2. Target Strike by % Gap
        gap_val = spot_price * (gap_pct / 100.0)
        target_exact = (base_strike + gap_val) if opt_type == "CE" else (base_strike - gap_val)

        if opt_type == "CE":
            targets = [x for x in options if x["strike"] >= target_exact and x["strike"] > base_strike]
            if not targets:
                return None
            targets.sort(key=lambda x: x["strike"])
            target_opt = targets[0]
        else:
            targets = [x for x in options if x["strike"] <= target_exact and x["strike"] < base_strike]
            if not targets:
                return None
            targets.sort(key=lambda x: -x["strike"])
            target_opt = targets[0]

        target_strike = target_opt["strike"]
        target_ltp = target_opt["ltp"]

        # 3. Main Net & Amount
        net_pt = (s_qty * target_ltp) - (b_qty * base_ltp)
        amount = round(abs(net_pt) * lot, 2)
        side = "CREDIT" if net_pt > 0 else ("DEBIT" if net_pt < 0 else "ZERO")

        if side == "CREDIT" and not (cred_range[0] <= amount <= cred_range[1]):
            return None
        if side == "DEBIT" and not (deb_range[0] <= amount <= deb_range[1]):
            return None
        if amount < min_pft:
            return None

        # 4. R1 Spread (Previous Spread)
        actual_gap = abs(target_strike - base_strike)
        r1_buy_strike = (base_strike - actual_gap) if opt_type == "CE" else (base_strike + actual_gap)
        r1_sell_strike = base_strike

        r1_b = next((x for x in options if abs(x["strike"] - r1_buy_strike) < 0.01), None)
        r1_s = next((x for x in options if abs(x["strike"] - r1_sell_strike) < 0.01), None)
        r1_txt = f"{r1_buy_strike:g} / {r1_sell_strike:g}" if (r1_b and r1_s) else "- / -"
        r1_pp = f"{r1_b['ltp']:.2f} / {r1_s['ltp']:.2f}" if (r1_b and r1_s) else "- / -"

        # 5. R2 Spread (Previous-to-previous sequence)
        r2_buy_strike = (r1_buy_strike - actual_gap) if opt_type == "CE" else (r1_buy_strike + actual_gap)
        r2_sell_strike = r1_buy_strike

        r2_b = next((x for x in options if abs(x["strike"] - r2_buy_strike) < 0.01), None)
        r2_s = next((x for x in options if abs(x["strike"] - r2_sell_strike) < 0.01), None)
        r2_txt = f"{r2_buy_strike:g} / {r2_sell_strike:g}" if (r2_b and r2_s) else "- / -"
        r2_pp = f"{r2_b['ltp']:.2f} / {r2_s['ltp']:.2f}" if (r2_b and r2_s) else "- / -"

        # Best Value Priority Sorting
        sort_score = amount if side == "CREDIT" else (-amount)

        return {
            "symbol": item["symbol"],
            "delta_display": f"Δ {base_opt['delta']:.2f}",
            "res_date": "",
            "strk_bs": f"{base_strike:g} / {target_strike:g}",
            "pp": f"{base_ltp:.2f} / {target_ltp:.2f}",
            "dc": f"{'C' if side == 'CREDIT' else 'D'} {amount:,.0f}",
            "r1_bs": r1_txt,
            "r1_pp": r1_pp,
            "r2_bs": r2_txt,
            "r2_pp": r2_pp,
            "sort_score": sort_score
        }
    except Exception:
        return None

# =========================================================
# CONTROL HEADER & STREAMLIT INPUTS
# =========================================================
col_head1, col_head2 = st.columns([2, 1])
with col_head1:
    st.markdown("### 📊 Project A Pro <span style='font-size:12px;color:gray;'>Options Ratio Spread Scanner</span>", unsafe_allow_html=True)
with col_head2:
    st.markdown(f"<div style='text-align:right;font-size:12px;'>🟢 <b>Live</b> &nbsp; {TODAY.strftime('%d %b %Y')}</div>", unsafe_allow_html=True)

# Filters Row 1
f1, f2, f3, f4, f5 = st.columns([1.1, 0.9, 0.9, 1.1, 0.9])
with f1:
    delta_in = st.text_input("Delta", "0.10 - 0.25")
with f2:
    ratio_in = st.selectbox("Ratio", ["1:3", "3:10", "1:4", "2:7"])
with f3:
    opt_in = st.selectbox("Option Type", ["CE", "PE"])
with f4:
    exp_in = st.selectbox("Expiry", available_expiries, format_func=lambda x: x.strftime("%d %b"))
with f5:
    res_profit_in = st.text_input("Result (₹)", "0")

# Filters Row 2 - Spread Cost
sc1, sc2 = st.columns(2)
with sc1:
    deb_in = st.text_input("Debit Spread Cost (₹)", "0 - 5000")
with sc2:
    cred_in = st.text_input("Credit Spread Cost (₹)", "0 - 5000")

# 3 Modules Cards
m_col1, m_col2, m_col3 = st.columns(3)
with m_col1:
    st.markdown("<div style='background:#f0fdf4;padding:6px;border-radius:6px;border:1px solid #bbf7d0;font-size:12px;font-weight:700;'>1. Debit ₹0</div>", unsafe_allow_html=True)
    st.caption("Module Pending")

with m_col2:
    st.markdown("<div style='background:#fff1f2;padding:6px;border-radius:6px;border:1px solid #fecdd3;font-size:12px;font-weight:700;'>2. % Gap (0-30%)</div>", unsafe_allow_html=True)
    gap_pct_val = st.number_input("Gap %", min_value=0.0, max_value=30.0, value=20.0, step=0.5, label_visibility="collapsed")
    
    # Auto ON/OFF Toggle and Manual Scan
    a_col, b_col = st.columns([1.2, 1])
    with a_col:
        auto_toggle = st.toggle("Auto", value=st.session_state.auto_scan_active)
        if auto_toggle != st.session_state.auto_scan_active:
            st.session_state.auto_scan_active = auto_toggle
    with b_col:
        man_scan_btn = st.button("Manual Scan", type="primary", use_container_width=True)

with m_col3:
    st.markdown("<div style='background:#fefce8;padding:6px;border-radius:6px;border:1px solid #fef08a;font-size:12px;font-weight:700;'>3. Spike UP/DN</div>", unsafe_allow_html=True)
    st.caption("Module Pending")

# =========================================================
# SCAN EXECUTION
# =========================================================
should_scan = man_scan_btn or st.session_state.auto_scan_active

if should_scan:
    ratio_map = {"1:3": (1, 3), "3:10": (3, 10), "1:4": (1, 4), "2:7": (2, 7)}
    b_qty, s_qty = ratio_map[ratio_in]
    d_low, d_high = parse_delta_range(delta_in)
    deb_range = parse_amount_range(deb_in)
    cred_range = parse_amount_range(cred_in)
    min_pft = float(res_profit_in) if res_profit_in else 0.0

    scan_universe = universe[universe["expiry"] == exp_in].drop_duplicates(subset=["underlying_key"]).reset_index(drop=True)
    raw_results = []

    with ThreadPoolExecutor(max_workers=6) as executor:
        futures = {
            executor.submit(
                scan_stock_pg, row, exp_in, opt_in, d_low, d_high,
                gap_pct_val, b_qty, s_qty, deb_range, cred_range, min_pft
            ): row["symbol"]
            for _, row in scan_universe.iterrows()
        }
        for future in as_completed(futures):
            res = future.result()
            if res:
                raw_results.append(res)

    # Sort: highest profit/credit first
    raw_results.sort(key=lambda x: x["sort_score"], reverse=True)
    st.session_state.scan_results = raw_results

# =========================================================
# 8-COLUMN MOBILE-OPTIMIZED RESULT TABLE
# =========================================================
results = st.session_state.scan_results

table_rows_html = ""
for i in range(max(10, len(results))):
    if i < len(results):
        r = results[i]
        date_badge = f"<span class='comp-date'>📅 {r['res_date']} ({r['delta_display']})</span>" if r['res_date'] else f"<span class='comp-date'>{r['delta_display']}</span>"
        table_rows_html += f"""
        <tr>
            <td class="c-comp"><div class="comp-name">{r['symbol']}</div>{date_badge}</td>
            <td class="c-col">{r['strk_bs']}</td>
            <td class="c-col">{r['pp']}</td>
            <td class="c-col highlight-dc">{r['dc']}</td>
            <td class="c-col">{r['r1_bs']}</td>
            <td class="c-col">{r['r1_pp']}</td>
            <td class="c-col">{r['r2_bs']}</td>
            <td class="c-col">{r['r2_pp']}</td>
        </tr>
        """
    else:
        table_rows_html += """
        <tr>
            <td class="c-comp"></td>
            <td class="c-col"></td>
            <td class="c-col"></td>
            <td class="c-col"></td>
            <td class="c-col"></td>
            <td class="c-col"></td>
            <td class="c-col"></td>
            <td class="c-col"></td>
        </tr>
        """

full_html = f"""
<!DOCTYPE html>
<html>
<head>
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
<style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }}
    .excel-container {{
        width: 100%;
        border: 1px solid #94a3b8;
        background: #ffffff;
        border-radius: 4px;
        overflow: hidden;
        margin-top: 6px;
    }}
    .excel-grid {{
        width: 100%;
        border-collapse: collapse;
        font-size: 0.62rem;
        table-layout: fixed;
    }}
    .excel-grid th, .excel-grid td {{
        border: 1px solid #cbd5e1;
        padding: 4px 1px;
        text-align: center;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
    }}
    .excel-grid th {{
        background-color: #e2e8f0;
        color: #0f172a;
        font-weight: 700;
        font-size: 0.60rem;
    }}
    .excel-grid td {{ height: 28px; }}
    
    /* 8 Columns - 100% Fit */
    .c-comp {{ width: 23%; text-align: left !important; padding-left: 3px !important; }}
    .c-col  {{ width: 11%; }}
    
    .comp-name {{ font-weight: 700; color: #0f172a; font-size: 0.64rem; }}
    .comp-date {{ font-size: 0.52rem; color: #0284c7; font-weight: 600; display: block; }}
    .highlight-dc {{ font-weight: 700; color: #047857; }}
</style>
</head>
<body>
    <div style="display:flex; justify-content:space-between; align-items:center; margin-top:4px; font-size:0.75rem; font-weight:700;">
        <span>🎯 Scan Results (Live)</span>
        <span style="font-size:0.68rem; font-weight:normal; color:#475569;">Total: <b>{len(results)}</b></span>
    </div>
    <div class="excel-container">
        <table class="excel-grid">
            <thead>
                <tr>
                    <th class="c-comp">Company (Date)</th>
                    <th class="c-col">Strk B/S</th>
                    <th class="c-col">P/P</th>
                    <th class="c-col">D/C</th>
                    <th class="c-col">R1 B/S</th>
                    <th class="c-col">R1 P/P</th>
                    <th class="c-col">R2 B/S</th>
                    <th class="c-col">R2 P/P</th>
                </tr>
            </thead>
            <tbody>
                {table_rows_html}
            </tbody>
        </table>
    </div>
</body>
</html>
"""

components.html(full_html, height=450, scrolling=False)

# Auto Refresh loop if Auto is ON
if st.session_state.auto_scan_active:
    import time
    time.sleep(15)
    st.rerun()
