import os
import time
import datetime
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Project A Pro - Options Ratio Spread Scanner", layout="wide")

# CSS to exactly match the clean design
st.markdown("""
<style>
    .block-container { padding-top: 1rem; padding-bottom: 2rem; max-width: 98%; }
    
    /* Top Header Bar */
    .top-bar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
    .logo-title { font-size: 1.4rem; font-weight: 700; color: #0f172a; margin: 0; display: flex; align-items: center; gap: 8px; }
    .sub-title { font-size: 0.85rem; color: #64748b; margin: 0; }
    
    /* Modules Cards */
    .mod-card {
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 6px;
        padding: 8px 12px;
        margin-bottom: 12px;
    }
    .mod-label { font-size: 0.85rem; font-weight: 600; color: #1e293b; margin-bottom: 6px; }

    /* Custom Table Styling */
    .table-container { width: 100%; border-collapse: collapse; font-family: -apple-system, sans-serif; }
    .table-container th {
        background-color: #f1f5f9;
        color: #334155;
        font-weight: 600;
        font-size: 0.82rem;
        padding: 10px 8px;
        text-align: left;
        border-bottom: 1px solid #cbd5e1;
    }
    .main-row {
        background-color: #ffffff;
        border-bottom: 1px solid #f1f5f9;
        font-size: 0.85rem;
    }
    .main-row td { padding: 8px 8px; vertical-align: middle; }
    
    /* Result Stock Highlights */
    .stock-result { border-left: 4px solid #3b82f6; }
    .result-date-highlight { color: #0284c7; font-weight: 600; }
    
    /* Sub Rows (Review-1 / Review-2) */
    .sub-row {
        background-color: #fafafa;
        color: #64748b;
        font-size: 0.78rem;
        border-bottom: 1px solid #f1f5f9;
    }
    .sub-row td { padding: 4px 8px; }
    
    /* Badges */
    .badge-debit {
        background-color: #dcfce7;
        color: #166534;
        font-weight: 600;
        padding: 4px 10px;
        border-radius: 4px;
        display: inline-block;
        font-size: 0.8rem;
    }
    .badge-credit {
        background-color: #fee2e2;
        color: #991b1b;
        font-weight: 600;
        padding: 4px 10px;
        border-radius: 4px;
        display: inline-block;
        font-size: 0.8rem;
    }
</style>
""", unsafe_allow_html=True)

# ----------------- SESSION STATE -----------------
if "auto_scan" not in st.session_state:
    st.session_state.auto_scan = False

# ----------------- TOP HEADER -----------------
h1, h2 = st.columns([3, 1.5])
with h1:
    st.markdown("""
        <div class="logo-title">📊 Project A Pro</div>
        <div class="sub-title">Options Ratio Spread Scanner</div>
    """, unsafe_allow_html=True)
with h2:
    status_icon = "🟢" if st.session_state.auto_scan else "⚪"
    status_name = "Live Scan" if st.session_state.auto_scan else "Manual Mode"
    st.markdown(f"<div style='text-align:right;'>{status_icon} <b>{status_name}</b> &nbsp;&nbsp; <code>{datetime.datetime.now().strftime('%d %b %Y %H:%M:%S')}</code></div>", unsafe_allow_html=True)

st.write("")

# ----------------- FILTERS BAR -----------------
f1, f2, f3, f4, f5 = st.columns([1.1, 1, 1.1, 1.1, 2])
with f1:
    st.selectbox("Delta", ["0.20 - 0.25", "0.15 - 0.20", "0.25 - 0.30"], index=0)
with f2:
    st.selectbox("Ratio", ["1 : 3", "1 : 2"], index=0)
with f3:
    st.selectbox("Option Type", ["CE (Call)", "PE (Put)"], index=0)
with f4:
    st.selectbox("Expiry", ["26 Sep 2026", "06 Oct 2026", "29 Oct 2026"], index=0)
