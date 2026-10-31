import streamlit as st

st.set_page_config(
    page_title="Auto Trade",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Compact 3-column layout. Scanner/API logic intentionally not included.
st.markdown(
    """
    <style>
    * { box-sizing: border-box; }
    .block-container {
        width: 100% !important;
        max-width: 100% !important;
        padding: 0.55rem 0.45rem 1rem 0.45rem !important;
    }
    .auto-title {
        text-align: center;
        font-size: 1.55rem;
        font-weight: 800;
        line-height: 1.2;
        margin: 0.2rem 0 0.8rem 0;
    }
    /* Force each Streamlit row to remain exactly 3 equal columns on phones. */
    div[data-testid="stHorizontalBlock"] {
        display: grid !important;
        grid-template-columns: repeat(3, minmax(0, 1fr)) !important;
        gap: 0.45rem !important;
        width: 100% !important;
        align-items: start !important;
    }
    div[data-testid="stHorizontalBlock"] > div[data-testid="column"] {
        width: auto !important;
        min-width: 0 !important;
        max-width: 100% !important;
        flex: initial !important;
        padding: 0 !important;
    }
    div[data-testid="stWidgetLabel"] {
        min-width: 0 !important;
    }
    div[data-testid="stWidgetLabel"] p {
        font-size: 0.78rem !important;
        font-weight: 650 !important;
        line-height: 1.15 !important;
        margin-bottom: 0.18rem !important;
        overflow-wrap: anywhere !important;
    }
    div[data-testid="stNumberInput"],
    div[data-testid="stSelectbox"] {
        width: 100% !important;
        min-width: 0 !important;
    }
    div[data-testid="stNumberInput"] input {
        min-width: 0 !important;
        width: 100% !important;
        padding-left: 0.3rem !important;
        padding-right: 0.1rem !important;
        font-size: 0.78rem !important;
    }
    div[data-testid="stSelectbox"] div[role="combobox"] {
        min-width: 0 !important;
        width: 100% !important;
        font-size: 0.76rem !important;
    }
    div[data-testid="stNumberInput"] button {
        min-width: 1.15rem !important;
        width: 1.15rem !important;
        padding: 0 !important;
    }
    div.stButton, div.stButton > button {
        width: 100% !important;
        min-width: 0 !important;
    }
    div.stButton > button {
        min-height: 2.5rem !important;
        padding: 0.25rem 0.12rem !important;
        font-size: 0.72rem !important;
        white-space: normal !important;
        line-height: 1.1 !important;
    }
    div[data-testid="stToggle"] {
        min-width: 0 !important;
        padding-top: 0.35rem !important;
    }
    div[data-testid="stToggle"] label p {
        font-size: 0.72rem !important;
        white-space: normal !important;
    }
    .cell-title {
        font-size: 0.82rem;
        font-weight: 700;
        margin: 0 0 0.25rem 0;
        line-height: 1.2;
    }
    hr { margin: 0.5rem 0 0.65rem 0 !important; }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown('<div class="auto-title">📈 Auto Trade</div>', unsafe_allow_html=True)

# ROW 1 — Delta | Ratio | Option
row1 = st.columns(3, gap="small")
with row1[0]:
    st.markdown('<div class="cell-title">Delta</div>', unsafe_allow_html=True)
    delta_min = st.number_input(
        "Min", min_value=0.05, max_value=0.90, value=0.05,
        step=0.01, format="%.2f", key="delta_min"
    )
    delta_max = st.number_input(
        "Max", min_value=0.05, max_value=0.90, value=0.90,
        step=0.01, format="%.2f", key="delta_max"
    )
with row1[1]:
    ratio = st.selectbox("Ratio", ["1:3", "3:10", "1:4", "2:7"], key="ratio")
with row1[2]:
    option = st.selectbox("Option", ["CE", "PE", "Both"], key="option")

st.divider()

# ROW 2 — Expiry | Result | Cost of Spread
row2 = st.columns(3, gap="small")
with row2[0]:
    expiry = st.selectbox(
        "Expiry", ["Current Month", "Far Month", "Third Month"], key="expiry"
    )
with row2[1]:
    result_value = st.number_input(
        "Result", min_value=-50000, max_value=50000, value=0,
        step=100, key="result_value"
    )
with row2[2]:
    spread_cost = st.number_input(
        "Cost of Spread", min_value=-50000, max_value=50000, value=0,
        step=100, key="spread_cost"
    )

st.divider()

# ROW 3 — VOL Gap | Auto Scan | Manual Scan
row3 = st.columns(3, gap="small")
with row3[0]:
    vol_gap = st.number_input(
        "VOL Gap (%)", min_value=1.0, max_value=30.0, value=5.0,
        step=0.5, format="%.1f", key="vol_gap"
    )
with row3[1]:
    st.markdown('<div class="cell-title">Auto Scan</div>', unsafe_allow_html=True)
    auto_scan = st.toggle("Auto ON/OFF", value=False, key="auto_scan")
with row3[2]:
    st.markdown('<div class="cell-title">Manual Scan</div>', unsafe_allow_html=True)
    manual_clicked = st.button("Manual Scan", type="primary", use_container_width=True)

if delta_min > delta_max:
    st.error("Delta Min, Max Delta કરતાં મોટું ન હોઈ શકે.")

if manual_clicked:
    st.info("UI Preview: Scanner logic અને API હજી જોડેલાં નથી.")
