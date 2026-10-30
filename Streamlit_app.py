import os
import time
import datetime
import streamlit as st

st.set_page_config(
    page_title="Project A Pro - Options Ratio Spread Scanner",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Safe secrets handling
try:
    secret_token = st.secrets.get("UPSTOX_ACCESS_TOKEN", "")
except Exception:
    secret_token = os.environ.get("UPSTOX_ACCESS_TOKEN", "")

# Pure CSS to prevent vertical collapsing on mobile & force horizontal layout
st.markdown("""
<style>
    /* Force main app wrapper to keep desktop width on mobile */
    .block-container {
        padding: 0.5rem !important;
        max-width: 100% !important;
    }
    
    /* Ensure columns do not break vertically on mobile */
    [data-testid="column"] {
        min-width: 0px !important;
        flex: 1 1 auto !important;
    }
    
    div[data-testid="stHorizontalBlock"] {
        display: flex !important;
        flex-direction: row !important;
        flex-wrap: nowrap !important;
        align-items: center !important;
        gap: 6px !important;
    }
    
    .logo-title { font-size: 1.35rem; font-weight: 800; color: #0f172a; margin: 0; line-height: 1.2; }
    .sub-title { font-size: 0.8rem; color: #64748b; margin: 0; }
    .sub-caption { font-size: 0.72rem; color: #64748b; text-align: center; margin-top: -2px; }

    /* Module cards styling */
    .module-box {
        border-radius: 6px;
        padding: 8px 10px;
        margin-bottom: 8px;
    }
    .mod-1 { background: #f0fdf4; border: 1px solid #bbf7d0; }
    .mod-2 { background: #fff1f2; border: 1px solid #fecdd3; }
    .mod-3 { background: #fefce8; border: 1px solid #fef08a; }
    .mod-title { font-size: 0.88rem; font-weight: 700; color: #0f172a; margin-bottom: 6px; }

    /* Excel Table Styling */
    .excel-container {
        width: 100%;
        overflow-x: auto;
        -webkit-overflow-scrolling: touch;
        border: 1px solid #cbd5e1;
        margin-top: 8px;
        background-color: #ffffff;
    }
    .excel-table {
        width: 100%;
        border-collapse: collapse;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        font-size: 0.75rem;
        min-width: 860px;
    }
    .excel-table th {
        background-color: #e2e8f0;
        color: #334155;
        font-weight: 600;
        border: 1px solid #cbd5e1;
        padding: 6px 4px;
        text-align: center;
        white-space: nowrap;
    }
    .col-header {
        background-color: #cbd5e1 !important;
        color: #475569 !important;
        font-weight: bold;
        font-size: 0.72rem;
    }
    .excel-table td {
        border: 1px solid #e2e8f0;
        padding: 6px 4px;
        text-align: center;
        background-color: #ffffff;
        height: 24px;
    }
    .row-num {
        background-color: #f1f5f9 !important;
        font-weight: 600;
        color: #64748b;
        width: 32px;
    }
</style>
""", unsafe_allow_html=True)

if "auto_scan" not in st.session_state:
    st.session_state.auto_scan = False

# ----------------- TOP HEADER -----------------
head_col1, head_col2 = st.columns([3, 1.8])
with head_col1:
    st.markdown("""
        <div class="logo-title">📊 Project A Pro</div>
        <div class="sub-title">Options Ratio Spread Scanner</div>
    """, unsafe_allow_html=True)
with head_col2:
    status_icon = "🟢" if st.session_state.auto_scan else "⚪"
    status_name = "Live Scan" if st.session_state.auto_scan else "Manual Mode"
    st.markdown(f"<div style='text-align:right; font-size:0.82rem;'>{status_icon} <b>{status_name}</b> &nbsp; <code>06 Oct 2026 12:30:15</code> 🔄</div>", unsafe_allow_html=True)

st.write("")

# ----------------- ROW 1: FILTERS -----------------
f1, f2, f3, f4, f5 = st.columns([1, 0.9, 1.1, 1.2, 0.9])
with f1:
    st.selectbox("Delta", ["0.20 - 0.25", "0.15 - 0.20"], index=0)
with f2:
    st.selectbox("Ratio", ["1 : 3", "1 : 2"], index=0)
with f3:
    st.selectbox("Option Type", ["CE (Call)", "PE (Put)"], index=0)
with f4:
    st.selectbox("Expiry", ["26 Sep 2026", "06 Oct 2026"], index=0)
with f5:
    st.text_input("Result", value="0")
    st.markdown("<div class='sub-caption'>Figures</div>", unsafe_allow_html=True)

# ----------------- ROW 2: SPREAD COST (₹) -----------------
st.markdown("<small style='font-weight:700; color:#0f172a;'>Spread Cost (₹)</small>", unsafe_allow_html=True)
c1, c2, c_empty = st.columns([1.5, 1.5, 3])
with c1:
    cd1, cd2 = st.columns([1, 2])
    with cd1:
        st.markdown("<div style='background:#0284c7; color:white; padding:6px; font-weight:bold; font-size:0.78rem; text-align:center; border-radius:4px;'>Debit</div>", unsafe_allow_html=True)
    with cd2:
        st.text_input("DebitVal", value="0 - 5000", label_visibility="collapsed")
with c2:
    cc1, cc2 = st.columns([1, 2])
    with cc1:
        st.markdown("<div style='background:#ef4444; color:white; padding:6px; font-weight:bold; font-size:0.78rem; text-align:center; border-radius:4px;'>Credit</div>", unsafe_allow_html=True)
    with cc2:
        st.text_input("CreditVal", value="0 - 5000", label_visibility="collapsed")

st.write("")

# ----------------- MODULES -----------------
# 1. Debit ₹0 Scanner
st.markdown("<div class='module-box mod-1'><div class='mod-title'>1. Debit ₹0 Scanner</div>", unsafe_allow_html=True)
m1_1, m1_2, m1_3 = st.columns(3)
with m1_1:
    if st.button("Auto", key="m1_auto", use_container_width=True):
        st.session_state.auto_scan = True
        st.rerun()
with m1_2:
    if st.button("Manual", key="m1_man", use_container_width=True):
        st.session_state.auto_scan = False
        st.rerun()
with m1_3:
    st.button("Scan", key="m1_scan", type="primary", use_container_width=True)
st.markdown("</div>", unsafe_allow_html=True)

# 2. % Gap Scanner
st.markdown("<div class='module-box mod-2'><div class='mod-title'>2. % Gap Scanner</div>", unsafe_allow_html=True)
m2_1, m2_2, m2_3, m2_4, m2_5 = st.columns([0.8, 0.4, 1.2, 1.2, 1.2])
with m2_1: st.text_input("gap_val", value="20", label_visibility="collapsed")
with m2_2: st.markdown("<div style='margin-top:6px; font-weight:bold;'>%</div>", unsafe_allow_html=True)
with m2_3:
    if st.button("Auto", key="m2_auto", use_container_width=True):
        st.session_state.auto_scan = True
        st.rerun()
with m2_4:
    if st.button("Manual", key="m2_man", use_container_width=True):
        st.session_state.auto_scan = False
        st.rerun()
with m2_5:
    st.button("Scan", key="m2_scan", type="primary", use_container_width=True)
st.markdown("</div>", unsafe_allow_html=True)

# 3. Option Premium Spike (UP / DOWN)
st.markdown("<div class='module-box mod-3'><div class='mod-title'>3. Option Premium Spike (UP / DOWN)</div>", unsafe_allow_html=True)
m3_1, m3_2, m3_3, m3_4, m3_5 = st.columns([0.8, 0.4, 1.2, 1.2, 1.2])
with m3_1: st.text_input("spike_val", value="10", label_visibility="collapsed")
with m3_2: st.markdown("<div style='margin-top:6px; font-weight:bold;'>%</div>", unsafe_allow_html=True)
with m3_3:
    if st.button("Auto", key="m3_auto", use_container_width=True):
        st.session_state.auto_scan = True
        st.rerun()
with m3_4:
    if st.button("Manual", key="m3_man", use_container_width=True):
        st.session_state.auto_scan = False
        st.rerun()
with m3_5:
    st.button("Scan", key="m3_scan", type="primary", use_container_width=True)
st.markdown("</div>", unsafe_allow_html=True)

# ----------------- SCAN RESULTS (TABLE) -----------------
r1, r2, r3 = st.columns([2, 1.2, 1.3])
with r1:
    st.markdown("<h4 style='margin:0;'>🎯 Scan Results (Live)</h4>", unsafe_allow_html=True)
with r2:
    st.markdown("<p style='text-align:right; font-size:0.85rem; margin:4px 0 0 0;'>Total Results: <b>24</b></p>", unsafe_allow_html=True)
with r3:
    st.text_input("Search", placeholder="🔍 Search...", label_visibility="collapsed")

# Excel table rows construction
table_rows = ""
for i in range(1, 15):
    table_rows += f"<tr><td class='row-num'>{i}</td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td></tr>"

full_table_html = f"""
<div class="excel-container">
<table class="excel-table">
<thead>
<tr class="col-header">
<th class="row-num"></th><th>A</th><th>B</th><th>C</th><th>D</th><th>E</th><th>F</th><th>G</th><th>H</th><th>I</th><th>J</th><th>K</th>
</tr>
<tr>
<th class="row-num">#</th><th>#</th><th>Company - delta value</th><th>strike buy/sale</th><th>price/ price</th><th>R1 buystrike / sale</th><th>R1 (price/ price)</th><th>R1 (profit)</th><th>R2 buystrike / sale</th><th>R2 (price/ price)</th><th>R2 (profit)</th><th>Resu date</th>
</tr>
</thead>
<tbody>
{table_rows}
</tbody>
</table>
</div>
"""

st.markdown(full_table_html, unsafe_allow_html=True)

if st.session_state.auto_scan:
    time.sleep(5)
    st.rerun()