with f5:
    st.markdown("<small style='font-weight:600; color:#475569;'>Spread Cost (₹)</small>", unsafe_allow_html=True)
    sc1, sc2 = st.columns(2)
    with sc1:
        st.text_input("Debit", value="0 - 5000", label_visibility="collapsed")
    with sc2:
        st.text_input("Credit", value="0 - 5000", label_visibility="collapsed")

# ----------------- SCANNER TOOLBAR (3 MODULES) -----------------
m_col1, m_col2, m_col3 = st.columns(3)

with m_col1:
    st.markdown("<div class='mod-card'><div class='mod-label'>1. Debit ₹0 Scanner</div>", unsafe_allow_html=True)
    b1, b2, b3 = st.columns([1, 1, 1.2])
    with b1:
        if st.button("Auto", key="m1_auto", use_container_width=True):
            st.session_state.auto_scan = True
            st.rerun()
    with b2:
        if st.button("Manual", key="m1_man", use_container_width=True):
            st.session_state.auto_scan = False
            st.rerun()
    with b3:
        if st.button("Scan", key="m1_scan", type="primary", use_container_width=True):
            st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

with m_col2:
    st.markdown("<div class='mod-card'><div class='mod-label'>2. % Gap Scanner</div>", unsafe_allow_html=True)
    g1, g2, g3, g4 = st.columns([0.8, 1, 1, 1.2])
    with g1: st.number_input("Gap", value=20, label_visibility="collapsed")
    with g2:
        if st.button("Auto", key="m2_auto", use_container_width=True):
            st.session_state.auto_scan = True
            st.rerun()
    with g3:
        if st.button("Manual", key="m2_man", use_container_width=True):
            st.session_state.auto_scan = False
            st.rerun()
    with g4:
        if st.button("Scan", key="m2_scan", type="primary", use_container_width=True):
            st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

with m_col3:
    st.markdown("<div class='mod-card'><div class='mod-label'>3. Option Premium Spike (UP / DOWN)</div>", unsafe_allow_html=True)
    s1, s2, s3, s4 = st.columns([0.8, 1, 1, 1.2])
    with s1: st.number_input("Spike", value=10, label_visibility="collapsed")
    with s2:
        if st.button("Auto", key="m3_auto", use_container_width=True):
            st.session_state.auto_scan = True
            st.rerun()
    with s3:
        if st.button("Manual", key="m3_man", use_container_width=True):
            st.session_state.auto_scan = False
            st.rerun()
    with s4:
        if st.button("Scan", key="m3_scan", type="primary", use_container_width=True):
            st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

# ----------------- RESULTS TABLE BAR -----------------
r1, r2, r3 = st.columns([2, 1, 1.2])
with r1:
    st.markdown("#### 🎯 Scan Results (Live)")
with r2:
    st.markdown("<p style='text-align:right; font-size:0.9rem; margin-top:8px;'>Total Results: <b>24</b></p>", unsafe_allow_html=True)
with r3:
    search = st.text_input("Search", placeholder="🔍 Search company...", label_visibility="collapsed")

