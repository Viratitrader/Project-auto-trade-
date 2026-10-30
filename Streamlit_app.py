import os
import time
import datetime
import streamlit as st
import streamlit.components.v1 as components

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

if "auto_scan" not in st.session_state:
    st.session_state.auto_scan = False

# Global Container Styling
st.markdown("""
<style>
    .block-container {
        padding: 0.5rem 0.5rem 2rem 0.5rem !important;
        max-width: 100% !important;
    }
    #MainMenu, header, footer { visibility: hidden; }
</style>
""", unsafe_allow_html=True)

# ----------------- EMBEDDED COMPLETE UI (DESKTOP + MOBILE LOCK) -----------------
app_html = """
<!DOCTYPE html>
<html>
<head>
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<style>
    * { box-sizing: border-box; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
    body { margin: 0; padding: 4px; background-color: #ffffff; color: #0f172a; }
    
    .scroll-wrapper {
        min-width: 820px;
        padding-bottom: 20px;
    }

    /* Top Bar */
    .top-bar {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 8px;
    }
    .brand-title { font-size: 1.35rem; font-weight: 800; color: #0f172a; margin: 0; }
    .brand-sub { font-size: 0.8rem; color: #64748b; margin: 0; }
    .status-badge { font-size: 0.8rem; color: #334155; display: flex; align-items: center; gap: 6px; }

    /* Filter Controls Row 1 */
    .filter-grid {
        display: grid;
        grid-template-columns: 1fr 0.9fr 1fr 1.1fr 0.9fr;
        gap: 8px;
        margin-bottom: 6px;
    }
    .field-box { display: flex; flex-direction: column; }
    .field-label { font-size: 0.76rem; font-weight: 600; color: #1e293b; margin-bottom: 3px; }
    .styled-select, .styled-input {
        height: 32px;
        border: 1px solid #cbd5e1;
        border-radius: 4px;
        padding: 2px 8px;
        font-size: 0.8rem;
        background: #f8fafc;
        outline: none;
    }
    .figures-text { font-size: 0.7rem; color: #64748b; text-align: center; margin-top: 2px; }

    /* Spread Cost Row 2 */
    .spread-row {
        display: flex;
        align-items: center;
        gap: 12px;
        margin-bottom: 10px;
    }
    .cost-group {
        display: flex;
        align-items: center;
        border: 1px solid #cbd5e1;
        border-radius: 4px;
        overflow: hidden;
        height: 30px;
    }
    .badge-debit {
        background-color: #0284c7;
        color: white;
        font-size: 0.78rem;
        font-weight: 700;
        padding: 0 10px;
        height: 100%;
        display: flex;
        align-items: center;
    }
    .badge-credit {
        background-color: #ef4444;
        color: white;
        font-size: 0.78rem;
        font-weight: 700;
        padding: 0 10px;
        height: 100%;
        display: flex;
        align-items: center;
    }
    .cost-val-input {
        border: none;
        padding: 0 8px;
        font-size: 0.8rem;
        width: 90px;
        outline: none;
        background: #ffffff;
    }

    /* Modules */
    .modules-container {
        display: grid;
        grid-template-columns: 1fr 1fr 1fr;
        gap: 8px;
        margin-bottom: 10px;
    }
    .module-card {
        border-radius: 6px;
        padding: 6px 8px;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
    }
    .mod-debit { background-color: #f0fdf4; border: 1px solid #bbf7d0; }
    .mod-gap { background-color: #fff1f2; border: 1px solid #fecdd3; }
    .mod-spike { background-color: #fefce8; border: 1px solid #fef08a; }
    .module-title { font-size: 0.82rem; font-weight: 700; margin-bottom: 6px; }
    .module-actions { display: flex; gap: 4px; align-items: center; }

    .btn {
        border: 1px solid #cbd5e1;
        background: #ffffff;
        border-radius: 4px;
        padding: 4px 10px;
        font-size: 0.76rem;
        font-weight: 600;
        cursor: pointer;
        flex: 1;
        text-align: center;
    }
    .btn-scan {
        background-color: #10b981;
        border-color: #10b981;
        color: white;
    }

    /* Table Toolbar */
    .results-head-bar {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin: 10px 0 6px 0;
    }
    .results-title { font-size: 0.96rem; font-weight: 700; display: flex; align-items: center; gap: 6px; }
    .search-input {
        border: 1px solid #cbd5e1;
        border-radius: 4px;
        padding: 4px 8px;
        font-size: 0.78rem;
        width: 130px;
    }

    /* Excel Table */
    .excel-table {
        width: 100%;
        border-collapse: collapse;
        font-size: 0.75rem;
        background: #ffffff;
    }
    .excel-table th {
        border: 1px solid #cbd5e1;
        padding: 5px 3px;
        text-align: center;
        font-weight: 600;
    }
    .excel-table td {
        border: 1px solid #e2e8f0;
        height: 22px;
        text-align: center;
    }
    .row-index {
        background-color: #f1f5f9;
        font-weight: 700;
        color: #64748b;
        width: 28px;
    }
    .col-letter-row th {
        background-color: #cbd5e1;
        color: #475569;
        font-weight: 700;
        font-size: 0.72rem;
    }
    .col-name-row th {
        background-color: #e2e8f0;
        color: #334155;
    }
</style>
</head>
<body>

<div class="scroll-wrapper">
    <!-- Top Header -->
    <div class="top-bar">
        <div>
            <div class="brand-title">📊 Project A Pro</div>
            <div class="brand-sub">Options Ratio Spread Scanner</div>
        </div>
        <div class="status-badge">
            <span style="color:#22c55e;">●</span> <b>Live Scan</b> &nbsp; <code>06 Oct 2026 12:30:15</code> 🔄
        </div>
    </div>

    <!-- Row 1: Filters -->
    <div class="filter-grid">
        <div class="field-box">
            <span class="field-label">Delta</span>
            <select class="styled-select"><option>0.20 - 0.25</option><option>0.15 - 0.20</option></select>
        </div>
        <div class="field-box">
            <span class="field-label">Ratio</span>
            <select class="styled-select"><option>1 : 3</option><option>1 : 2</option></select>
        </div>
        <div class="field-box">
            <span class="field-label">Option Type</span>
            <select class="styled-select"><option>CE (Call)</option><option>PE (Put)</option></select>
        </div>
        <div class="field-box">
            <span class="field-label">Expiry</span>
            <select class="styled-select"><option>26 Sep 2026</option><option>06 Oct 2026</option></select>
        </div>
        <div class="field-box">
            <span class="field-label">Result</span>
            <input type="text" class="styled-input" value="0" style="text-align:center;">
            <div class="figures-text">Figures</div>
        </div>
    </div>

    <!-- Row 2: Spread Cost -->
    <div style="font-size:0.76rem; font-weight:700; margin-bottom:4px;">Spread Cost (₹)</div>
    <div class="spread-row">
        <div class="cost-group">
            <div class="badge-debit">Debit</div>
            <input type="text" class="cost-val-input" value="0 - 5000">
        </div>
        <div class="cost-group">
            <div class="badge-credit">Credit</div>
            <input type="text" class="cost-val-input" value="0 - 5000">
        </div>
    </div>

    <!-- 3 Scanner Modules -->
    <div class="modules-container">
        <div class="module-card mod-debit">
            <div class="module-title">1. Debit ₹0 Scanner</div>
            <div class="module-actions">
                <button class="btn">Auto</button>
                <button class="btn">Manual</button>
                <button class="btn btn-scan">Scan</button>
            </div>
        </div>
        <div class="module-card mod-gap">
            <div class="module-title">2. % Gap Scanner</div>
            <div class="module-actions">
                <input type="text" value="20" style="width:36px; height:24px; text-align:center; border:1px solid #cbd5e1; border-radius:4px;">
                <span style="font-weight:bold; font-size:0.75rem;">%</span>
                <button class="btn">Auto</button>
                <button class="btn">Manual</button>
                <button class="btn btn-scan">Scan</button>
            </div>
        </div>
        <div class="module-card mod-spike">
            <div class="module-title">3. Option Premium Spike (UP / DOWN)</div>
            <div class="module-actions">
                <input type="text" value="10" style="width:36px; height:24px; text-align:center; border:1px solid #cbd5e1; border-radius:4px;">
                <span style="font-weight:bold; font-size:0.75rem;">%</span>
                <button class="btn">Auto</button>
                <button class="btn">Manual</button>
                <button class="btn btn-scan">Scan</button>
            </div>
        </div>
    </div>

    <!-- Results Header -->
    <div class="results-head-bar">
        <div class="results-title">🎯 Scan Results (Live)</div>
        <div style="font-size:0.8rem; color:#475569;">Total Results: <b>24</b></div>
        <input type="text" class="search-input" placeholder="🔍 Search...">
    </div>

    <!-- Complete Clean Excel Grid -->
    <table class="excel-table">
        <thead>
            <tr class="col-letter-row">
                <th class="row-index"></th>
                <th>A</th><th>B</th><th>C</th><th>D</th><th>E</th><th>F</th><th>G</th><th>H</th><th>I</th><th>J</th><th>K</th>
            </tr>
            <tr class="col-name-row">
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

# Append 14 excel rows cleanly
for i in range(1, 15):
    app_html += f"""
            <tr>
                <td class="row-index">{i}</td>
                <td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td>
            </tr>
    """

app_html += """
        </tbody>
    </table>
</div>

</body>
</html>
"""

# Component render: perfectly renders raw HTML without Markdown parser breaking it
components.html(app_html, height=720, scrolling=True)
