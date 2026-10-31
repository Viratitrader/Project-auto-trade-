import os
import gzip
import json
import time
from datetime import date
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

# =========================================================
# RENDER-READY PROJECT A PRO — INDEPENDENT TEST APP
# Uses Upstox REST Option Chain API. This is NOT a WebSocket feed.
# =========================================================
st.set_page_config(page_title="Project A Pro", page_icon="📊", layout="wide", initial_sidebar_state="collapsed")

OPTION_CHAIN_URL = "https://api.upstox.com/v2/option/chain"
INSTRUMENT_URLS = [
    "https://assets.upstox.com/market-quote/instruments/exchange/complete.json.gz",
    "https://assets.upstox.com/market-quote/instruments/exchange/NSE.json.gz",
]
TODAY = date.today()

st.markdown("""
<style>
* { box-sizing: border-box !important; }
html, body, [data-testid="stAppViewContainer"], [data-testid="stMain"],
.main, .block-container {
    width: 100% !important; max-width: 100% !important;
    overflow-x: hidden !important; margin: 0 !important;
}
.block-container { padding: 5px 8px !important; }
#MainMenu, header, footer { display: none !important; }

/* Desktop: preserve the existing horizontal rows */
div[data-testid="stHorizontalBlock"] {
    display: flex !important; flex-wrap: nowrap !important;
    gap: 6px !important; width: 100% !important;
    margin-bottom: 5px !important;
}
div[data-testid="stHorizontalBlock"] > div[data-testid="column"] {
    flex: 1 1 0% !important; width: 0 !important;
    min-width: 0 !important; max-width: 100% !important;
    padding: 0 2px !important;
}

/* Inputs must stay inside their own column */
div[data-testid="stTextInput"],
div[data-testid="stSelectbox"],
div[data-testid="stNumberInput"] {
    width: 100% !important; min-width: 0 !important;
}
div[data-testid="stTextInput"] input,
div[data-testid="stNumberInput"] input,
div[data-testid="stSelectbox"] [data-baseweb="select"] {
    width: 100% !important; min-width: 0 !important;
    max-width: 100% !important; min-height: 32px !important;
    font-size: 13px !important; font-weight: 600 !important;
}
label[data-testid="stWidgetLabel"] p {
    font-size: 12px !important; font-weight: 700 !important;
    white-space: normal !important; overflow: visible !important;
    margin-bottom: 2px !important;
}
.stButton button {
    width: 100% !important; min-width: 0 !important;
    min-height: 32px !important; padding: 2px 4px !important;
    font-size: 12px !important; font-weight: 700 !important;
    border-radius: 5px !important; background: #ef4444 !important;
    color: #fff !important; border: 0 !important;
}

/* Mobile: three-column filter rows and two-column cost/scanner rows */
@media screen and (max-width: 700px) {
    .block-container { padding: 4px 5px !important; }
    div[data-testid="stHorizontalBlock"] {
        display: grid !important;
        grid-template-columns: repeat(3, minmax(0, 1fr)) !important;
        gap: 5px !important; width: 100% !important;
        margin-bottom: 7px !important;
    }
    div[data-testid="stHorizontalBlock"]:has(> div[data-testid="column"]:nth-child(2)):not(:has(> div[data-testid="column"]:nth-child(3))) {
        grid-template-columns: repeat(2, minmax(0, 1fr)) !important;
    }
    div[data-testid="stHorizontalBlock"] > div[data-testid="column"] {
        width: 100% !important; min-width: 0 !important;
        max-width: 100% !important; flex: none !important;
        padding: 0 !important;
    }
    div[data-testid="stTextInput"] input,
    div[data-testid="stNumberInput"] input,
    div[data-testid="stSelectbox"] [data-baseweb="select"] {
        width: 100% !important; min-width: 0 !important;
        max-width: 100% !important; min-height: 34px !important;
        font-size: 12px !important; padding-left: 5px !important;
        padding-right: 5px !important;
    }
    label[data-testid="stWidgetLabel"] p {
        font-size: 11px !important; line-height: 1.15 !important;
        white-space: normal !important; overflow: visible !important;
    }
    .stButton button {
        width: 100% !important; min-width: 0 !important;
        min-height: 33px !important; font-size: 11px !important;
        padding: 2px !important; white-space: normal !important;
    }
    div[data-testid="stToggle"] {
        width: 100% !important; min-width: 0 !important;
        margin-top: 3px !important;
    }
    iframe { width: 100% !important; max-width: 100% !important; border: 0 !important; }
}
</style>
""", unsafe_allow_html=True)