# Complete Dataset with Parent and Review Sub-rows
data = [
    {
        "id": 1, "company": "RELIANCE", "delta_lot": "Δ 0.22 | Lot 500", "has_result": True,
        "buy_strike": 840, "buy_price": 118.50, "sell_strike": 900, "sell_price": 39.20, "spread": "₹0 (Debit)", "type": "debit", "result_date": "06 Oct 2026",
        "reviews": [
            {"name": "Review-1", "buy_strike": 820, "buy_price": 112.40, "sell_strike": 980, "sell_price": 46.10, "spread": "₹40 (Credit)", "type": "credit"},
            {"name": "Review-2", "buy_strike": 860, "buy_price": 105.60, "sell_strike": 920, "sell_price": 31.20, "spread": "₹20 (Debit)", "type": "debit"}
        ]
    },
    {
        "id": 2, "company": "TCS", "delta_lot": "Δ 0.21 | Lot 500", "has_result": True,
        "buy_strike": 3200, "buy_price": 145.30, "sell_strike": 3300, "sell_price": 48.80, "spread": "₹120 (Credit)", "type": "credit", "result_date": "06 Oct 2026",
        "reviews": [
            {"name": "Review-1", "buy_strike": 3180, "buy_price": 152.60, "sell_strike": 3280, "sell_price": 52.10, "spread": "₹90 (Credit)", "type": "credit"},
            {"name": "Review-2", "buy_strike": 3220, "buy_price": 138.20, "sell_strike": 3320, "sell_price": 45.60, "spread": "₹10 (Debit)", "type": "debit"}
        ]
    },
    {
        "id": 3, "company": "INFY", "delta_lot": "Δ 0.23 | Lot 500", "has_result": False,
        "buy_strike": 1520, "buy_price": 62.40, "sell_strike": 1580, "sell_price": 19.50, "spread": "₹0 (Debit)", "type": "debit", "result_date": "06 Oct 2026",
        "reviews": [
            {"name": "Review-1", "buy_strike": 1500, "buy_price": 68.20, "sell_strike": 1560, "sell_price": 21.60, "spread": "₹40 (Credit)", "type": "credit"},
            {"name": "Review-2", "buy_strike": 1540, "buy_price": 58.20, "sell_strike": 1600, "sell_price": 17.40, "spread": "₹10 (Debit)", "type": "debit"}
        ]
    },
    {
        "id": 4, "company": "HDFCBANK", "delta_lot": "Δ 0.24 | Lot 500", "has_result": False,
        "buy_strike": 1640, "buy_price": 74.20, "sell_strike": 1700, "sell_price": 22.10, "spread": "₹50 (Credit)", "type": "credit", "result_date": "06 Oct 2026",
        "reviews": [
            {"name": "Review-1", "buy_strike": 1620, "buy_price": 78.50, "sell_strike": 1680, "sell_price": 24.80, "spread": "₹30 (Credit)", "type": "credit"},
            {"name": "Review-2", "buy_strike": 1660, "buy_price": 69.10, "sell_strike": 1720, "sell_price": 20.40, "spread": "₹20 (Debit)", "type": "debit"}
        ]
    },
    {
        "id": 5, "company": "ICICIBANK", "delta_lot": "Δ 0.21 | Lot 500", "has_result": True,
        "buy_strike": 1120, "buy_price": 48.90, "sell_strike": 1180, "sell_price": 15.60, "spread": "₹0 (Debit)", "type": "debit", "result_date": "06 Oct 2026",
        "reviews": [
            {"name": "Review-1", "buy_strike": 1100, "buy_price": 52.40, "sell_strike": 1160, "sell_price": 18.20, "spread": "₹30 (Credit)", "type": "credit"},
            {"name": "Review-2", "buy_strike": 1140, "buy_price": 45.10, "sell_strike": 1200, "sell_price": 13.40, "spread": "₹20 (Debit)", "type": "debit"}
        ]
    },
    {
        "id": 6, "company": "SBIN", "delta_lot": "Δ 0.20 | Lot 500", "has_result": False,
        "buy_strike": 360, "buy_price": 36.70, "sell_strike": 920, "sell_price": 11.40, "spread": "₹80 (Credit)", "type": "credit", "result_date": "06 Oct 2026",
        "reviews": [
            {"name": "Review-1", "buy_strike": 340, "buy_price": 40.20, "sell_strike": 900, "sell_price": 13.60, "spread": "₹50 (Credit)", "type": "credit"},
            {"name": "Review-2", "buy_strike": 380, "buy_price": 33.10, "sell_strike": 940, "sell_price": 9.80, "spread": "₹10 (Debit)", "type": "debit"}
        ]
    },
    {
        "id": 7, "company": "BHARTIARTL", "delta_lot": "Δ 0.22 | Lot 500", "has_result": False,
        "buy_strike": 880, "buy_price": 42.10, "sell_strike": 940, "sell_price": 12.30, "spread": "₹0 (Debit)", "type": "debit", "result_date": "06 Oct 2026",
        "reviews": [
            {"name": "Review-1", "buy_strike": 860, "buy_price": 46.20, "sell_strike": 920, "sell_price": 15.60, "spread": "₹40 (Credit)", "type": "credit"},
            {"name": "Review-2", "buy_strike": 900, "buy_price": 38.40, "sell_strike": 960, "sell_price": 10.80, "spread": "₹20 (Debit)", "type": "debit"}
        ]
    },
    {
        "id": 8, "company": "LT", "delta_lot": "Δ 0.21 | Lot 500", "has_result": True,
        "buy_strike": 3600, "buy_price": 158.20, "sell_strike": 3700, "sell_price": 52.60, "spread": "₹100 (Credit)", "type": "credit", "result_date": "06 Oct 2026",
        "reviews": [
            {"name": "Review-1", "buy_strike": 3580, "buy_price": 165.40, "sell_strike": 3680, "sell_price": 56.30, "spread": "₹70 (Credit)", "type": "credit"},
            {"name": "Review-2", "buy_strike": 3620, "buy_price": 150.10, "sell_strike": 3720, "sell_price": 48.10, "spread": "₹20 (Debit)", "type": "debit"}
        ]
    }
]

