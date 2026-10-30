import os
import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(
    page_title="Project A Pro",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Safe secrets / environment token handling
try:
    secret_token = st.secrets.get("UPSTOX_ACCESS_TOKEN", "")
except Exception:
    secret_token = os.environ.get("UPSTOX_ACCESS_TOKEN", "")

# Streamlit native padding zero
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

mobile_ui_html = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
<style>
    * { box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
    body { background-color: #ffffff; color: #0f172a; padding: 8px 10px; overflow-x: hidden; }

    /* Top Brand Bar */
    .header-bar {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 8px;
    }
    .brand-title {
        font-size: 1.15rem;
        font-weight: 800;
        color: #0f172a;
        display: flex;
        align-items: center;
        gap: 4px;
    }
    .brand-sub { font-size: 0.72rem; color: #64748b; margin-top: 1px; }
    .status-text {
        font-size: 0.70rem;
        color: #334155;
        display: flex;
        align-items: center;
        gap: 4px;
        white-space: nowrap;
    }
    .status-dot {
        width: 8px;
        height: 8px;
        background-color: #22c55e;
        border-radius: 50%;
        display: inline-block;
    }

    /* Filters Grid (Row 1) */
    .filter-grid {
        display: grid;
        grid-template-columns: 1.15fr 0.85fr 1fr 1.1fr 0.9fr;
        gap: 5px;
        margin-bottom: 8px;
    }
    .field-wrap { display: flex; flex-direction: column; }
    .field-title { font-size: 0.72rem; font-weight: 600; color: #1e293b; margin-bottom: 3px; }
    .custom-select, .custom-input {
        width: 100%;
        height: 30px;
        border: 1px solid #cbd5e1;
        border-radius: 4px;
        padding: 0 4px;
        font-size: 0.73rem;
        background-color: #f8fafc;
        outline: none;
    }
    .custom-input {
        background-color: #ffffff;
        text-align: center;
        font-weight: 500;
    }
    .result-sub { font-size: 0.65rem; color: #64748b; text-align: center; margin-top: 1px; }

    /* Spread Cost (Row 2) */
    .cost-title { font-size: 0.74rem; font-weight: 700; color: #0f172a; margin-bottom: 4px; }
    .spread-row {
        display: flex;
        gap: 8px;
        margin-bottom: 10px;
    }
    .cost-box {
        flex: 1;
        display: flex;
        align-items: center;
        border: 1px solid #cbd5e1;
        border-radius: 6px;
        height: 32px;
        overflow: hidden;
        background: #ffffff;
    }
    .badge-debit {
        background-color: #0284c7;
        color: white;
        font-weight: 700;
        font-size: 0.75rem;
        padding: 0 10px;
        height: 100%;
        display: flex;
        align-items: center;
    }
    .badge-credit {
        background-color: #ef4444;
        color: white;
        font-weight: 700;
        font-size: 0.75rem;
        padding: 0 10px;
        height: 100%;
        display: flex;
        align-items: center;
    }
    .cost-input-field {
        border: none;
        outline: none;
        font-size: 0.76rem;
        padding: 0 8px;
        width: 100%;
        background: transparent;
    }

    /* 3 Scanner Modules Side-by-Side */
    .modules-container {
        display: grid;
        grid-template-columns: 1fr 1fr 1fr;
        gap: 6px;
        margin-bottom: 10px;
    }
    .module-card {
        border-radius: 6px;
        padding: 6px;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
    }
    .mod-debit { background-color: #f0fdf4; border: 1px solid #bbf7d0; }
    .mod-gap { background-color: #fff1f2; border: 1px solid #fecdd3; }
    .mod-spike { background-color: #fefce8; border: 1px solid #fef08a; }

    .module-heading {
        font-size: 0.72rem;
        font-weight: 700;
        color: #0f172a;
        margin-bottom: 6px;
        line-height: 1.1;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }
    .btn-row { display: flex; align-items: center; gap: 3px; }
    
    .btn-opt {
        flex: 1;
        height: 24px;
        border: 1px solid #cbd5e1;
        background: #ffffff;
        border-radius: 4px;
        font-size: 0.68rem;
        font-weight: 600;
        color: #0f172a;
        display: flex;
        align-items: center;
        justify-content: center;
        cursor: pointer;
    }
    .btn-scan {
        background-color: #10b981;
        border-color: #10b981;
        color: #ffffff;
    }
    .num-box {
        width: 28px;
        height: 24px;
        border: 1px solid #cbd5e1;
        border-radius: 4px;
        text-align: center;
        font-size: 0.70rem;
        background: #ffffff;
        outline: none;
        padding: 0;
    }
    .unit-symbol { font-size: 0.68rem; font-weight: bold; }

    /* Results Header Bar */
    .results-head {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin: 6px 0 6px 0;
    }
    .results-left {
        display: flex;
        align-items: center;
        gap: 4px;
        font-size: 0.82rem;
        font-weight: 700;
    }
    .results-right {
        display: flex;
        align-items: center;
        gap: 6px;
    }
    .total-counter { font-size: 0.70rem; color: #334155; }
    .table-search {
        height: 24px;
        width: 85px;
        border: 1px solid #cbd5e1;
        border-radius: 4px;
        font-size: 0.68rem;
        padding: 0 4px;
        outline: none;
    }

    /* Excel Scroll Container */
    .excel-scroll {
        width: 100%;
        overflow-x: auto;
        -webkit-overflow-scrolling: touch;
        border: 1px solid #cbd5e1;
        background: #ffffff;
    }
    .excel-grid {
        border-collapse: collapse;
        font-size: 0.70rem;
        white-space: nowrap;
        min-width: 780px;
        table-layout: fixed;
    }
    .excel-grid th {
        border: 1px solid #cbd5e1;
        padding: 4px 6px;
        text-align: center;
    }
    .excel-grid td {
        border: 1px solid #e2e8f0;
        height: 28px;
        padding: 2px 6px;
        text-align: center;
    }
    .col-letter th {
        background-color: #cbd5e1;
        color: #475569;
        font-weight: bold;
        font-size: 0.68rem;
    }
    .col-title th {
        background-color: #e2e8f0;
        color: #1e293b;
        font-weight: 600;
    }
    
    /* Fixed Column Widths for Consistent Layout */
    .col-a { width: 34px; }
    .col-b { width: 140px; text-align: left !important; }
    .col-c { width: 95px; }
    .col-d { width: 85px; }
    .col-e { width: 95px; }
    .col-f { width: 85px; }
    .col-g { width: 80px; }
    .col-h { width: 95px; }
    .col-i { width: 85px; }
    .col-j { width: 80px; }

    .row-index {
        background-color: #f1f5f9;
        font-weight: 700;
        color: #64748b;
    }
    .comp-cell {
        text-align: left !important;
        line-height: 1.15;
    }
    .comp-name { font-weight: 700; color: #0f172a; }
    .comp-date { font-size: 0.64rem; color: #0284c7; font-weight: 600; display: block; }
</style>
</head>
<body>

    <!-- Header -->
    <div class="header-bar">
        <div>
            <div class="brand-title">📊 Project A Pro</div>
            <div class="brand-sub">Options Ratio Spread Scanner</div>
        </div>
        <div class="status-text">
            <span class="status-dot"></span> <b>Live Scan</b> &nbsp; <code>06 Oct 2026 12:30:15</code> 🔄
        </div>
    </div>

    <!-- Filters Row 1 -->
    <div class="filter-grid">
        <!-- Delta Open Range Box -->
        <div class="field-wrap">
            <span class="field-title">Delta</span>
            <input type="text" class="custom-input" placeholder="0.10 - 0.25" value="0.10 - 0.25">
        </div>
        <!-- Ratio Dropdown with Custom Specified Options -->
        <div class="field-wrap">
            <span class="field-title">Ratio</span>
            <select class="custom-select">
                <option value="1:3">1:3</option>
                <option value="3:10">3:10</option>
                <option value="1:4">1:4</option>
                <option value="2:7">2:7</option>
            </select>
        </div>
        <!-- Option Type Dropdown -->
        <div class="field-wrap">
            <span class="field-title">Option Type</span>
            <select class="custom-select">
                <option value="CE">CE (Call)</option>
                <option value="PE">PE (Put)</option>
            </select>
        </div>
        <!-- Expiry Dropdown -->
        <div class="field-wrap">
            <span class="field-title">Expiry</span>
            <select class="custom-select">
                <option>26 Sep 2026</option>
                <option>06 Oct 2026</option>
                <option>29 Oct 2026</option>
            </select>
        </div>
        <!-- Result Input Box -->
        <div class="field-wrap">
            <span class="field-title">Result</span>
            <input type="text" class="custom-input" value="0" inputmode="numeric">
            <span class="result-sub">Figures</span>
        </div>
    </div>

    <!-- Spread Cost Row 2 -->
    <div class="cost-title">Spread Cost (₹)</div>
    <div class="spread-row">
        <div class="cost-box">
            <div class="badge-debit">Debit</div>
            <input type="text" class="cost-input-field" value="0 - 5000" inputmode="numeric" placeholder="Enter debit...">
        </div>
        <div class="cost-box">
            <div class="badge-credit">Credit</div>
            <input type="text" class="cost-input-field" value="0 - 5000" inputmode="numeric" placeholder="Enter credit...">
        </div>
    </div>

    <!-- 3 Scanner Modules Side-by-Side -->
    <div class="modules-container">
        <!-- 1. Debit Module -->
        <div class="module-card mod-debit">
            <div class="module-heading">1. Debit ₹0</div>
            <div class="btn-row">
                <button class="btn-opt">Auto</button>
                <button class="btn-opt">Man</button>
                <button class="btn-opt btn-scan">Scan</button>
            </div>
        </div>

        <!-- 2. % Gap Module -->
        <div class="module-card mod-gap">
            <div class="module-heading">2. % Gap</div>
            <div class="btn-row">
                <input type="number" class="num-box" value="20" inputmode="numeric">
                <span class="unit-symbol">%</span>
                <button class="btn-opt">Auto</button>
                <button class="btn-opt btn-scan">Scan</button>
            </div>
        </div>

        <!-- 3. Spike Module -->
        <div class="module-card mod-spike">
            <div class="module-heading">3. Spike UP/DN</div>
            <div class="btn-row">
                <input type="number" class="num-box" value="10" inputmode="numeric">
                <span class="unit-symbol">%</span>
                <button class="btn-opt">Auto</button>
                <button class="btn-opt btn-scan">Scan</button>
            </div>
        </div>
    </div>

    <!-- Results Header -->
    <div class="results-head">
        <div class="results-left">🎯 Scan Results (Live)</div>
        <div class="results-right">
            <span class="total-counter">Total: <b>24</b></span>
            <input type="text" class="table-search" placeholder="🔍 Search...">
        </div>
    </div>

    <!-- Excel Table (Single # Column & Consistent Row Layout up to Column J) -->
    <div class="excel-scroll">
        <table class="excel-grid">
            <thead>
                <tr class="col-letter">
                    <th class="col-a">A</th>
                    <th class="col-b">B</th>
                    <th class="col-c">C</th>
                    <th class="col-d">D</th>
                    <th class="col-e">E</th>
                    <th class="col-f">F</th>
                    <th class="col-g">G</th>
                    <th class="col-h">H</th>
                    <th class="col-i">I</th>
                    <th class="col-j">J</th>
                </tr>
                <tr class="col-title">
                    <th class="col-a row-index">#</th>
                    <th class="col-b">Company (Result Date)</th>
                    <th class="col-c">strike buy/sale</th>
                    <th class="col-d">price/ price</th>
                    <th class="col-e">R1 buystrike / sale</th>
                    <th class="col-f">R1 (price/ price)</th>
                    <th class="col-g">R1 (profit)</th>
                    <th class="col-h">R2 buystrike / sale</th>
                    <th class="col-i">R2 (price/ price)</th>
                    <th class="col-j">R2 (profit)</th>
                </tr>
            </thead>
            <tbody>
"""

sample_stocks = [
    ("RELIANCE", "Δ 0.22", "06 Oct 2026"),
    ("TCS", "Δ 0.21", "06 Oct 2026"),
    ("INFY", "Δ 0.23", "08 Oct 2026"),
    ("HDFCBANK", "Δ 0.24", "12 Oct 2026"),
    ("ICICIBANK", "Δ 0.21", "14 Oct 2026"),
]

for i in range(1, 15):
    if i <= len(sample_stocks):
        comp, delta, rdate = sample_stocks[i - 1]
        comp_display = f"<div class='comp-name'>{comp} <small style='color:#64748b;'>({delta})</small></div><span class='comp-date'>📅 {rdate}</span>"
    else:
        comp_display = ""

    mobile_ui_html += f"""
                <tr>
                    <td class="col-a row-index">{i}</td>
                    <td class="col-b comp-cell">{comp_display}</td>
                    <td class="col-c"></td>
                    <td class="col-d"></td>
                    <td class="col-e"></td>
                    <td class="col-f"></td>
                    <td class="col-g"></td>
                    <td class="col-h"></td>
                    <td class="col-i"></td>
                    <td class="col-j"></td>
                </tr>
    """

mobile_ui_html += """
            </tbody>
        </table>
    </div>

</body>
</html>
"""

components.html(mobile_ui_html, height=750, scrolling=False)