# Token priority: Render environment variable -> Streamlit secrets -> manual session input.
access_token = os.getenv("UPSTOX_ACCESS_TOKEN", "").strip()
if not access_token:
    try:
        access_token = str(st.secrets.get("UPSTOX_ACCESS_TOKEN", "")).strip()
    except Exception:
        access_token = ""
if not access_token:
    if "manual_token" not in st.session_state:
        st.session_state.manual_token = ""
    with st.expander("🔑 Upstox Access Token સેટ કરો", expanded=not bool(st.session_state.manual_token)):
        token = st.text_input("Access Token", type="password", key="token_entry", label_visibility="collapsed", placeholder="Upstox token paste કરો")
        if token.strip() and token.strip() != st.session_state.manual_token:
            st.session_state.manual_token = token.strip()
            st.rerun()
    access_token = st.session_state.manual_token

for key, default in [("scan_results", []), ("auto_scan_active", False), ("last_scan_time", 0.0), ("last_scan_error", "")]:
    if key not in st.session_state:
        st.session_state[key] = default


def parse_delta_range(value):
    try:
        s = str(value).strip().replace(" ", "")
        if "-" in s:
            a, b = map(float, s.split("-", 1))
            if max(a, b) <= 1:
                a, b = a * 100, b * 100
            return min(a, b), max(a, b)
        n = float(s)
        if n <= 1:
            n *= 100
        return 0.0, n
    except Exception:
        return 10.0, 25.0


def parse_amount_range(value, default_high=5000.0):
    try:
        s = str(value).strip().replace(",", "").replace(" ", "")
        if "-" in s:
            a, b = map(float, s.split("-", 1))
            return min(a, b), max(a, b)
        return 0.0, float(s) if s else default_high
    except Exception:
        return 0.0, default_high


def parse_profit_input(value):
    try:
        return float(str(value).strip().replace(",", "").replace(" ", "") or 0)
    except Exception:
        return 0.0


@st.cache_data(ttl=3600, show_spinner=False)
def load_instruments():
    for url in INSTRUMENT_URLS:
        try:
            response = requests.get(url, timeout=25, headers={"User-Agent": "Mozilla/5.0"})
            response.raise_for_status()
            content = response.content
            if content[:2] == b"\x1f\x8b":
                content = gzip.decompress(content)
            data = json.loads(content.decode("utf-8"))
            if isinstance(data, dict):
                data = data.get("data", list(data.values()))
            frame = pd.DataFrame(data)
            if not frame.empty:
                return frame
        except Exception:
            continue
    return pd.DataFrame()


def convert_expiry_dates(series):
    numeric = pd.to_numeric(series, errors="coerce")
    result = pd.Series(pd.NaT, index=series.index, dtype="datetime64[ns]")
    mask = numeric.notna()
    if mask.any():
        median = numeric[mask].median()
        unit = "ms" if median > 100_000_000_000 else ("s" if median > 1_000_000_000 else None)
        if unit:
            result.loc[mask] = pd.to_datetime(numeric[mask], unit=unit, errors="coerce")
    missing = result.isna()
    if missing.any():
        result.loc[missing] = pd.to_datetime(series.loc[missing], errors="coerce")
    return result


@st.cache_data(ttl=3600, show_spinner=False)
def build_universe():
    frame = load_instruments()
    required = {"segment", "instrument_type", "underlying_type", "underlying_key", "expiry", "lot_size"}
    if frame.empty or not required.issubset(frame.columns):
        return pd.DataFrame()
    frame = frame[(frame.segment.astype(str) == "NSE_FO") & frame.instrument_type.astype(str).isin(["CE", "PE"]) & (frame.underlying_type.astype(str) == "EQUITY") & frame.underlying_key.astype(str).str.startswith("NSE_EQ|")].copy()
    if frame.empty:
        return pd.DataFrame()
    frame["expiry"] = convert_expiry_dates(frame["expiry"]).dt.date
    frame["lot_size"] = pd.to_numeric(frame["lot_size"], errors="coerce")
    frame = frame[frame.expiry.notna() & (frame.expiry >= TODAY) & (frame.lot_size > 0)].copy()
    if frame.empty:
        return pd.DataFrame()
    symbol_col = next((c for c in ["underlying_symbol", "trading_symbol"] if c in frame.columns), None)
    cols = ["underlying_key", "expiry", "lot_size"] + ([symbol_col] if symbol_col else [])
    out = frame[cols].drop_duplicates().copy()
    out["symbol"] = out[symbol_col].astype(str).str.strip() if symbol_col else out.underlying_key.astype(str).str.replace("NSE_EQ|", "", regex=False)
    return out[["underlying_key", "symbol", "expiry", "lot_size"]]