# Generate Clean HTML Table Structure
html_table = """
<div style="overflow-x: auto;">
<table class="table-container">
    <thead>
        <tr>
            <th style="width: 3%;">#</th>
            <th style="width: 25%;">Company (Delta | Lot)</th>
            <th style="width: 10%;">Buy Strike</th>
            <th style="width: 12%;">Buy Price (LTP)</th>
            <th style="width: 10%;">Sell Strike</th>
            <th style="width: 12%;">Sell Price (LTP)</th>
            <th style="width: 14%;">Debit / Credit</th>
            <th style="width: 14%;">Result Date</th>
        </tr>
    </thead>
    <tbody>
"""

for item in data:
    if search and search.upper() not in item["company"]:
        continue

    # Main Row with Left Accent Border for Result Stocks
    result_class = "stock-result" if item["has_result"] else ""
    badge_type = "badge-debit" if item["type"] == "debit" else "badge-credit"
    
    html_table += f"""
        <tr class="main-row {result_class}">
            <td><b>{item['id']}</b></td>
            <td><b>{item['company']}</b> <small style="color:#64748b;">({item['delta_lot']})</small></td>
            <td><b>{item['buy_strike']}</b></td>
            <td><b>{item['buy_price']:.2f}</b></td>
            <td><b>{item['sell_strike']}</b></td>
            <td><b>{item['sell_price']:.2f}</b></td>
            <td><span class="{badge_type}">{item['spread']}</span></td>
            <td><span class="{'result-date-highlight' if item['has_result'] else ''}">{item['result_date']}</span></td>
        </tr>
    """
    
    # Sub Rows for Review-1 and Review-2
    for rev in item["reviews"]:
        rev_badge = "badge-debit" if rev["type"] == "debit" else "badge-credit"
        html_table += f"""
            <tr class="sub-row {result_class}">
                <td></td>
                <td style="padding-left: 20px;">↳ {rev['name']}</td>
                <td>{rev['buy_strike']}</td>
                <td>{rev['buy_price']:.2f}</td>
                <td>{rev['sell_strike']}</td>
                <td>{rev['sell_price']:.2f}</td>
                <td><span class="{rev_badge}">{rev['spread']}</span></td>
                <td>{item['result_date']}</td>
            </tr>
        """

html_table += """
    </tbody>
</table>
</div>
"""

st.markdown(html_table, unsafe_allow_html=True)

# Auto Scan loop trigger
if st.session_state.auto_scan:
    time.sleep(5)
    st.rerun()
