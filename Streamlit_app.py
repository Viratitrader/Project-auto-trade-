import os
import io
import json
from datetime import date
from typing import Dict, List, Optional, Tuple

import pandas as pd
import streamlit as st

# ============================================================
# AUTO TRADE v1
# UI retained from the approved 3-column mobile layout.
# Scanner calculations are isolated below the UI.
# Market-data adapter is intentionally explicit: connect the
# user's Upstox option-chain/WebSocket feed before live trading.
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
.result-wrap { overflow-x:auto; width:100%; }
table.results { border-collapse:collapse; width:100%; min-width:980px; font-size:11px; }
table.results th, table.results td { border:1px solid #7776; padding:4px 5px; text-align:center; white-space:nowrap; }
table.results th { font-weight:800; background:rgba(120,120,120,.14); }
tr.ban-row { background:#ffd6d6 !important; color:#7a0000 !important; font-weight:700; }
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
                "Result Date": str(base.get("result_date", "—")), "Targeted Strike": f"{base['strike']:g}/{target['strike']:g}",
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
        out = out.sort_values("Matched Amount", ascending=(cfg["result_limit"] < 0)).reset_index(drop=True)
    return out


# ------------------------- Data input / status -------------------------
st.caption("Scanner v1 • Manual mode is the default. Auto Scan remains OFF until you switch it ON.")
with st.expander("Market Data / CSV Input", expanded=True):
    st.write("હાલના પ્રથમ વર્ઝનમાં Scanner Engine ચકાસવા Option Chain CSV અપલોડ કરો. CSVમાં નીચેના columns જરૂરી છે:")
    st.code("symbol,strike,option,expiry,delta,iv,premium,lot_size\nABC,100,CE,2026-11-26,0.18,35,30,100", language="text")
    st.caption("Optional columns: ban (true/false), result_date. Live Upstox/WebSocket adapter હજી જોડાયેલો નથી.")
    uploaded = st.file_uploader("Option Chain CSV", type=["csv"], key="chain_csv")

cfg = {"delta_min": delta_min, "delta_max": delta_max, "ratio": ratio, "option": option,
       "expiry": expiry, "vol_gap": vol_gap, "result_limit": result_value, "cost_limit": spread_cost}

if delta_min > delta_max:
    st.error("Delta Min, Max Delta કરતાં મોટું ન હોઈ શકે.")
else:
    should_scan = manual_clicked
    if auto_scan:
        st.warning("Auto Scan ON છે, પરંતુ Live WebSocket data adapter જોડાયેલો નથી. હાલ CSV data પર live scan કરવાનો દાવો કરવામાં આવતો નથી.")
    if uploaded is not None and (should_scan or auto_scan):
        try:
            source_df = pd.read_csv(uploaded)
            results = run_scanner(source_df, cfg)
            st.session_state["scan_results"] = results
            st.session_state["scan_timestamp"] = pd.Timestamp.now().strftime("%d-%m-%Y %H:%M:%S")
        except Exception as exc:
            st.error(f"Scanner error: {exc}")
    elif manual_clicked and uploaded is None:
        st.info("Manual Scan માટે પહેલાં Option Chain CSV અપલોડ કરો. Upstox Live connection આગળના integration stepમાં જોડાશે.")

# ------------------------- Result Card -------------------------
st.divider()
results = st.session_state.get("scan_results", pd.DataFrame())
if isinstance(results, pd.DataFrame) and not results.empty:
    st.markdown(f"**Results: {len(results)}**  ·  Last Scan: {st.session_state.get('scan_timestamp', '—')}")
    # Display only the 3 spreads requested: Targeted, Base, and one step before Targeted.
    display_cols = ["Company", "Delta", "Result Date", "Targeted Strike", "Targeted Price", "Targeted D/C",
                    "Base Strike", "Base Price", "Base D/C", "Review Strike", "Review Price", "Review D/C", "Matched Spread"]
    view = results[display_cols].head(10).copy()
    html = ['<div class="result-wrap"><table class="results"><thead><tr>']
    html += [f"<th>{c}</th>" for c in display_cols]
    html.append("</tr></thead><tbody>")
    for _, row in view.iterrows():
        cls = ' class="ban-row"' if bool(results.loc[row.name, "F&O Ban"]) else ""
        html.append(f"<tr{cls}>")
        for c in display_cols:
            val = row[c]
            html.append(f"<td>{str(val)}</td>")
        html.append("</tr>")
    html.append("</tbody></table></div>")
    st.markdown("".join(html), unsafe_allow_html=True)
    st.caption("લાલ રંગની Row = NSE F&O Ban (CSVના 'ban' column મુજબ). એક સ્ક્રીનમાં 10 સુધી પરિણામ; વધુ હોય તો આગળના પરિણામ માટે સ્ક્રોલ કરો.")
else:
    st.info("હજુ કોઈ Result નથી. Option Chain CSV અપલોડ કરીને Manual Scan દબાવો.")

st.caption("સાવચેતી: આ v1માં CSV આધારિત scanner calculation છે. Upstox authentication, NSE result-date feed અને live WebSocket જોડ્યા પછી જ તેને live market scanner તરીકે વાપરવો.")