universe = build_universe()
has_universe = not universe.empty
expiries = sorted(universe.expiry.dropna().unique()) if has_universe else [TODAY]


def get_option_chain(underlying_key, expiry, token):
    headers = {"Accept": "application/json", "Authorization": f"Bearer {token}"}
    params = {"instrument_key": underlying_key, "expiry_date": expiry.isoformat()}
    try:
        response = requests.get(OPTION_CHAIN_URL, params=params, headers=headers, timeout=12)
        if response.status_code == 200:
            return response.json().get("data", []), None
        if response.status_code == 401:
            return [], "TOKEN_EXPIRED"
        if response.status_code == 429:
            return [], "RATE_LIMIT"
        return [], f"API_ERROR_{response.status_code}"
    except requests.exceptions.Timeout:
        return [], "FETCH_TIMEOUT"
    except requests.exceptions.RequestException:
        return [], "FETCH_ERROR"
    except Exception:
        return [], "FETCH_ERROR"


def extract_side_options(chain, option_type):
    key = "call_options" if option_type == "CE" else "put_options"
    options, spot = [], 0.0
    for row in chain:
        try:
            spot = spot or float(row.get("underlying_spot_price", 0) or 0)
            strike = float(row.get("strike_price", 0) or 0)
            opt = row.get(key, {}) or {}
            market = opt.get("market_data", {}) or {}
            greeks = opt.get("option_greeks", {}) or {}
            ltp = float(market.get("ltp", 0) or 0)
            delta = abs(float(greeks.get("delta", 0) or 0)) * 100
            if strike > 0 and ltp > 0:
                options.append({"strike": strike, "ltp": ltp, "delta": delta})
        except Exception:
            continue
    options.sort(key=lambda x: x["strike"])
    return options, spot


def scan_stock(item, expiry, option_type, delta_low, delta_high, gap_pct, buy_qty, sell_qty, debit_range, credit_range, min_profit, token):
    try:
        chain, error = get_option_chain(item["underlying_key"], expiry, token)
        if error or not chain:
            return None, error
        options, spot = extract_side_options(chain, option_type)
        if len(options) < 3 or spot <= 0:
            return None, None
        matches = [o for o in options if delta_low <= o["delta"] <= delta_high]
        if not matches:
            return None, None
        mid = (delta_low + delta_high) / 2
        base = min(matches, key=lambda x: abs(x["delta"] - mid))
        base_strike, base_ltp = base["strike"], base["ltp"]
        gap = spot * gap_pct / 100.0
        target_exact = base_strike + gap if option_type == "CE" else base_strike - gap
        if option_type == "CE":
            targets = [o for o in options if o["strike"] >= target_exact and o["strike"] > base_strike]
            target = min(targets, key=lambda x: x["strike"]) if targets else None
        else:
            targets = [o for o in options if o["strike"] <= target_exact and o["strike"] < base_strike]
            target = max(targets, key=lambda x: x["strike"]) if targets else None
        if not target:
            return None, None
        target_strike, target_ltp = target["strike"], target["ltp"]
        net_points = sell_qty * target_ltp - buy_qty * base_ltp
        amount = round(abs(net_points) * int(item["lot_size"]), 2)
        side = "ZERO" if abs(net_points) < 1e-6 else ("CREDIT" if net_points > 0 else "DEBIT")
        if side == "CREDIT" and not credit_range[0] <= amount <= credit_range[1]:
            return None, None
        if side == "DEBIT" and not debit_range[0] <= amount <= debit_range[1]:
            return None, None
        if amount < min_profit:
            return None, None
        actual_gap = abs(target_strike - base_strike)
        r1_buy = base_strike - actual_gap if option_type == "CE" else base_strike + actual_gap
        r1_sell = base_strike
        r1b = next((o for o in options if abs(o["strike"] - r1_buy) < .01), None)
        r1s = next((o for o in options if abs(o["strike"] - r1_sell) < .01), None)
        r2_buy = r1_buy - actual_gap if option_type == "CE" else r1_buy + actual_gap
        r2_sell = r1_buy
        r2b = next((o for o in options if abs(o["strike"] - r2_buy) < .01), None)
        r2s = next((o for o in options if abs(o["strike"] - r2_sell) < .01), None)
        fmt_pair = lambda a, b: f"{a:g}/{b:g}" if a and b else "-/-"
        fmt_price = lambda a, b: f"{a['ltp']:.2f}/{b['ltp']:.2f}" if a and b else "-/-"
        return {"symbol": str(item["symbol"]), "res_date": "", "delta_display": f"Δ{base['delta']:.2f}", "strk_bs": f"{base_strike:g}/{target_strike:g}", "pp": f"{base_ltp:.2f}/{target_ltp:.2f}", "dc": f"{'C' if side == 'CREDIT' else 'D' if side == 'DEBIT' else 'Z'}{amount:,.0f}", "r1_bs": fmt_pair(r1_buy, r1_sell), "r1_pp": fmt_price(r1b, r1s), "r2_bs": fmt_pair(r2_buy, r2_sell), "r2_pp": fmt_price(r2b, r2s), "sort_score": amount, "side": side, "lot_size": int(item["lot_size"])}, None
    except Exception:
        return None, None

