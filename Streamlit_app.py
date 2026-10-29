import os
import time
import datetime
import pandas as pd
import streamlit as st

# Page layout & styling
st.set_page_config(page_title="Project A Pro - Options Ratio Spread Scanner", layout="wide")

# Custom CSS for UI & Result Company Styling
st.markdown("""
<style>
    .block-container { padding-top: 1.5rem; padding-bottom: 2rem; }
    .scanner-card {
        background-color: #f8f9fa;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        padding: 12px;
        margin-bottom: 15px;
    }
    .scanner-title { font-weight: 600; font-size: 0.95rem; margin-bottom: 8px; color: #1e293b; }
    .result-badge {
        background-color: #d97706;
        color: #ffffff;
        font-weight: 700;
        font-size: 0.72rem;
        padding: 2px 7px;
        border-radius: 4px;
        margin-left: 6px;
        vertical-align: middle;
    }
    .badge-debit { background-color: #dcfce7; color: #15803d; padding: 4px 10px; border-radius: 4px; font-weight: 600; display: inline-block; }
    .badge-credit { background-color: #fee2e2; color: #b91c1c; padding: 4px 10px; border-radius: 4px; font-weight: 600; display: inline-block; }
</style>
""", unsafe_allow_html=True)

# ----------------- SESSION STATE MANAGEMENT FOR AUTO SCAN -----------------
if "auto_mode" not in st.session_state:
    st.session_state.auto_mode = False

# ----------------- TOP HEADER -----------------
head_col1, head_col2 = st.columns([3, 1.5])
with head_col1:
    st.markdown("### 📊 Project A Pro")
    st.caption("Options Ratio Spread Scanner")

with head_col2:
    status_text = "🟢 Auto Scanning Active (5s)" if st.session_state.auto_mode else "⚪ Manual Mode"
    st.markdown(f"**Status:** `{status_text}`<br><small>🕒 {datetime.datetime.now().strftime('%d %b %Y %H:%M:%S')}</small>", unsafe_allow_html=True)

# ----------------- GLOBAL CONTROLS BAR -----------------
c1, c2, c3, c4, c5 = st.columns([1.2, 1, 1.2, 1.2, 2])
with c1:
    delta_range = st.selectbox("Delta", ["0.20 - 0.25", "0.15 - 0.20", "0.25 - 0.30"], index=0)
with c2:
    ratio = st.selectbox("Ratio", ["1 : 2", "1 : 3"], index=1)
with c3:
    option_type = st.selectbox("Option Type", ["CE (Call)", "PE (Put)"], index=0)
with c4:
    expiry = st.selectbox("Expiry", ["26 Sep 2026", "06 Oct 2026", "29 Oct 2026"], index=0)
with c5:
    st.markdown("**Spread Cost (₹)**")
    sc1, sc2 = st.columns(2)
    with sc1:
        st.text_input("Debit Range", value="0 - 5000", label_visibility="collapsed")
    with sc2:
        st.text_input("Credit Range", value="0 - 5000", label_visibility="collapsed")

st.markdown("---")

# ----------------- SCANNER TOOLBAR (3 MODULES) -----------------
mod_col1, mod_col2, mod_col3 = st.columns(3)

with mod_col1:
    st.markdown("<div class='scanner-card'><div class='scanner-title'>1. Debit ₹0 Scanner</div>", unsafe_allow_html=True)
    m1_a, m1_b, m1_c = st.columns([1, 1, 1.2])
    with m1_a:
        if st.button("Auto", key="m1_auto", use_container_width=True):
            st.session_state.auto_mode = True
            st.rerun()
    with m1_b:
        if st.button("Manual", key="m1_man", use_container_width=True):
            st.session_state.auto_mode = False
            st.rerun()
    with m1_c:
        if st.button("Scan", key="m1_scan", type="primary", use_container_width=True):
            st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

with mod_col2:
    st.markdown("<div class='scanner-card'><div class='scanner-title'>2. % Gap Scanner</div>", unsafe_allow_html=True)
    m2_inp, m2_a, m2_b, m2_c = st.columns([0.8, 1, 1, 1.2])
    with m2_inp: st.number_input("Gap %", value=20, label_visibility="collapsed", key="gap_val")
    with m2_a:
        if st.button("Auto", key="m2_auto", use_container_width=True):
            st.session_state.auto_mode = True
            st.rerun()
    with m2_b:
        if st.button("Manual", key="m2_man", use_container_width=True):
            st.session_state.auto_mode = False
            st.rerun()
    with m2_c:
        if st.button("Scan", key="m2_scan", type="primary", use_container_width=True):
            st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

with mod_col3:
    st.markdown("<div class='scanner-card'><div class='scanner-title'>3. Option Premium Spike (UP / DOWN)</div>", unsafe_allow_html=True)
    m3_inp, m3_a, m3_b, m3_c = st.columns([0.8, 1, 1, 1.2])
    with m3_inp: st.number_input("Spike %", value=10, label_visibility="collapsed", key="spike_val")
    with m3_a:
        if st.button("Auto", key="m3_auto", use_container_width=True):
            st.session_state.auto_mode = True
            st.rerun()
    with m3_b:
        if st.button("Manual", key="m3_man", use_container_width=True):
            st.session_state.auto_mode = False
            st.rerun()
    with m3_c:
        if st.button("Scan", key="m3_scan", type="primary", use_container_width=True):
            st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

