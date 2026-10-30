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
        align-items: flex-start;
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
        grid-template-columns: 1.1fr 0.85fr 1fr 1.15fr 0.9fr;
        gap: 5px;
        margin-bottom: 6px;
    }
    .field-wrap { display: flex; flex-direction: column; }
    .field-title { font-size: 0.72rem; font-weight: 600; color: #1e293b; margin-bottom: 3px; }
    .custom-select, .custom-input {
        width: 100%;
        height: 28px;
        border: 1px solid #cbd5e1;
        border-radius: 4px;
        padding: 0 4px;
        font-size: 0.72rem;
        background-color: #f8fafc;
        outline: none;
    }
    .result-sub { font-size: 0.65rem; color: #64748b; text-align: center; margin-top: 1px; }

    /* Spread Cost (Row 2) */
    .cost-title { font-size: 0.72rem; font-weight: 700; color: #0f172a; margin-bottom: 3px; }
    .spread-row {
        display: flex;
        gap: 10px;
        margin-bottom: 8px;
    }
    .cost-pill {
        display: flex;
        align-items: center;
        border: 1px solid #cbd5e1;
        border-radius: 4px;
        height: 26px;
        overflow: hidden;
    }
    .pill-debit {
        background-color: #0284c7;
        color: white;
        font-weight: 700;
        font-size: 0.72rem;
        padding: 0 8px;
        height: 100%;
        display: flex;
        align-items: center;
    }
    .pill-credit {
        background-color: #ef4444;
        color: white;
        font-weight: 700;
        font-size: 0.72rem;
        padding: 0 8px;
        height: 100%;
        display: flex;
        align-items: center;
    }
    .cost-input {
        border: none;
        outline: none;
        font-size: 0.72rem;
        padding: 0 6px;
        width: 72px;
        background: transparent;
    }

    /* 3 Scanner Modules */
    .module-card {
        border-radius: 5px;
        padding: 6px 8px;
        margin-bottom: 6px;
    }
    .mod-debit { background-color: #f0fdf4; border: 1px solid #bbf7d0; }
    .mod-gap { background-color: #fff1f2; border: 1px solid #fecdd3; }
    .mod-spike { background-color: #fefce8; border: 1px solid #fef08a; }

    .module-heading { font-size: 0.78rem; font-weight: 700; color: #0f172a; margin-bottom: 5px; }
    .btn-row { display: flex; align-items: center; gap: 4px; }
    
    .btn-opt {
        flex: 1;
        height: 26px;
        border: 1px solid #cbd5e1;
        background: #ffffff;
        border-radius: 4px;
        font-size: 0.72rem;
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
        width: 32px;
        height: 26px;
        border: 1px solid #cbd5e1;
        border-radius: 4px;
        text-align: center;
        font-size: 0.72rem;
        background: #ffffff;
        outline: none;
    }
    .unit-symbol { font-size: 0.72rem; font-weight: bold; margin-right: 2px; }

    /* Results Header Bar */
    .results-head {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin: 8px 0 6px 0;
    }
    .results-left {
        display: flex;
        align-items: center;
        gap: 4px;
        font-size: 0.85rem;
        font-weight: 700;
    }
    .results-right {
        display: flex;
        align-items: center;
        gap: 6px;
    }
    .total-counter { font-size: 0.72rem; color: #334155; }
    .table-search {
        height: 24px;
        width: 90px;
        border: 1px solid #cbd5e1;
        border-radius: 4px;
        font-size: 0.70rem;
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
        min-width: 860px;
    }
    .excel-grid th {
        border: 1px solid #cbd5e1;
        padding: 4px 6px;
        text-align: center;
    }
    .excel-grid td {
        border: 1px solid #e2e8f0;
        height: 22px;
        padding: 2px 4px;
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
    .row-index {
        background-color: #f1f5f9;
        font-weight: 700;
        color: #64748b;
        width: 26px;
    }
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
        <div class="field-wrap">
            <span class="field-title">Delta</span>
            <select class="custom-select"><option>0.20 - 0.25</option><option>0.15 - 0.20</option></select>
        </div>
        <div class="field-wrap">
            <span class="field-title">Ratio</span>
            <select class="custom-select"><option>1 : 3</option><option>1 : 2</option></select>
        </div>
        <div class="field-wrap">
            <span class="field-title">Option Type</span>
            <select class="custom-select"><option>CE (Call)</option><option>PE (Put)</option></select>
        </div>
        <div class="field-wrap">
            <span class="field-title">Expiry</span>
            <select class="custom-select"><option>26 Sep 2026</option><option>06 Oct 2026</option></select>
        </div>
        <div class="field-wrap">
            <span class="field-title">Result</span>
            <input type="text" class="custom-input" value="0" style="text-align:center;">
            <span class="result-sub">Figures</span>
        </div>
    </div>

    <!-- Spread Cost Row 2 -->
    <div class="cost-title">Spread Cost (₹)</div>
    <div class="spread-row">
        <div class="cost-pill">
            <div class="pill-debit">Debit</div>
            <input type="text" class="cost-input" value="0 - 5000">
        </div>
        <div class="cost-pill">
            <div class="pill-credit">Credit</div>
            <input type="text" class="cost-input" value="0 - 5000">
        </div>
    </div>

    <!-- 1. Debit ₹0 Scanner -->
    <div class="module-card mod-debit">
        <div class="module-heading">1. Debit ₹0 Scanner</div>
        <div class="btn-row">
            <button class="btn-opt">Auto</button>
            <button class="btn-opt">Manual</button>
            <button class="btn-opt btn-scan">Scan</button>
        </div>
    </div>

    <!-- 2. % Gap Scanner -->
    <div class="module-card mod-gap">
        <div class="module-heading">2. % Gap Scanner</div>
        <div class="btn-row">
            <input type="text" class="num-box" value="20">
            <span class="unit-symbol">%</span>
            <button class="btn-opt">Auto</button>
            <button class="btn-opt">Manual</button>
            <button class="btn-opt btn-scan">Scan</button>
        </div>
    </div>

    <!-- 3. Option Premium Spike (UP / DOWN) -->
    <div class="module-card mod-spike">
        <div class="module-heading">3. Option Premium Spike (UP / DOWN)</div>
        <div class="btn-row">
            <input type="text" class="num-box" value="10">
            <span class="unit-symbol">%</span>
            <button class="btn-opt">Auto</button>
            <button class="btn-opt">Manual</button>
            <button class="btn-opt btn-scan">Scan</button>
        </div>
    </div>

    <!-- Results Header -->
    <div class="results-head">
        <div class="results-left">🎯 Scan Results (Live)</div>
        <div class="results-right">
            <span class="total-counter">Total Results: <b>24</b></span>
            <input type="text" class="table-search" placeholder="🔍 Search...">
        </div>
    </div>

    <!-- Excel Table -->
    <div class="excel-scroll">
        <table class="excel-grid">
            <thead>
                <tr class="col-letter">
                    <th class="row-index"></th>
                    <th>A</th><th>B</th><th>C</th><th>D</th><th>E</th><th>F</th><th>G</th><th>H</th><th>I</th><th>J</th><th>K</th>
                </tr>
                <tr class="col-title">
                    <th class="row-index">#</th>
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

# Generate 14 Excel rows
for i in range(1, 15):
    mobile_ui_html += f"""
                <tr>
                    <td class="row-index">{i}</td>
                    <td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td>
                </tr>
    """

mobile_ui_html += """
            </tbody>
        </table>
    </div>

</body>
</html>
"""

components.html(mobile_ui_html, height=760, scrolling=False)