# Header and controls
st.markdown("<div style='display:flex;justify-content:space-between;align-items:center;margin-bottom:2px'><b style='font-size:.9rem'>📊 Project A Pro</b><span style='font-size:.65rem;color:#0a8f42'>● REST API</span></div>", unsafe_allow_html=True)
if not has_universe:
    st.warning("Upstox instrument data લોડ થયું નથી. થોડીવાર પછી ફરી પ્રયાસ કરો.")

f1, f2, f3 = st.columns([1.2, .9, .9])
with f1: delta_input = st.text_input("Delta", "0.10 - 0.25")
with f2: ratio = st.selectbox("Ratio", ["1:3", "3:10", "1:4"])
with f3: option_type = st.selectbox("Option", ["CE", "PE"])
f4, f5 = st.columns(2)
with f4: expiry = st.selectbox("Expiry", expiries, format_func=lambda x: x.strftime("%d %b %Y"))
with f5: min_profit_input = st.text_input("Minimum Profit (₹)", "0")
sc1, sc2 = st.columns(2)
with sc1: debit_input = st.text_input("Debit Cost (₹)", "0 - 5000")
with sc2: credit_input = st.text_input("Credit Cost (₹)", "0 - 5000")

s1, s2 = st.columns(2)
with s1:
    st.markdown("<div style='text-align:center;background:#f0fdf4;border:1px solid #bbf7d0;border-radius:4px;padding:4px;font-size:.65rem;font-weight:700'>1. Debit ₹0 Scanner<br><small style='font-weight:400;color:#64748b'>Not implemented in this build</small></div>", unsafe_allow_html=True)
with s2:
    st.markdown("<div style='text-align:center;background:#fff1f2;border:1px solid #fecdd3;border-radius:4px;padding:3px;font-size:.65rem;font-weight:700'>2. % Gap Scanner</div>", unsafe_allow_html=True)
    gap_pct = st.number_input("Gap %", min_value=0.0, max_value=30.0, value=20.0, step=.5, label_visibility="collapsed")
    auto = st.toggle("Auto Scan (60 sec)", value=st.session_state.auto_scan_active)
    if auto != st.session_state.auto_scan_active:
        st.session_state.auto_scan_active = auto
        st.rerun()
    manual_scan = st.button("Scan", type="primary", use_container_width=True)

# Optional periodic rerun for Auto Scan. Requires streamlit-autorefresh in requirements.
if st.session_state.auto_scan_active:
    try:
        from streamlit_autorefresh import st_autorefresh
        st_autorefresh(interval=60_000, key="pro_auto_refresh")
    except Exception:
        st.warning("Auto refresh package ઉપલબ્ધ નથી; Auto Scan માટે requirements.txt માં streamlit-autorefresh ઉમેરો.")

