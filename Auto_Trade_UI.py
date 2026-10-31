import streamlit as st

st.set_page_config(
    page_title="Auto Trade",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Compact, fixed three-column mobile layout matching the user's hand sketch.
st.markdown(
    """
    <style>
    .block-container {
        max-width: 100%;
        padding: 0.65rem 0.55rem 1rem 0.55rem;
    }
    .auto-title {
        text-align: center;
        font-size: 1.65rem;
        font-weight: 800;
        line-height: 1.2;
        margin: 0.15rem 0 1rem 0;
        white-space: nowrap;
    }

    /* Keep Streamlit's three columns side-by-side on narrow phone screens. */
    div[data-testid="stHorizontalBlock"] {
        display: flex !important;
        flex-wrap: nowrap !important;
        gap: 0.45rem !important;
        align-items: flex-start !important;
        width: 100% !important;
    }
    div[data-testid="stHorizontalBlock"] > div[data-testid="column"] {
        min-width: 0 !important;
        width: 0 !important;
        flex: 1 1 0 !important;
        padding: 0 !important;
    }

    div[data-testid="stWidgetLabel"] p {
        font-size: 0.82rem !important;
        font-weight: 650 !important;
        line-height: 1.15 !important;
        margin-bottom: 0.2rem !important;
    }
    div[data-testid="stNumberInput"] input {
        font-size: 0.82rem !important;
        min-width: 0 !important;
    }
    div[data-testid="stSelectbox"] div[role="combobox"] {
        font-size: 0.78rem !important;
        min-width: 0 !important;
    }
    div[data-testid="stNumberInput"] button {
        min-width: 1.35rem !important;
        padding: 0 !important;
    }
    div.stButton > button {
        width: 100% !important;
        min-height: 2.55rem !important;
        padding: 0.25rem 0.15rem !important;
        font-size: 0.78rem !important;
        white-space: normal !important;
        border-radius: 0.55rem !important;
    }
    div[data-testid="stToggle"] label p {
        font-size: 0.76rem !important;
        line-height: 1.1 !important;
    }
    .cell-heading {
        font-size: 0.84rem;
        font-weight: 700;
        margin: 0 0 0.3rem 0;
    }
    hr {
        margin: 0.55rem 0 0.75rem 0 !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown('<div class="auto-title">📈 Auto Trade</div>', unsafe_allow_html=True)

# ROW 1 — Delta | Ratio | Option
row1 = st.columns(3, gap="small")

with row1[0]:
    st.markdown('<div class="cell-heading">Delta</div>', unsafe_allow_html=True)
    delta_min = st.number_input(
        "Min", min_value=0.05, max_value=0.90, value=0.05,
        step=0.01, format="%.2f", key="delta_min"
    )
    delta_max = st.number_input(
        "Max", min_value=0.05, max_value=0.90, value=0.90,
        step=0.01, format="%.2f", key="delta_max"
    )

with row1[1]:
    ratio = st.selectbox(
        "Ratio", ["1:3", "3:10", "1:4", "2:7"], key="ratio"
    )

with row1[2]:
    option = st.selectbox(
        "Option", ["CE", "PE", "Both"], key="option"
    )

st.divider()

# ROW 2 — Expiry | Result | Cost of Spread
row2 = st.columns(3, gap="small")

with row2[0]:
    expiry = st.selectbox(
        "Expiry",
        ["Current Month", "Far Month", "Third Month"],
        key="expiry",
    )

with row2[1]:
    result_value = st.number_input(
        "Result", min_value=-50000, max_value=50000, value=0,
        step=100, key="result"
    )

with row2[2]:
    spread_cost = st.number_input(
        "Cost of Spread", min_value=-50000, max_value=50000, value=0,
        step=100, key="spread_cost"
    )

st.divider()

# ROW 3 — VOL Gap | Auto ON/OFF | Manual Scan
row3 = st.columns(3, gap="small")

with row3[0]:
    vol_gap = st.number_input(
        "VOL Gap (%)", min_value=1.0, max_value=30.0, value=5.0,
        step=0.5, format="%.1f", key="vol_gap"
    )

with row3[1]:
    st.markdown('<div class="cell-heading">Auto Scan</div>', unsafe_allow_html=True)
    auto_scan = st.toggle("Auto ON/OFF", value=False, key="auto_scan")

with row3[2]:
    st.markdown('<div class="cell-heading">Manual Scan</div>', unsafe_allow_html=True)
    manual_clicked = st.button(
        "Manual Scan", type="primary", use_container_width=True
    )

if delta_min > delta_max:
    st.error("Delta Min must be less than or equal to Delta Max.")

# UI-only stage: scanner logic and API intentionally not connected.
if manual_clicked:
    st.info("UI તૈયાર છે. Scanner logic અને API હજી જોડેલાં નથી.")
