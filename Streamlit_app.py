import os
import io
import json
import gzip
import time
import requests
from datetime import date
from typing import Dict, List, Optional, Tuple

import pandas as pd
import streamlit as st

# ============================================================
# AUTO TRADE v1
# UI retained from the approved 3-column mobile layout.
# Scanner calculations are isolated below the UI.
# Market data is fetched from Upstox REST Option Chain API.
# Auto mode remains disabled until a tested streaming adapter is added.
# ============================================================

st.set_page_config(page_title="Auto Trade", page_icon="📈", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
<style>
* { box-sizing: border-box; }
.block-container { width:100% !important; max-width:100% !important; padding:0.55rem 0.45rem 1rem 0.45rem !important; }
.auto-title { text-align:center; font-size:1.55rem; font-weight:800; line-height:1.2; margin:0.2rem 0 0.8rem 0; }
div[data-testid="stHorizontalBlock"] { display:grid !important; grid-template-columns:repeat(3,minmax(0,1fr)) !important; gap:0.45rem !important; width:100% !important; align-items:start !important; }
div[data-testid="stHorizontalBlock"] > div[data-testid="column"] { width:auto !important; min-width:0 !important; max-width:100% !important; flex:initial !important; padding:0 !important; }
div[data-testid="stWidgetLabel"] { min-width:0 !important; }
div[data-testid="stWidgetLabel"] p { font-size:0.78rem !important; font-weight:650 !important; line-height:1.15 !important; margin-bottom:0.18rem !important; overflow-wrap:anywhere !important; }
div[data-testid="stNumberInput"], div[data-testid="stSelectbox"] { width:100% !important; min-width:0 !important; }
div[data-testid="stNumberInput"] input { min-width:0 !important; width:100% !important; padding-left:0.3rem !important; padding-right:0.1rem !important; font-size:0.78rem !important; }
div[data-testid="stSelectbox"] div[role="combobox"] { min-width:0 !important; width:100% !important; font-size:0.76rem !important; }
div[data-testid="stNumberInput"] button { min-width:1.15rem !important; width:1.15rem !important; padding:0 !important; }
div.stButton, div.stButton > button { width:100% !important; min-width:0 !important; }
div.stButton > button { min-height:2.5rem !important; padding:0.25rem 0.12rem !important; font-size:0.72rem !important; white-space:normal !important; line-height:1.1 !important; }
div[data-testid="stToggle"] { min-width:0 !important; padding-top:0.35rem !important; }
div[data-testid="stToggle"] label p { font-size:0.72rem !important; white-space:normal !important; }
.cell-title { font-size:0.82rem; font-weight:700; margin:0 0 0.25rem 0; line-height:1.2; }
hr { margin:0.5rem 0 0.65rem 0 !important; }
.result-list { width:100%; display:flex; flex-direction:column; gap:6px; }
.result-card { width:100%; border:1px solid #9aa0a6; border-radius:7px; overflow:hidden; background:rgba(127,127,127,.035); }
.spread-row { display:grid; grid-template-columns:minmax(0,1.12fr) minmax(0,1fr) minmax(0,.78fr); gap:3px; align-items:center; padding:3px 4px; font-size:10px; line-height:1.15; }
.spread-row + .spread-row { border-top:1px solid #7775; }
.spread-label { font-weight:800; font-size:9px; opacity:.78; }
.spread-cell { min-width:0; text-align:center; overflow-wrap:anywhere; }
.spread-value { font-weight:750; }
.result-tag { display:inline-block; font-size:8px; font-weight:900; letter-spacing:.3px; border:1px solid currentColor; border-radius:3px; padding:1px 3px; margin-left:3px; vertical-align:middle; }
.result-card.ban-row { background:#ffd6d6 !important; color:#7a0000 !important; border:2px solid #b00020; }
@media (max-width:390px) { .spread-row { font-size:9px; padding:3px 2px; gap:2px; } }
.small-note {font-size:0.78rem; opacity:.8;}
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="auto-title">📈 Auto Trade</div>', unsafe_allow_html=True)

# ------------------------- UI (locked layout) -------------------------
row1 = st.columns(3, gap="small")
with row1[0]:
    st.markdown('<div class="cell-title">Delta</div>', unsafe_allow_html=True)
    delta_min = st.number_input("Min", min_value=0.05, max_value=0.90, value=0.15, step=0.01, format="%.2f", key="delta_min")
    delta_max = st.number_input("Max", min_value=0.05, max_value=0.90, value=0.20, step=0.01, format="%.2f", key="delta_max")
with row1[1]:
    ratio = st.selectbox("Ratio", ["1:3", "3:10", "1:4", "2:7"], key="ratio")
with row1[2]:
    option = st.selectbox("Option", ["CE", "PE", "Both"], key="option")

st.divider()
row2 = st.columns(3, gap="small")
with row2[0]:
    expiry = st.selectbox("Expiry", ["Current Month", "Far Month", "Third Month"], key="expiry")
with row2[1]:
    result_value = st.number_input("Result", min_value=-50000, max_value=50000, value=0, step=100, key="result_value")
with row2[2]:
    spread_cost = st.number_input("Cost of Spread", min_value=-50000, max_value=50000, value=0, step=100, key="spread_cost")

st.divider()
row3 = st.columns(3, gap="small")
with row3[0]:
    vol_gap = st.number_input("VOL Gap (%)", min_value=1.0, max_value=30.0, value=2.0, step=0.5, format="%.1f", key="vol_gap")
with row3[1]:
    st.markdown('<div class="cell-title">Auto Scan</div>', unsafe_allow_html=True)
    auto_scan = st.toggle("Auto ON/OFF", value=False, key="auto_scan")
with row3[2]:
    st.markdown('<div class="cell-title">Manual Scan</div>', unsafe_allow_html=True)
    manual_clicked = st.button("Manual Scan", type="primary", use_container_width=True)

# ------------------------- Scanner engine -------------------------
RATIOS = {"1:3": (1, 3), "3:10": (3, 10), "1:4": (1, 4), "2:7": (2, 7)}


def spread_value(short_leg: float, long_leg: float, ratio_pair: Tuple[int, int], lot_size: int) -> Tuple[float, str]:
    """Net amount for ratio legs. Positive = Debit; negative = Credit."""
    a, b = ratio_pair
    net_per_unit = (short_leg * a) - (long_leg * b)
    total = round(net_per_unit * int(lot_size), 2)
    return total, ("DEBIT" if total > 0 else "CREDIT" if total < 0 else "ZERO")


def within_limit(amount: float, configured: float) -> bool:
    """Signed input: +amount is max Debit; -amount is max Credit; zero accepts zero only."""
    if configured > 0:
        return 0 <= amount <= configured
    if configured < 0:
        return configured <= amount <= 0
    return amount == 0


def month_expiry_rank(expiries: List[str], selected: str) -> Optional[str]:
    vals = sorted({str(x) for x in expiries if str(x) and str(x).lower() != "nan"})
    if not vals:
        return None
    today = date.today()
    future = []
    for x in vals:
        try:
            d = pd.to_datetime(x).date()
            if d >= today:
                future.append((d, x))
        except Exception:
            pass
    future.sort()
    if not future:
        return None
    idx = {"Current Month": 0, "Far Month": 1, "Third Month": 2}.get(selected, 0)
    # Current/Far/Third are treated as first, second, third listed future expiries in v1.
    return future[min(idx, len(future)-1)][1]


def prepare_chain(df: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    required = {"symbol", "strike", "option", "expiry", "delta", "iv", "premium", "lot_size"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError("CSVમાં જરૂરી columns નથી: " + ", ".join(sorted(missing)))
    x = df.copy()
    x["option"] = x["option"].astype(str).str.upper()
    x["strike"] = pd.to_numeric(x["strike"], errors="coerce")
    for c in ["delta", "iv", "premium", "lot_size"]:
        x[c] = pd.to_numeric(x[c], errors="coerce")
    x = x.dropna(subset=["strike", "delta", "iv", "premium", "lot_size"])
    # Keep the full option chain: only Base-Strike candidates are Delta-filtered later.
    if cfg["option"] != "Both":
        x = x[x["option"] == cfg["option"]]
    if "ban" not in x.columns:
        x["ban"] = False
    x["ban"] = x["ban"].astype(str).str.lower().isin(["1", "true", "yes", "y", "ban"])
    if "result_date" not in x.columns:
        x["result_date"] = "—"
    return x


def build_company_result(g: pd.DataFrame, cfg: dict) -> Optional[dict]:
    ratio_pair = RATIOS[cfg["ratio"]]
    option_rows = []
    for opt in (["CE", "PE"] if cfg["option"] == "Both" else [cfg["option"]]):
        go = g[g["option"] == opt].copy()
        if go.empty:
            continue
        expiry = month_expiry_rank(go["expiry"].tolist(), cfg["expiry"])
        if not expiry:
            continue
        go = go[go["expiry"].astype(str) == str(expiry)].sort_values("strike")
        # Every strike in selected delta range is a possible base candidate.
        all_rows = g[(g["option"] == opt) & (g["expiry"].astype(str) == str(expiry))].copy()
        all_rows = all_rows.sort_values("strike").reset_index(drop=True)
        candidates = all_rows[(all_rows["delta"].abs() >= cfg["delta_min"]) & (all_rows["delta"].abs() <= cfg["delta_max"])]
        for _, base in candidates.iterrows():
            # Target is the nearest higher strike whose IV is at least Base IV + VOL gap.
            after = all_rows[all_rows["strike"] > base["strike"]]
            target = None
            for _, cand in after.iterrows():
                if cand["iv"] >= base["iv"] + cfg["vol_gap"]:
                    target = cand
                    break
            if target is None:
                continue
            gap = float(target["strike"] - base["strike"])
            base_strike = float(base["strike"] - gap)
            base_leg = all_rows[all_rows["strike"] == base_strike]
            if base_leg.empty:
                continue
            base_leg = base_leg.iloc[0]
            # For CE, first leg is lower strike; for PE, first leg is higher strike.
            # Pair builder follows the same directional gap on the option chain.
            def get_pair(first_strike: float, second_strike: float):
                p1 = all_rows[all_rows["strike"] == first_strike]
                p2 = all_rows[all_rows["strike"] == second_strike]
                if p1.empty or p2.empty:
                    return None
                return p1.iloc[0], p2.iloc[0]
            # Base spread: base strike minus gap versus base strike.
            base_pair = get_pair(base_strike, float(base["strike"]))
            target_pair = get_pair(float(base["strike"]), float(target["strike"]))
            if not base_pair or not target_pair:
                continue
            base_amt, base_kind = spread_value(float(base_pair[0]["premium"]), float(base_pair[1]["premium"]), ratio_pair, int(base["lot_size"]))
            target_amt, target_kind = spread_value(float(target_pair[0]["premium"]), float(target_pair[1]["premium"]), ratio_pair, int(base["lot_size"]))
            # Review candidates are all consecutive offsets between base and target, excluding Targeted Spread.
            review_matches = []
            steps = int(round(gap / max(float(all_rows["strike"].diff().dropna().median() or 1), 1)))
            step_size = float(all_rows["strike"].diff().dropna().median() or 1)
            for n in range(1, max(steps, 1)):
                p = get_pair(base_strike + n * step_size, float(base["strike"]) + n * step_size)
                if not p:
                    continue
                amt, kind = spread_value(float(p[0]["premium"]), float(p[1]["premium"]), ratio_pair, int(base["lot_size"]))
                review_matches.append({"name": f"R{n}", "amount": amt, "kind": kind})
            # Result filter: any Base or Review spread can satisfy it; never Targeted.
            eligible_result = []
            for item in [{"name": "BASE", "amount": base_amt, "kind": base_kind}] + review_matches:
                if within_limit(item["amount"], cfg["result_limit"]):
                    eligible_result.append(item)
            if not eligible_result or not within_limit(target_amt, cfg["cost_limit"]):
                continue
            # Best matching spread determines ranking and is recorded for transparency.
            if cfg["result_limit"] >= 0:
                chosen = max(eligible_result, key=lambda z: z["amount"])
            else:
                chosen = min(eligible_result, key=lambda z: z["amount"])
            # Card shows Targeted, Base, and one spread immediately before Targeted.
            review_display = None
            if steps >= 1:
                review_display = get_pair(float(base["strike"]) - step_size, float(target["strike"]) - step_size)
            if review_display:
                r_amt, r_kind = spread_value(float(review_display[0]["premium"]), float(review_display[1]["premium"]), ratio_pair, int(base["lot_size"]))
                review_text = f"{review_display[0]['strike']:g}/{review_display[1]['strike']:g}"
                review_price = f"{review_display[0]['premium']:g}/{review_display[1]['premium']:g}"
            else:
                r_amt, r_kind, review_text, review_price = None, "—", "—", "—"
            option_rows.append({
                "Company": str(base["symbol"]), "Option": opt, "Delta": round(float(base["delta"]), 3),
                "Lot Size": int(base["lot_size"]), "Result Date": str(base.get("result_date", "—")), "Targeted Strike": f"{base['strike']:g}/{target['strike']:g}",
                "Targeted Price": f"{base['premium']:g}/{target['premium']:g}", "Targeted D/C": f"{target_kind} ₹{abs(target_amt):,.0f}",
                "Base Strike": f"{base_pair[0]['strike']:g}/{base_pair[1]['strike']:g}", "Base Price": f"{base_pair[0]['premium']:g}/{base_pair[1]['premium']:g}",
                "Base D/C": f"{base_kind} ₹{abs(base_amt):,.0f}", "Review Strike": review_text, "Review Price": review_price,
                "Review D/C": f"{r_kind} ₹{abs(r_amt):,.0f}" if r_amt is not None else "—",
                "Matched Spread": chosen["name"], "Matched Amount": chosen["amount"], "F&O Ban": bool(base["ban"])
            })
    if not option_rows:
        return None
    # If CE and PE both qualify for same symbol, keep the best qualifying result row.
    return sorted(option_rows, key=lambda z: z["Matched Amount"], reverse=(cfg["result_limit"] >= 0))[0]


def run_scanner(df: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    clean = prepare_chain(df, cfg)
    rows = []
    for _, group in clean.groupby("symbol", sort=False):
        result = build_company_result(group, cfg)
        if result:
            rows.append(result)
    out = pd.DataFrame(rows)
    if not out.empty:
        out["Sort Debit"] = pd.to_numeric(out["Matched Amount"], errors="coerce").fillna(float("-inf"))
        out = out.sort_values("Sort Debit", ascending=False, kind="stable").drop(columns=["Sort Debit"]).reset_index(drop=True)
    return out


# ------------------------- Upstox market-data adapter -------------------------
UPSTOX_TOKEN = os.getenv("UPSTOX_ACCESS_TOKEN", "").strip()
INSTRUMENT_MASTER_URL = "https://assets.upstox.com/market-quote/instruments/exchange/complete.json.gz"
UPSTOX_BASE = "https://api.upstox.com/v2"


def upstox_headers():
    if not UPSTOX_TOKEN:
        raise RuntimeError("Render Environmentમાં UPSTOX_ACCESS_TOKEN મળ્યો નથી. Render → Environment તપાસો.")
    return {"Accept": "application/json", "Authorization": f"Bearer {UPSTOX_TOKEN}"}


@st.cache_data(ttl=6 * 60 * 60, show_spinner=False)
def load_nse_fo_equity_master() -> pd.DataFrame:
    """Download Upstox complete instrument master and retain NSE stock options only."""
    response = requests.get(INSTRUMENT_MASTER_URL, timeout=45)
    response.raise_for_status()
    raw = gzip.decompress(response.content)
    data = json.loads(raw.decode("utf-8"))
    master = pd.DataFrame(data)
    required = {"segment", "instrument_type", "underlying_type", "underlying_key", "underlying_symbol", "expiry", "strike_price", "lot_size", "instrument_key"}
    missing = required - set(master.columns)
    if missing:
        raise RuntimeError("Upstox instrument masterમાં જરૂરી fields નથી: " + ", ".join(sorted(missing)))
    master = master[(master["segment"] == "NSE_FO") & (master["underlying_type"] == "EQUITY") & (master["instrument_type"].isin(["CE", "PE"]))].copy()
    master["expiry_date"] = pd.to_datetime(master["expiry"], unit="ms", errors="coerce").dt.date.astype("string")
    master["strike_price"] = pd.to_numeric(master["strike_price"], errors="coerce")
    master["lot_size"] = pd.to_numeric(master["lot_size"], errors="coerce")
    master = master.dropna(subset=["underlying_key", "expiry_date", "strike_price", "lot_size"])
    return master


def get_selected_expiry(group: pd.DataFrame, selected: str) -> Optional[str]:
    dates = sorted({str(v) for v in group["expiry_date"].dropna().tolist() if str(v) >= str(date.today())})
    if not dates:
        return None
    index = {"Current Month": 0, "Far Month": 1, "Third Month": 2}.get(selected, 0)
    # UI choices map to first, second and third available monthly expiries.
    return dates[min(index, len(dates) - 1)]


def fetch_one_option_chain(instrument_key: str, expiry_date: str) -> list:
    url = f"{UPSTOX_BASE}/option/chain"
    response = requests.get(url, params={"instrument_key": instrument_key, "expiry_date": expiry_date}, headers=upstox_headers(), timeout=18)
    if response.status_code == 429:
        raise RuntimeError("Upstox API rate limit (429). થોડા સમય પછી ફરી Scan કરો.")
    if response.status_code == 401:
        raise RuntimeError("Upstox Access Token અમાન્ય અથવા expire થયો છે. Render Environmentમાં નવો token મૂકો.")
    response.raise_for_status()
    payload = response.json()
    if payload.get("status") != "success":
        raise RuntimeError(str(payload.get("errors") or payload))
    return payload.get("data", [])


def fetch_all_stock_option_data(expiry_choice: str, option_choice: str, progress) -> tuple[pd.DataFrame, dict]:
    """Fetch one option-chain response per eligible NSE F&O equity underlying."""
    master = load_nse_fo_equity_master()
    if master.empty:
        raise RuntimeError("Upstox masterમાં NSE F&O Equity options મળ્યા નથી.")
    # Select one expiry independently for every stock; do not include index options.
    jobs = []
    for (symbol, underlying_key), group in master.groupby(["underlying_symbol", "underlying_key"], sort=True):
        chosen_expiry = get_selected_expiry(group, expiry_choice)
        if chosen_expiry:
            jobs.append((str(symbol), str(underlying_key), chosen_expiry, group))
    records, errors = [], []
    total = len(jobs)
    for number, (symbol, underlying_key, exp, contracts) in enumerate(jobs, start=1):
        try:
            chain = fetch_one_option_chain(underlying_key, exp)
            lot_by_key = dict(zip(contracts["instrument_key"].astype(str), contracts["lot_size"].astype(int)))
            for item in chain:
                strike = item.get("strike_price")
                for opt, field in (("CE", "call_options"), ("PE", "put_options")):
                    if option_choice not in ("Both", opt):
                        continue
                    leg = item.get(field) or {}
                    market = leg.get("market_data") or {}
                    greeks = leg.get("option_greeks") or {}
                    key = str(leg.get("instrument_key", ""))
                    premium = market.get("ltp")
                    delta = greeks.get("delta")
                    iv = greeks.get("iv")
                    lot = lot_by_key.get(key)
                    if strike is None or premium is None or delta is None or iv is None or not lot:
                        continue
                    records.append({"symbol": symbol, "strike": float(strike), "option": opt, "expiry": exp,
                                    "delta": float(delta), "iv": float(iv), "premium": float(premium),
                                    "lot_size": int(lot), "ban": False, "result_date": "—"})
        except Exception as exc:
            errors.append(f"{symbol}: {exc}")
        progress.progress(number / max(total, 1), text=f"Upstox Option Chain: {number}/{total} stocks")
        # Conservative pacing to reduce burst requests; Upstox applies endpoint limits.
        time.sleep(0.25)
    frame = pd.DataFrame(records)
    stats = {"stocks": total, "rows": len(frame), "errors": errors}
    if frame.empty:
        detail = " | ".join(errors[:5])
        raise RuntimeError("Upstoxમાંથી કોઈ usable Option Chain data મળ્યો નથી. " + detail)
    return frame, stats


st.caption("Market Data: Upstox API • NSE F&O Equityના બધા ઉપલબ્ધ શેર • Manual Scan default • Auto Scan OFF")
with st.expander("Upstox API / Market Data Status", expanded=False):
    if UPSTOX_TOKEN:
        st.success("UPSTOX_ACCESS_TOKEN Render Environment Variableમાં ઉપલબ્ધ છે. Token સુરક્ષા માટે અહીં બતાવવામાં આવતો નથી.")
    else:
        st.error("UPSTOX_ACCESS_TOKEN Environment Variable મળ્યો નથી.")
    st.write("Manual Scan સમયે Upstox Instrument Masterમાંથી NSE F&O Equityના બધા શેર શોધી, પસંદ કરેલી expiryની Option Chain મેળવવામાં આવશે.")

cfg = {"delta_min": delta_min, "delta_max": delta_max, "ratio": ratio, "option": option,
       "expiry": expiry, "vol_gap": vol_gap, "result_limit": result_value, "cost_limit": spread_cost}

if delta_min > delta_max:
    st.error("Delta Min, Max Delta કરતાં મોટું ન હોઈ શકે.")
else:
    if auto_scan:
        st.warning("Auto Scan ON દેખાય છે, પરંતુ આ buildમાં REST Manual Scan જ સક્રિય છે. Live WebSocket adapter અલગથી integrate અને test કર્યા પછી જ continuous Auto Scan સક્રિય થશે.")
    if manual_clicked:
        try:
            with st.spinner("Upstoxમાંથી NSE F&Oના બધા સ્ટોકની Option Chain મેળવી રહ્યા છીએ..."):
                progress = st.progress(0, text="Upstox Instrument Master લોડ થઈ રહ્યું છે...")
                source_df, api_stats = fetch_all_stock_option_data(expiry, option, progress)
                progress.empty()
                results = run_scanner(source_df, cfg)
                st.session_state["scan_results"] = results
                st.session_state["scan_timestamp"] = pd.Timestamp.now().strftime("%d-%m-%Y %H:%M:%S")
                st.session_state["api_stats"] = api_stats
            st.success(f"API Scan પૂર્ણ: {api_stats['stocks']} F&O શેર તપાસ્યા • {api_stats['rows']} option rows મળ્યાં.")
            if api_stats["errors"]:
                st.warning(f"{len(api_stats['errors'])} શેરની API વિનંતી નિષ્ફળ ગઈ. નીચેના પ્રથમ 5 જુઓ: " + " | ".join(api_stats["errors"][:5]))
        except Exception as exc:
            st.error(f"Upstox API Scan નિષ્ફળ: {exc}")

# ------------------------- Result Card -------------------------
st.divider()
results = st.session_state.get("scan_results", pd.DataFrame())
if isinstance(results, pd.DataFrame) and not results.empty:
    # Show EVERY result; compact cards flow vertically. No horizontal scrolling.
    # Highest qualifying debit first, then lower debit/credit results.
    view = results.copy()
    view["_sort"] = pd.to_numeric(view.get("Matched Amount"), errors="coerce").fillna(float("-inf"))
    view = view.sort_values("_sort", ascending=False, kind="stable").drop(columns=["_sort"]).reset_index(drop=True)

    def esc(value):
        return (str(value).replace("&", "&amp;").replace("<", "&lt;")
                .replace(">", "&gt;").replace('"', "&quot;"))

    def amount_text(value):
        try:
            number = float(value)
            kind = "DEBIT" if number > 0 else "CREDIT" if number < 0 else "ZERO"
            return f"{kind} ₹{abs(number):,.0f}"
        except Exception:
            return "—"

    cards = ['<div class="result-list">']
    for _, row in view.iterrows():
        ban_class = " ban-row" if bool(row.get("F&O Ban", False)) else ""
        company = esc(row.get("Company", "—"))
        opt = esc(row.get("Option", ""))
        delta = esc(row.get("Delta", "—"))
        lot = esc(row.get("Lot Size", "—"))
        matched = esc(row.get("Matched Spread", "—"))
        # Strike and price pairs are stored as buy/sell order in the scanner.
        cards.append(f'<div class="result-card{ban_class}">')

        def spread_row(label, strike, price, amount, result_badge=False, main=False):
            badge = '<span class="result-tag">RESULT</span>' if result_badge else ''
            if main:
                first = (f'<span class="spread-label">{company} {opt} · Δ {delta} · LOT {lot}</span><br>'
                         f'<span class="spread-value">{label}: {esc(strike)}</span>')
            else:
                first = (f'<span class="spread-label">{label}</span><br>'
                         f'<span class="spread-value">{esc(strike)}</span>')
            return (f'<div class="spread-row"><div class="spread-cell">{first}</div>'
                    f'<div class="spread-cell"><span class="spread-label">BUY / SELL PRICE</span><br>'
                    f'<span class="spread-value">{esc(price)}</span></div>'
                    f'<div class="spread-cell"><span class="spread-label">DEBIT / CREDIT</span><br>'
                    f'<span class="spread-value">{esc(amount)}</span>{badge}</div></div>')

        cards.append(spread_row("TARGETED BUY / SELL", row.get("Targeted Strike", "—"), row.get("Targeted Price", "—"), row.get("Targeted D/C", "—"), main=True))
        cards.append(spread_row("BASE BUY / SELL", row.get("Base Strike", "—"), row.get("Base Price", "—"), row.get("Base D/C", "—"), matched == "BASE"))
        cards.append(spread_row("REVIEW BUY / SELL", row.get("Review Strike", "—"), row.get("Review Price", "—"), row.get("Review D/C", "—"), str(matched).startswith("R")))
        cards.append('</div>')
    cards.append('</div>')
    st.markdown("".join(cards), unsafe_allow_html=True)
    st.caption("દરેક કંપનીનું કાર્ડ 3 લાઇનનું છે. બધા Results નીચે સ્ક્રોલ કરતાં દેખાશે. લાલ કાર્ડ = F&O Ban.")
else:
    st.info("હજુ કોઈ Result નથી. Upstox APIમાંથી બધા NSE F&O Equity શેર સ્કેન કરવા Manual Scan દબાવો.")

st.caption("સાવચેતી: આ વર્ઝનમાં Upstox REST Option Chain પરથી Manual Scan થાય છે. Auto Scan માટે Live WebSocket હજી જોડાયેલું નથી. NSE Result Date અને F&O Ban feed પણ હજી જોડવાના બાકી છે. પરિણામો ટ્રેડિંગ નિર્ણય પહેલાં ચકાસો.")