now = time.time()
auto_due = st.session_state.auto_scan_active and now - st.session_state.last_scan_time >= 60
if manual_scan or auto_due:
    st.session_state.last_scan_time = now
    if not access_token:
        st.error("Upstox Access Token જરૂરી છે.")
    elif not has_universe:
        st.error("NSE F&O Universe ઉપલબ્ધ નથી.")
    else:
        ratios = {"1:3": (1, 3), "3:10": (3, 10), "1:4": (1, 4)}
        buy_qty, sell_qty = ratios[ratio]
        dlow, dhigh = parse_delta_range(delta_input)
        drange, crange = parse_amount_range(debit_input), parse_amount_range(credit_input)
        min_profit = parse_profit_input(min_profit_input)
        scan_items = universe[universe.expiry == expiry].drop_duplicates(subset=["underlying_key"]).reset_index(drop=True)
        results, critical = [], None
        progress = st.progress(0, text="Scanning NSE F&O symbols…")
        total = max(1, len(scan_items))
        with ThreadPoolExecutor(max_workers=5) as pool:
            futures = [pool.submit(scan_stock, row, expiry, option_type, dlow, dhigh, gap_pct, buy_qty, sell_qty, drange, crange, min_profit, access_token) for _, row in scan_items.iterrows()]
            for idx, future in enumerate(as_completed(futures), 1):
                try:
                    result, err = future.result()
                    if err in ("TOKEN_EXPIRED", "RATE_LIMIT") or (err and err.startswith("API_ERROR_")):
                        critical = err
                    if result:
                        results.append(result)
                except Exception:
                    pass
                progress.progress(idx / total, text=f"Scanning… {idx}/{total}")
        progress.empty()
        results.sort(key=lambda x: x["sort_score"], reverse=True)
        st.session_state.scan_results = results
        st.session_state.last_scan_error = critical or ""
        if critical == "TOKEN_EXPIRED": st.error("Upstox Token expire થયો છે. નવો token આપો.")
        elif critical == "RATE_LIMIT": st.error("Upstox Rate Limit (429). થોડીવાર રાહ જુઓ.")
        elif critical: st.error(f"Upstox API Error: {critical}")

# Results: locked compact 8-column table. Date intentionally blank until verified NSE result-date source is connected.
results = st.session_state.scan_results
rows = "".join(f"<tr><td class='company'><b>{r['symbol']}</b><small>{r['res_date'] or r['delta_display']}</small></td><td>{r['strk_bs']}</td><td>{r['pp']}</td><td class='dc'>{r['dc']}</td><td>{r['r1_bs']}</td><td>{r['r1_pp']}</td><td>{r['r2_bs']}</td><td>{r['r2_pp']}</td></tr>" for r in results)
html = f'''<!DOCTYPE html><html><head><meta name="viewport" content="width=device-width,initial-scale=1"><style>
*{{box-sizing:border-box;margin:0;padding:0;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}}html,body{{width:100%;overflow:hidden;background:transparent}}.heading{{display:flex;justify-content:space-between;font-size:11px;font-weight:700;margin:3px 0}}.wrap{{width:100%;border:1px solid #94a3b8;border-radius:4px;overflow:auto;max-height:300px;background:white}}table{{width:100%;table-layout:fixed;border-collapse:collapse;font-size:10px}}th,td{{border:1px solid #cbd5e1;text-align:center;padding:4px 1px;white-space:nowrap;overflow:hidden;text-overflow:clip}}th{{position:sticky;top:0;background:#e2e8f0;font-size:9px;color:#0f172a}}td{{height:27px}}th:first-child,td:first-child{{width:19%;text-align:left;padding-left:3px}}th:not(:first-child),td:not(:first-child){{width:11.57%}}.company b{{display:block;font-size:10px;line-height:1.1}}.company small{{display:block;font-size:8px;color:#0284c7;font-weight:700}}.dc{{font-weight:800;color:#047857}}.empty{{padding:14px 4px;text-align:center;color:#64748b;font-size:11px}}@media(max-width:700px){{table{{font-size:9px}}th{{font-size:8px;padding:4px 0}}td{{font-size:9px;padding:3px 0;height:26px}}.company b{{font-size:9px}}.company small{{font-size:8px}}}}
</style></head><body><div class="heading"><span>🎯 Scan Results</span><span>Total: {len(results)}</span></div><div class="wrap"><table><thead><tr><th>Company</th><th>Main Strike</th><th>Main Price</th><th>D/C</th><th>R1 Strike</th><th>R1 Price</th><th>R2 Strike</th><th>R2 Price</th></tr></thead><tbody>{rows if rows else '<tr><td colspan="8" class="empty">Scan કર્યા પછી પરિણામ અહીં દેખાશે</td></tr>'}</tbody></table></div></body></html>'''
components.html(html, height=340, scrolling=False)

st.caption("નોંધ: આ Render test build Upstox REST Option Chain API વાપરે છે; WebSocket feed, Debit ₹0 scanner, Premium Spike scanner, NSE official Result Date અને F&O ban validation આ buildમાં હજી જોડાયેલા નથી.")
