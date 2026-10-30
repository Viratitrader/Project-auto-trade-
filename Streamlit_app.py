import os
import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(
    page_title="Project A Pro",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Streamlit native reset
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
    html, body {
        background-color: #ffffff;
        color: #0f172a;
        padding: 6px;
        width: 100%;
        overflow-x: hidden;
    }

    /* Top Bar */
    .header-bar {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 6px;
    }
    .brand-title {
        font-size: 1.10rem;
        font-weight: 800;
        color: #0f172a;
        display: flex;
        align-items: center;
        gap: 4px;
    }
    .brand-sub { font-size: 0.70rem; color: #64748b; margin-top: 1px; }
    .status-text {
        font-size: 0.68rem;
        color: #334155;
        display: flex;
        align-items: center;
        gap: 4px;
        white-space: nowrap;
    }
    .status-dot {
        width: 7px;
        height: 7px;
        background-color: #22c55e;
        border-radius: 50%;
        display: inline-block;
    }

    /* Row 1 - Filters */
    .filter-grid {
        display: grid;
        grid-template-columns: 1.15fr 0.85fr 1fr 1.1fr 0.9fr;
        gap: 4px;
        margin-bottom: 6px;
    }
    .field-wrap { display: flex; flex-direction: column; }
    .field-title { font-size: 0.68rem; font-weight: 600; color: #1e293b; margin-bottom: 2px; }
    .custom-select, .custom-input {
        width: 100%;
        height: 28px;
        border: 1px solid #cbd5e1;
        border-radius: 4px;
        padding: 0 2px;
        font-size: 0.70rem;
        background-color: #f8fafc;
        outline: none;
    }
    .custom-input {
        background-color: #ffffff;
        text-align: center;
        font-weight: 500;
    }
    .result-sub { font-size: 0.62rem; color: #64748b; text-align: center; margin-top: 1px; }

    /* Row 2 - Spread Cost */
    .cost-title { font-size: 0.70rem; font-weight: 700; color: #0f172a; margin-bottom: 3px; }
    .spread-row {
        display: flex;
        gap: 6px;
        margin-bottom: 8px;
    }
    .cost-box {
        flex: 1;
        display: flex;
        align-items: center;
        border: 1px solid #cbd5e1;
        border-radius: 5px;
        height: 30px;
        overflow: hidden;
        background: #ffffff;
    }
    .badge-debit {
        background-color: #0284c7;
        color: white;
        font-weight: 700;
        font-size: 0.72rem;
        padding: 0 8px;
        height: 100%;
        display: flex;
        align-items: center;
    }
    .badge-credit {
        background-color: #ef4444;
        color: white;
        font-weight: 700;
        font-size: 0.72rem;
        padding: 0 8px;
        height: 100%;
        display: flex;
        align-items: center;
    }
    .cost-input-field {
        border: none;
        outline: none;
        font-size: 0.72rem;
        padding: 0 6px;
        width: 100%;
        background: transparent;
    }

    /* 3 Scanner Modules */
    .modules-container {
        display: grid;
        grid-template-columns: 1fr 1fr 1fr;
        gap: 5px;
        margin-bottom: 8px;
    }
    .module-card {
        border-radius: 5px;
        padding: 5px;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
    }
    .mod-debit { background-color: #f0fdf4; border: 1px solid #bbf7d0; }
    .mod-gap { background-color: #fff1f2; border: 1px solid #fecdd3; }
    .mod-spike { background-color: #fefce8; border: 1px solid #fef08a; }

    .module-heading {
        font-size: 0.68rem;
        font-weight: 700;
        color: #0f172a;
        margin-bottom: 4px;
        line-height: 1.1;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }
    .btn-row { display: flex; align-items: center; gap: 2px; }
    
    .btn-opt {
        flex: 1;
        height: 22px;
        border: 1px solid #cbd5e1;
        background: #ffffff;
        border-radius: 3px;
        font-size: 0.65rem;
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
        width: 25px;
        height: 22px;
        border: 1px solid #cbd5e1;
        border-radius: 3px;
        text-align: center;
        font-size: 0.66rem;
        background: #ffffff;
        outline: none;
        padding: 0;
    }
    .unit-symbol { font-size: 0.65rem; font-weight: bold; }

    /* Results Header */
    .results-head {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin: 4px 0 5px 0;
    }
    .results-left {
        display: flex;
        align-items: center;
        gap: 3px;
        font-size: 0.78rem;
        font-weight: 700;
    }
    .results-right {
        display: flex;
        align-items: center;
        gap: 4px;
    }
    .total-counter { font-size: 0.66rem; color: #334155; }
    .table-search {
        height: 22px;
        width: 75px;
        border: 1px solid #cbd5e1;
        border-radius: 3px;
        font-size: 0.65rem;
        padding: 0 3px;
        outline: none;
    }

    /* Fixed Screen Table (NO A/B/C, NO 1/2/3, 100% Fit) */
    .excel-container {
        width: 100%;
        overflow: hidden;
        border: 1px solid #94a3b8;
        background: #ffffff;
        border-radius: 4px;
    }
    .excel-grid {
        width: 100%;
        border-collapse: collapse;
        font-size: 0.62rem;
        table-layout: fixed;
    }
    .excel-grid th, .excel-grid td {
        border: 1px solid #cbd5e1;
        padding: 3px 2px;
        text-align: center;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
    }
    .excel-grid td {
        height: 28px;
    }
    .col-title th {
        background-color: #e2e8f0;
        color: #0f172a;
        font-weight: 700;
        font-size: 0.60rem;
        line-height: 1.1;
    }
    
    /* Column Widths (9 Main Columns Totaling 100%) */
    .c-comp { width: 24%; text-align: left !important; padding-left: 4px !important; }
    .c-col  { width: 9.5%; }

    .comp-cell {
        line-height: 1.15;
    }
    .comp-name { font-weight: 700; color: #0f172a; font-size: 0.64rem; }
    .comp-date { font-size: 0.54rem; color: #0284c7; font-weight: 600; display: block; }
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
            <span class="status-dot"></span> <b>Live Scan</b> &nbsp; <code>06 Oct 2026</code> 🔄
        </div>
    </div>

    <!-- Filters Row 1 -->
    <div class="filter-grid">
        <div class="field-wrap">
            <span class="field-title">Delta</span>
            <input type="text" class="custom-input" placeholder="0.10 - 0.25" value="0.10 - 0.25">
        </div>
        <div class="field-wrap">
            <span class="field-title">Ratio</span>
            <select class="custom-select">
                <option value="1:3">1:3</option>
                <option value="3:10">3:10</option>
                <option value="1:4">1:4</option>
                <option value="2:7">2:7</option>
            </select>
        </div>
        <div class="field-wrap">
            <span class="field-title">Option Type</span>
            <select class="custom-select">
                <option value="CE">CE (Call)</option>
                <option value="PE">PE (Put)</option>
            </select>
        </div>
        <div class="field-wrap">
            <span class="field-title">Expiry</span>
            <select class="custom-select">
                <option>26 Sep</option>
                <option>06 Oct</option>
                <option>29 Oct</option>
            </select>
        </div>
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
            <input type="text" class="cost-input-field" value="0 - 5000" inputmode="numeric">
        </div>
        <div class="cost-box">
            <div class="badge-credit">Credit</div>
            <input type="text" class="cost-input-field" value="0 - 5000" inputmode="numeric">
        </div>
    </div>

    <!-- 3 Scanner Modules -->
    <div class="modules-container">
        <div class="module-card mod-debit">
            <div class="module-heading">1. Debit ₹0</div>
            <div class="btn-row">
                <button class="btn-opt">Auto</button>
                <button class="btn-opt">Man</button>
                <button class="btn-opt btn-scan">Scan</button>
            </div>
        </div>

        <div class="module-card mod-gap">
            <div class="module-heading">2. % Gap</div>
            <div class="btn-row">
                <input type="number" class="num-box" value="20" inputmode="numeric">
                <span class="unit-symbol">%</span>
                <button class="btn-opt">Auto</button>
                <button class="btn-opt btn-scan">Scan</button>
            </div>
        </div>

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

    <!-- Direct Clean Data Table -->
    <div class="excel-container">
        <table class="excel-grid">
            <thead>
                <tr class="col-title">
                    <th class="c-comp">Company (Date)</th>
                    <th class="c-col">Strk B/S</th>
                    <th class="c-col">P/P</th>
                    <th class="c-col">R1 B/S</th>
                    <th class="c-col">R1 P/P</th>
                    <th class="c-col">R1 Pft</th>
                    <th class="c-col">R2 B/S</th>
                    <th class="c-col">R2 P/P</th>
                    <th class="c-col">R2 Pft</th>
                </tr>
            </thead>
            <tbody>
"""

sample_stocks = [
    ("RELIANCE", "Δ 0.22", "06 Oct"),
    ("TCS", "Δ 0.21", "06 Oct"),
    ("INFY", "Δ 0.23", "08 Oct"),
    ("HDFCBANK", "Δ 0.24", "12 Oct"),
    ("ICICIBANK", "Δ 0.21", "14 Oct"),
]

for i in range(1, 14):
    if i <= len(sample_stocks):
        comp, delta, rdate = sample_stocks[i - 1]
        comp_display = f"<div class='comp-name'>{comp}</div><span class='comp-date'>📅 {rdate} ({delta})</span>"
    else:
        comp_display = ""

    mobile_ui_html += f"""
                <tr>
                    <td class="c-comp comp-cell">{comp_display}</td>
                    <td class="c-col"></td>
                    <td class="c-col"></td>
                    <td class="c-col"></td>
                    <td class="c-col"></td>
                    <td class="c-col"></td>
                    <td class="c-col"></td>
                    <td class="c-col"></td>
                    <td class="c-col"></td>
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