# ----------------- SCAN RESULTS TABLE -----------------
res_head1, res_head2, res_head3 = st.columns([2, 1, 1])
with res_head1:
    st.markdown("#### 🎯 Scan Results (Live)")
with res_head2:
    st.markdown("**Total Results:** `24`")
with res_head3:
    search_query = st.text_input("Search company...", placeholder="Search company...", label_visibility="collapsed")

# Complete Live Data Records
data = [
    {"id": 1, "company": "RELIANCE", "delta_lot": "Δ 0.22 | Lot 500", "buy_strike": 840, "buy_price": 118.50, "sell_strike": 900, "sell_price": 39.20, "spread": "₹0 (Debit)", "type": "debit", "result_date": "06 Oct 2026", "has_result": True},
    {"id": 2, "company": "TCS", "delta_lot": "Δ 0.21 | Lot 500", "buy_strike": 3200, "buy_price": 145.30, "sell_strike": 3300, "sell_price": 48.80, "spread": "₹120 (Credit)", "type": "credit", "result_date": "06 Oct 2026", "has_result": True},
    {"id": 3, "company": "INFY", "delta_lot": "Δ 0.23 | Lot 500", "buy_strike": 1520, "buy_price": 62.40, "sell_strike": 1580, "sell_price": 19.50, "spread": "₹0 (Debit)", "type": "debit", "result_date": "06 Oct 2026", "has_result": False},
    {"id": 4, "company": "HDFCBANK", "delta_lot": "Δ 0.24 | Lot 500", "buy_strike": 1640, "buy_price": 74.20, "sell_strike": 1700, "sell_price": 22.10, "spread": "₹50 (Credit)", "type": "credit", "result_date": "06 Oct 2026", "has_result": False},
    {"id": 5, "company": "ICICIBANK", "delta_lot": "Δ 0.21 | Lot 500", "buy_strike": 1120, "buy_price": 48.90, "sell_strike": 1180, "sell_price": 15.60, "spread": "₹0 (Debit)", "type": "debit", "result_date": "06 Oct 2026", "has_result": True},
    {"id": 6, "company": "SBIN", "delta_lot": "Δ 0.20 | Lot 500", "buy_strike": 360, "buy_price": 36.70, "sell_strike": 920, "sell_price": 11.40, "spread": "₹80 (Credit)", "type": "credit", "result_date": "06 Oct 2026", "has_result": False},
    {"id": 7, "company": "BHARTIARTL", "delta_lot": "Δ 0.22 | Lot 500", "buy_strike": 880, "buy_price": 42.10, "sell_strike": 940, "sell_price": 12.30, "spread": "₹0 (Debit)", "type": "debit", "result_date": "06 Oct 2026", "has_result": False},
    {"id": 8, "company": "LT", "delta_lot": "Δ 0.21 | Lot 500", "buy_strike": 3600, "buy_price": 158.20, "sell_strike": 3700, "sell_price": 52.60, "spread": "₹100 (Credit)", "type": "credit", "result_date": "06 Oct 2026", "has_result": True},
]

# Table Header
cols = st.columns([0.4, 2, 1, 1.2, 1, 1.2, 1.3, 1.2])
headers = ["#", "Company (Delta | Lot)", "Buy Strike", "Buy Price (LTP)", "Sell Strike", "Sell Price (LTP)", "Debit / Credit", "Result Date"]
for col, header in zip(cols, headers):
    col.markdown(f"**{header}**")

st.markdown("<hr style='margin: 0.2rem 0 0.8rem 0;'>", unsafe_allow_html=True)

# Render Rows with Result Highlighting
for row in data:
    if search_query and search_query.upper() not in row["company"]:
        continue
        
    c_idx, c_name, c_bstrike, c_bltp, c_sstrike, c_sltp, c_spread, c_rdate = st.columns([0.4, 2, 1, 1.2, 1, 1.2, 1.3, 1.2])
    
    # Check if Result Company
    is_result = row["has_result"]
    bg_style = "background-color: #fef9c3; border-left: 4px solid #f59e0b; padding-left: 6px; border-radius: 4px;" if is_result else ""
    
    c_idx.write(f"{row['id']}")
    
    if is_result:
        c_name.markdown(f"<div style='{bg_style}'><b>{row['company']}</b> <span class='result-badge'>RESULT</span><br><small style='color:gray;'>{row['delta_lot']}</small></div>", unsafe_allow_html=True)
    else:
        c_name.markdown(f"<b>{row['company']}</b><br><small style='color:gray;'>{row['delta_lot']}</small>", unsafe_allow_html=True)
        
    c_bstrike.write(f"{row['buy_strike']}")
    c_bltp.write(f"{row['buy_price']:.2f}")
    c_sstrike.write(f"{row['sell_strike']}")
    c_sltp.write(f"{row['sell_price']:.2f}")
    
    badge_cls = "badge-debit" if row["type"] == "debit" else "badge-credit"
    c_spread.markdown(f"<span class='{badge_cls}'>{row['spread']}</span>", unsafe_allow_html=True)
    
    c_rdate.write(row["result_date"])
    st.markdown("<hr style='margin: 0.3rem 0;'>", unsafe_allow_html=True)

# ----------------- AUTO-SCAN REFRESH TRIGGER -----------------
if st.session_state.auto_mode:
    time.sleep(5)
    st.rerun()
