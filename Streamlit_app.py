import os
import time
import datetime
import streamlit as st

st.set_page_config(
    page_title="Project A Pro - Options Ratio Spread Scanner",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
    .block-container {
        padding-top: 0.8rem !important;
        padding-bottom: 2rem !important;
        padding-left: 0.8rem !important;
        padding-right: 0.8rem !important;
        max-width: 100% !important;
    }
    
    .top-bar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
    .logo-title { font-size: 1.35rem; font-weight: 800; color: #0f172a; margin: 0; line-height: 1.2; }
    .sub-title { font-size: 0.8rem; color: #64748b; margin: 0; }
    
    .filter-label { font-size: 0.8rem; font-weight: 600; color: #0f172a; margin-bottom: 4px; }
    .sub-caption { font-size: 0.72rem; color: #64748b; margin-top: 2px; }
    
    .cost-badge-debit {
        background-color: #0284c7;
        color: white;
        font-weight: 600;
        font-size: 0.8rem;
        padding: 5px 12px;
        border-radius: 4px 0 0 4px;
        display: inline-flex;
        align-items: center;
    }
    .cost-badge-credit {
        background-color: #ef4444;
        color: white;
        font-weight: 600;
        font-size: 0.8rem;
        padding: 5px 12px;
        border-radius: 4px 0 0 4px;
        display: inline-flex;
        align-items: center;
    }
    
    .card-mod-1 {
        background: #f0fdf4;
        border: 1px solid #bbf7d0;
        border-radius: 6px;
        padding: 8px 10px;
        margin-bottom: 10px;
    }
    .card-mod-2 {
        background: #fff1f2;
        border: 1px solid #fecdd3;
        border-radius: 6px;
        padding: 8px 10px;
        margin-bottom: 10px;
    }
    .card-mod-3 {
        background: #fefce8;
        border: 1px solid #fef08a;
        border-radius: 6px;
        padding: 8px 10px;
        margin-bottom: 10px;
    }
    .mod-title { font-size: 0.88rem; font-weight: 700; color: #0f172a; margin-bottom: 6px; }

    .excel-container {
        width: 100%;
        overflow-x: auto;
        -webkit-overflow-scrolling: touch;
        border: 1px solid #cbd5e1;
        margin-top: 6px;
    }
    .excel-table {
        width: 100%;
        border-collapse: collapse;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        font-size: 0.78rem;
        min-width: 880px;
    }
    .excel-table th {
        background-color: #e2e8f0;
        color: #334155;
        font-weight: 600;
        border: 1px solid #cbd5e1;
        padding: 5px 4px;
        text-align: center;
    }
    .col-letter-header {
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
h1, h2 = st.columns([3, 1.8])
with h1:
    st.markdown("""
        <div class="logo-title">📊 Project A Pro</div>
        <div class="sub-title">Options Ratio Spread Scanner</div>
    """, unsafe_allow_html=True)
with h2:
    status_icon = "🟢" if st.session_state.auto_scan else "⚪"
    status_name = "Live Scan" if st.session_state.auto_scan else "Manual Mode"
    st.markdown(f"<div style='text-align:right; font-size:0.82rem;'>{status_icon} <b>{status_name}</b> &nbsp; <code>06 Oct 2026 12:30:15</code> 🔄</div>", unsafe_allow_html=True)

st.write("")

# ----------------- TOP FILTERS (ROW 1) -----------------
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
    st.markdown("<div class='sub-caption' style='text-align:center;'>Figures</div>", unsafe_allow_html=True)

# ----------------- SPREAD COST (ROW 2) -----------------
st.markdown("<div class='filter-label'>Spread Cost (₹)</div>", unsafe_allow_html=True)
sc1, sc2, empty_space = st.columns([1.5, 1.5, 3])
with sc1:
    debit_col1, debit_col2 = st.columns([1, 2])
    with debit_col1:
        st.markdown("<div class='cost-badge-debit'>Debit</div>", unsafe_allow_html=True)
    with debit_col2:
        st.text_input("DebitVal", value="0 - 5000", label_visibility="collapsed")
with sc2:
    credit_col1, credit_col2 = st.columns([1, 2])
    with credit_col1:
        st.markdown("<div class='cost-badge-credit'>Credit</div>", unsafe_allow_html=True)
    with credit_col2:
        st.text_input("CreditVal", value="0 - 5000", label_visibility="collapsed")

st.write("")

# ----------------- 3 MODULES -----------------
st.markdown("<div class='card-mod-1'><div class='mod-title'>1. Debit ₹0 Scanner</div>", unsafe_allow_html=True)
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

st.markdown("<div class='card-mod-2'><div class='mod-title'>2. % Gap Scanner</div>", unsafe_allow_html=True)
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

st.markdown("<div class='card-mod-3'><div class='mod-title'>3. Option Premium Spike (UP / DOWN)</div>", unsafe_allow_html=True)
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

# ----------------- SCAN RESULTS (EXCEL SHEET STYLE) -----------------
r1, r2, r3 = st.columns([2, 1.2, 1.3])
with r1:
    st.markdown("<h4 style='margin:0;'>🎯 Scan Results (Live)</h4>", unsafe_allow_html=True)
with r2:
    st.markdown("<p style='text-align:right; font-size:0.85rem; margin:4px 0 0 0;'>Total Results: <b>24</b></p>", unsafe_allow_html=True)
with r3:
    st.text_input("Search", placeholder="🔍 Search...", label_visibility="collapsed")

# Excel Grid Table
excel_html = """
<div class="excel-container">
<table class="excel-table">
    <thead>
        <tr class="col-letter-header">
            <th class="row-num"></th>
            <th>A</th>
            <th>B</th>
            <th>C</th>
            <th>D</th>
            <th>E</th>
            <th>F</th>
            <th>G</th>
            <th>H</th>
            <th>I</th>
            <th>J</th>
            <th>K</th>
        </tr>
        <tr>
            <th class="row-num">#</th>
            <th>#</th>
            <th>Company - delta value</th>
            <th>strike buy/sale</th>
            <th>price/ price</th>
            <th>R1 buystrike / sale</th>
            <th>R1 (price/ price)</th>
            <th>R1 (profit)</th>
            <th>R2 buystrike / sale</th>
            <th>R2 (price/ price)</th>
            <th>R2 (profit)</th>
            <th>Resu date</th>
        </tr>
    </thead>
    <tbody>
"""

for row_idx in range(1, 15):
    excel_html += f"""
        <tr>
            <td class="row-num">{row_idx}</td>
            <td></td>
            <td></td>
            <td></td>
            <td></td>
            <td></td>
            <td></td>
            <td></td>
            <td></td>
            <td></td>
            <td></td>
            <td></td>
        </tr>
    """

excel_html += """
    </tbody>
</table>
</div>
"""

st.markdown(excel_html, unsafe_allow_html=True)

if st.session_state.auto_scan:
    time.sleep(5)
    st.rerun()
