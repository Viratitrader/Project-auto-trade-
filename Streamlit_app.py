import os
import re
import gzip
import json
import time
import requests
import pandas as pd
from datetime import date
from concurrent.futures import ThreadPoolExecutor, as_completed
import streamlit as st
import streamlit.components.v1 as components

# =========================================================
# PAGE CONFIG & STRICT MOBILE COMPACT CSS
# =========================================================
st.set_page_config(
    page_title="Project A Pro",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
    /* Full view padding removal */
    .block-container {
        padding: 4px 6px !important;
        margin: 0px !important;
        max-width: 100% !important;
    }
    #MainMenu, header, footer { display: none !important; visibility: hidden; }

    /* Force mobile columns to stay strictly horizontal (No breaking) */
    div[data-testid="column"] {
        width: auto !important;
        flex: 1 1 0px !important;
        min-width: 0px !important;
        padding: 0px 2px !important;
    }
    div[data-testid="stHorizontalBlock"] {
        display: flex !important;
        flex-direction: row !important;
        flex-wrap: nowrap !important;
        align-items: flex-end !important;
        gap: 4px !important;
        margin-bottom: 4px !important;
    }

    /* Compact inputs styling */
    .stTextInput input, .stSelectbox select, .stNumberInput input {
        font-size: 0.65rem !important;
        padding: 2px 4px !important;
        height: 28px !important;
        font-weight: 600 !important;
    }
    label[data-testid="stWidgetLabel"] p {
        font-size: 0.62rem !important;
        font-weight: 700 !important;
        margin-bottom: 1px !important;
        color: #1e293b !important;
        white-space: nowrap !important;
    }

    /* Compact buttons & toggle */
    .stButton button {
        padding: 2px 4px !important;
        height: 28px !important;
        font-size: 0.68rem !important;
        font-weight: 700 !important;
        border-radius: 4px !important;
    }
    div[data-testid="stToggle"] {
        margin-bottom: 2px !important;
    }

    /* Expander styling for token */
    .streamlit-expanderHeader {
        font-size: 0.65rem !important;
        font-weight: 700 !important;
        padding: 2px 6px !important;
    }
</style>
""", unsafe_allow_html=True)

# =========================================================
# CONSTANTS & SAFE UPSTOX AUTH (RENDER COMPATIBLE)
# =========================================================
OPTION_CHAIN_URL = "https://api.upstox.com/v2/option/chain[span_5](start_span)"[span_5](end_span)
INSTRUMENT_URLS = [
    "https://assets.upstox.com/market-quote/instruments/exchange/complete.json.gz",[span_6](start_span)[span_6](end_span)
    "https://assets.upstox.com/market-quote/instruments/exchange/NSE.json.gz[span_7](start_span)"[span_7](end_span)
]
TODAY = date.today()[span_8](start_span)[span_8](end_span)

# 1. Render Environment Variables ચેક કરશે
access_token = os.getenv("UPSTOX_ACCESS_TOKEN", "").strip()

# 2. જો ન મળે તો Streamlit Secrets ચેક કરશે
if not access_token:
    try:
        access_token = str(st.secrets.get("UPSTOX_ACCESS_TOKEN", "")).strip()[span_9](start_span)[span_9](end_span)
    except Exception:
        access_token = ""

# 3. જો બંને જગ્યાએ ન હોય તો કૉમ્પેક્ટ એક્સપેન્ડરમાં ઇનપુટ બોક્સ આપશે (UI ખરાબ કર્યા વગર)
if not access_token:
    if "upstox_access_token" not in st.session_state:
        st.session_state.upstox_access_token = "[span_10](start_span)"[span_10](end_span)
    
    with st.expander("🔑 Upstox Access Token સેટ કરો", expanded=(not bool(st.session_state.upstox_access_token))):
        token_input = st.text_input(
            "Access Token",
            type="password",
            placeholder="Upstox token paste karo",
            key="token_input_box",
            label_visibility="collapsed"
        )
        if token_input.strip():
            st.session_state.upstox_access_token = token_input.strip()[span_11](start_span)[span_11](end_span)
            access_token = token_input.strip()[span_12](start_span)[span_12](end_span)
        else:
            access_token = st.session_state.get("upstox_access_token", "")[span_13](start_span)[span_13](end_span)

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
            res = requests.get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0"})[span_14](start_span)[span_14](end_span)
            res.raise_for_status()[span_15](start_span)[span_15](end_span)
            raw = gzip.decompress(res.content)[span_16](start_span)[span_16](end_span)
            data = json.loads(raw.decode("utf-8"))[span_17](start_span)[span_17](end_span)
            if isinstance(data, dict):
                data = data.get("data", list(data.values()))[span_18](start_span)[span_18](end_span)
            df = pd.DataFrame(data)[span_19](start_span)[span_19](end_span)
            if not df.empty:
                return df[span_20](start_span)[span_20](end_span)
        except Exception:
            continue
    return pd.DataFrame()

@st.cache_data(ttl=3600)
def build_universe():
    df = load_instruments()[span_21](start_span)[span_21](end_span)
    if df.empty:
        return pd.DataFrame()

    df = df[
        (df["segment"].astype(str) == "NSE_FO") &
        (df["instrument_type"].astype(str).isin(["CE", "PE"])) &
        (df["underlying_type"].astype(str) == "EQUITY") &
        (df["underlying_key"].astype(str).str.startswith("NSE_EQ|"))
    ].copy()[span_22](start_span)[span_22](end_span)

    df["expiry_dt"] = pd.to_datetime(df["expiry"], errors="coerce")[span_23](start_span)[span_23](end_span)
    df["expiry"] = df["expiry_dt"].dt.date[span_24](start_span)[span_24](end_span)
    df["lot_size"] = pd.to_numeric(df["lot_size"], errors="coerce")[span_25](start_span)[span_25](end_span)
    df = df[df["expiry"].notna() & (df["expiry"] >= TODAY) & (df["lot_size"] > 0)].copy()[span_26](start_span)[span_26](end_span)

    sym_col = next((c for c in ["underlying_symbol", "trading_symbol"] if c in df.columns), None)[span_27](start_span)[span_27](end_span)
    if sym_col:
        universe = df[["underlying_key", sym_col, "expiry", "lot_size"]].drop_duplicates().copy()[span_28](start_span)[span_28](end_span)
        universe["symbol"] = universe[sym_col].astype(str).str.strip()[span_29](start_span)[span_29](end_span)
    else:
        universe = df[["underlying_key", "expiry", "lot_size"]].drop_duplicates().copy()[span_30](start_span)[span_30](end_span)
        universe["symbol"] = universe["underlying_key"].astype(str).str.replace("NSE_EQ|", "", regex=False)[span_31](start_span)[span_31](end_span)

    return universe

universe = build_universe()[span_32](start_span)[span_32](end_span)
available_expiries = sorted(universe["expiry"].dropna().unique()) if not universe.empty else [TODAY][span_33](start_span)[span_33](end_span)

def parse_delta_range(text):
    text = str(text).strip().replace(" ", "")[span_34](start_span)[span_34](end_span)
    if "-" in text:
        a, b = text.split("-")[span_35](start_span)[span_35](end_span)
        low, high = float(a), float(b)[span_36](start_span)[span_36](end_span)
        if high <= 1.0:
            low *= 100[span_37](start_span)[span_37](end_span)
            high *= 100[span_38](start_span)[span_38](end_span)
        return min(low, high), max(low, high)[span_39](start_span)[span_39](end_span)
    val = float(text)[span_40](start_span)[span_40](end_span)
    if val <= 1.0:
        val *= 100[span_41](start_span)[span_41](end_span)
    return 0.0, val[span_42](start_span)[span_42](end_span)

def parse_amount_range(text):
    text = str(text).strip().replace(",", "")[span_43](start_span)[span_43](end_span)
    if "-" in text:
        a, b = text.split("-")[span_44](start_span)[span_44](end_span)
        return float(a), float(b)[span_45](start_span)[span_45](end_span)
    val = float(text) if text else 5000.0[span_46](start_span)[span_46](end_span)
    return 0.0, val[span_47](start_span)[span_47](end_span)

def get_option_chain(underlying_key, exp_date, token):
    headers = {"Accept": "application/json", "Authorization": f"Bearer {token}"}[span_48](start_span)[span_48](end_span)
    params = {"instrument_key": underlying_key, "expiry_date": exp_date.isoformat()}[span_49](start_span)[span_49](end_span)
    try:
        r = requests.get(OPTION_CHAIN_URL, params=params, headers=headers, timeout=12)[span_50](start_span)[span_50](end_span)
        if r.status_code == 200:
            return r.json().get("data", [])[span_51](start_span)[span_51](end_span)
    except Exception:
        pass
    return [][span_52](start_span)[span_52](end_span)

def extract_side_options(chain, opt_type):
    key = "call_options" if opt_type == "CE" else "put_options[span_53](start_span)"[span_53](end_span)
    items = []
    spot_price = 0.0
    for row in chain:
        try:
            spot = float(row.get("underlying_spot_price", 0) or 0)[span_54](start_span)[span_54](end_span)
            if spot > 0 and spot_price == 0:
                spot_price = spot[span_55](start_span)[span_55](end_span)
            strike = float(row.get("strike_price", 0) or 0)[span_56](start_span)[span_56](end_span)
            opt = row.get(key, {}) or {}[span_57](start_span)[span_57](end_span)
            mdata = opt.get("market_data", {}) or {}[span_58](start_span)[span_58](end_span)
            greeks = opt.get("option_greeks", {}) or {}[span_59](start_span)[span_59](end_span)
            ltp = float(mdata.get("ltp", 0) or 0)[span_60](start_span)[span_60](end_span)
            delta = abs(float(greeks.get("delta", 0) or 0)) * 100[span_61](start_span)[span_61](end_span)
            if strike > 0 and ltp > 0:[span_62](start_span)[span_62](end_span)
                items.append({"strike": strike, "ltp": ltp, "delta": delta})[span_63](start_span)[span_63](end_span)
        except Exception:
            continue
    items.sort(key=lambda x: x["strike"])[span_64](start_span)[span_64](end_span)
    return items, spot_price

# =========================================================
# SCAN LOGIC (% GAP ENGINE)
# =========================================================
def scan_stock_pg(item, exp_val, opt_type, delta_low, delta_high, gap_pct, b_qty, s_qty, deb_range, cred_range, min_pft):
    try:
        chain = get_option_chain(item["underlying_key"], exp_val, access_token)[span_65](start_span)[span_65](end_span)
        if not chain:
            return None

        options, spot_price = extract_side_options(chain, opt_type)
        if len(options) < 3 or spot_price <= 0:[span_66](start_span)[span_66](end_span)
            return None

        # 1. Base Strike by Delta
        delta_matches = [x for x in options if delta_low <= x["delta"] <= delta_high][span_67](start_span)[span_67](end_span)
        if not delta_matches:
            return None
        mid_delta = (delta_low + delta_high) / 2[span_68](start_span)[span_68](end_span)
        delta_matches.sort(key=lambda x: abs(x["delta"] - mid_delta))[span_69](start_span)[span_69](end_span)
        base_opt = delta_matches[0][span_70](start_span)[span_70](end_span)
        base_strike = base_opt["strike"][span_71](start_span)[span_71](end_span)
        base_ltp = base_opt["ltp"][span_72](start_span)[span_72](end_span)
        lot = int(item["lot_size"])[span_73](start_span)[span_73](end_span)

        # 2. Target Strike by % Gap
        gap_val = spot_price * (gap_pct / 100.0)[span_74](start_span)[span_74](end_span)
        target_exact = (base_strike + gap_val) if opt_type == "CE" else (base_strike - gap_val)[span_75](start_span)[span_75](end_span)

        if opt_type == "CE":
            targets = [x for x in options if x["strike"] >= target_exact and x["strike"] > base_strike][span_76](start_span)[span_76](end_span)
            if not targets:
                return None
            targets.sort(key=lambda x: x["strike"])[span_77](start_span)[span_77](end_span)
            target_opt = targets[0][span_78](start_span)[span_78](end_span)
        else:
            targets = [x for x in options if x["strike"] <= target_exact and x["strike"] < base_strike][span_79](start_span)[span_79](end_span)
            if not targets:
                return None
            targets.sort(key=lambda x: -x["strike"])[span_80](start_span)[span_80](end_span)
            target_opt = targets[0][span_81](start_span)[span_81](end_span)

        target_strike = target_opt["strike"][span_82](start_span)[span_82](end_span)
        target_ltp = target_opt["ltp"][span_83](start_span)[span_83](end_span)

        # 3. Main Net & Amount
        net_pt = (s_qty * target_ltp) - (b_qty * base_ltp)[span_84](start_span)[span_84](end_span)
        amount = round(abs(net_pt) * lot, 2)[span_85](start_span)[span_85](end_span)
        side = "CREDIT" if net_pt > 0 else ("DEBIT" if net_pt < 0 else "ZERO")[span_86](start_span)[span_86](end_span)

        if side == "CREDIT" and not (cred_range[0] <= amount <= cred_range[1]):[span_87](start_span)[span_87](end_span)
            return None
        if side == "DEBIT" and not (deb_range[0] <= amount <= deb_range[1]):[span_88](start_span)[span_88](end_span)
            return None
        if amount < min_pft:[span_89](start_span)[span_89](end_span)
            return None

        # 4. R1 Spread (Previous Spread)
        actual_gap = abs(target_strike - base_strike)[span_90](start_span)[span_90](end_span)
        r1_buy_strike = (base_strike - actual_gap) if opt_type == "CE" else (base_strike + actual_gap)[span_91](start_span)[span_91](end_span)
        r1_sell_strike = base_strike[span_92](start_span)[span_92](end_span)

        r1_b = next((x for x in options if abs(x["strike"] - r1_buy_strike) < 0.01), None)[span_93](start_span)[span_93](end_span)
        r1_s = next((x for x in options if abs(x["strike"] - r1_sell_strike) < 0.01), None)[span_94](start_span)[span_94](end_span)
        r1_txt = f"{r1_buy_strike:g}/{r1_sell_strike:g}" if (r1_b and r1_s) else "-/-"
        r1_pp = f"{r1_b['ltp']:.2f}/{r1_s['ltp']:.2f}" if (r1_b and r1_s) else "-/-"

        # 5. R2 Spread (Sequence)
        r2_buy_strike = (r1_buy_strike - actual_gap) if opt_type == "CE" else (r1_buy_strike + actual_gap)[span_95](start_span)[span_95](end_span)
        r2_sell_strike = r1_buy_strike

        r2_b = next((x for x in options if abs(x["strike"] - r2_buy_strike) < 0.01), None)[span_96](start_span)[span_96](end_span)
        r2_s = next((x for x in options if abs(x["strike"] - r2_sell_strike) < 0.01), None)[span_97](start_span)[span_97](end_span)
        r2_txt = f"{r2_buy_strike:g}/{r2_sell_strike:g}" if (r2_b and r2_s) else "-/-"
        r2_pp = f"{r2_b['ltp']:.2f}/{r2_s['ltp']:.2f}" if (r2_b and r2_s) else "-/-"

        # Best Value Priority Sorting (Best credit first)
        sort_score = amount if side == "CREDIT" else (-amount)

        return {
            "symbol": item["symbol"],[span_98](start_span)[span_98](end_span)
            "delta_display": f"Δ{base_opt['delta']:.2f}",
            "res_date": "",
            "strk_bs": f"{base_strike:g}/{target_strike:g}",
            "pp": f"{base_ltp:.2f}/{target_ltp:.2f}",
            "dc": f"{'C' if side == 'CREDIT' else 'D'}{amount:,.0f}",
            "r1_bs": r1_txt,
            "r1_pp": r1_pp,
            "r2_bs": r2_txt,
            "r2_pp": r2_pp,
            "sort_score": sort_score
        }
    except Exception:
        return None

# =========================================================
# HEADER & FILTER PANELS (STRICT HORIZONTAL COMPACT)
# =========================================================
st.markdown("<div style='display:flex;justify-content:space-between;align-items:center;margin-bottom:2px;'><b style='font-size:0.85rem;'>📊 Project A Pro</b><span style='font-size:0.65rem;color:green;'>🟢 Live</span></div>", unsafe_allow_html=True)

# Row 1: 5 Filters Horizontal
f1, f2, f3, f4, f5 = st.columns([1.1, 0.9, 0.8, 1.1, 0.9])
with f1:
    delta_in = st.text_input("Delta", "0.10 - 0.25")[span_99](start_span)[span_99](end_span)
with f2:
    ratio_in = st.selectbox("Ratio", ["1:3", "3:10", "1:4", "2:7"])[span_100](start_span)[span_100](end_span)[span_101](start_span)[span_101](end_span)
with f3:
    opt_in = st.selectbox("Option Type", ["CE", "PE"])[span_102](start_span)[span_102](end_span)
with f4:
    exp_in = st.selectbox("Expiry", available_expiries, format_func=lambda x: x.strftime("%d %b"))[span_103](start_span)[span_103](end_span)[span_104](start_span)[span_104](end_span)
with f5:
    res_profit_in = st.text_input("Result (₹)", "0")[span_105](start_span)[span_105](end_span)

# Row 2: Spread Cost Side by Side
sc1, sc2 = st.columns(2)
with sc1:
    deb_in = st.text_input("Debit Spread Cost (₹)", "0 - 5000")[span_106](start_span)[span_106](end_span)
with sc2:
    cred_in = st.text_input("Credit Spread Cost (₹)", "0 - 5000")[span_107](start_span)[span_107](end_span)

# Row 3: 3 Cards Side by Side
m1, m2, m3 = st.columns(3)
with m1:
    st.markdown("<div style='background:#f0fdf4;padding:4px;border-radius:4px;border:1px solid #bbf7d0;font-size:0.65rem;font-weight:700;text-align:center;'>1. Debit ₹0<br><span style='font-size:0.55rem;font-weight:normal;color:gray;'>Pending</span></div>", unsafe_allow_html=True)[span_108](start_span)[span_108](end_span)

with m2:
    st.markdown("<div style='background:#fff1f2;padding:3px;border-radius:4px;border:1px solid #fecdd3;margin-bottom:2px;font-size:0.65rem;font-weight:700;text-align:center;'>2. % Gap (0-30%)</div>", unsafe_allow_html=True)[span_109](start_span)[span_109](end_span)
    gap_pct_val = st.number_input("Gap %", min_value=0.0, max_value=30.0, value=20.0, step=0.5, label_visibility="collapsed")[span_110](start_span)[span_110](end_span)
    
    # Auto Toggle and Manual Scan strictly inline inside Card
    ca, cb = st.columns([1, 1.3])
    with ca:
        auto_toggle = st.toggle("Auto", value=st.session_state.auto_scan_active)[span_111](start_span)[span_111](end_span)
        if auto_toggle != st.session_state.auto_scan_active:
            st.session_state.auto_scan_active = auto_toggle
    with cb:
        man_scan_btn = st.button("Manual Scan", type="primary", use_container_width=True)[span_112](start_span)[span_112](end_span)

with m3:
    st.markdown("<div style='background:#fefce8;padding:4px;border-radius:4px;border:1px solid #fef08a;font-size:0.65rem;font-weight:700;text-align:center;'>3. Spike UP/DN<br><span style='font-size:0.55rem;font-weight:normal;color:gray;'>Pending</span></div>", unsafe_allow_html=True)[span_113](start_span)[span_113](end_span)

# =========================================================
# SCAN EXECUTION
# =========================================================
should_scan = man_scan_btn or st.session_state.auto_scan_active[span_114](start_span)[span_114](end_span)

if should_scan:
    if not access_token:
        st.error("Access Token required")[span_115](start_span)[span_115](end_span)
    else:
        ratio_map = {"1:3": (1, 3), "3:10": (3, 10), "1:4": (1, 4), "2:7": (2, 7)}[span_116](start_span)[span_116](end_span)
        b_qty, s_qty = ratio_map[ratio_in][span_117](start_span)[span_117](end_span)
        d_low, d_high = parse_delta_range(delta_in)
        deb_range = parse_amount_range(deb_in)
        cred_range = parse_amount_range(cred_in)
        min_pft = float(res_profit_in) if res_profit_in else 0.0

        scan_universe = universe[universe["expiry"] == exp_in].drop_duplicates(subset=["underlying_key"]).reset_index(drop=True)[span_118](start_span)[span_118](end_span)
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

        # Sort: Best Value (highest credit) first
        raw_results.sort(key=lambda x: x["sort_score"], reverse=True)
        st.session_state.scan_results = raw_results

# =========================================================
# 8-COLUMN EXACT FORMAT RESULT TABLE (ZERO SCROLL FIT)
# =========================================================
results = st.session_state.scan_results

table_rows_html = ""
for i in range(max(10, len(results))):
    if i < len(results):
        r = results[i]
        date_badge = f"<span class='comp-date'>📅{r['res_date']} {r['delta_display']}</span>" if r['res_date'] else f"<span class='comp-date'>{r['delta_display']}</span>"
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
        margin-top: 3px;
    }}
    .excel-grid {{
        width: 100%;
        border-collapse: collapse;
        font-size: 0.60rem;
        table-layout: fixed;
    }}
    .excel-grid th, .excel-grid td {{
        border: 1px solid #cbd5e1;
        padding: 3px 1px;
        text-align: center;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
    }}
    .excel-grid th {{
        background-color: #e2e8f0;
        color: #0f172a;
        font-weight: 700;
        font-size: 0.58rem;
    }}
    .excel-grid td {{ height: 26px; }}
    
    /* 8 Columns exact proportions */
    .c-comp {{ width: 23%; text-align: left !important; padding-left: 2px !important; }}
    .c-col  {{ width: 11%; }}
    
    .comp-name {{ font-weight: 700; color: #0f172a; font-size: 0.62rem; line-height: 1.1; }}
    .comp-date {{ font-size: 0.50rem; color: #0284c7; font-weight: 600; display: block; }}
    .highlight-dc {{ font-weight: 700; color: #047857; }}
</style>
</head>
<body>
    <div style="display:flex; justify-content:space-between; align-items:center; margin-top:2px; font-size:0.70rem; font-weight:700;">
        <span>🎯 Scan Results</span>
        <span style="font-size:0.65rem; font-weight:normal; color:#475569;">Total: <b>{len(results)}</b></span>
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

components.html(full_html, height=440, scrolling=False)

# Auto Refresh loop if Auto is ON
if st.session_state.auto_scan_active:
    time.sleep(15)
    st.rerun()
