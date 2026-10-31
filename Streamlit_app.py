import streamlit as st

st.set_page_config(
    page_title="Auto Trade",
    page_icon="📈",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# Mobile-first styling: controls stack vertically like the user's reference.
st.markdown(
    """
    <style>
    .block-container {
        max-width: 760px;
        padding: 1.1rem 1rem 2.5rem 1rem;
    }
    .app-title {
        text-align: center;
        font-size: 2.1rem;
        line-height: 1.2;
        font-weight: 800;
        margin: 0.3rem 0 2rem 0;
    }
    div[data-testid="stWidgetLabel"] p {
        font-size: 1rem;
        font-weight: 600;
    }
    div[data-testid="stNumberInput"] input,
    div[data-testid="stSelectbox"] div[role="combobox"] {
        min-height: 2.8rem;
        font-size: 1rem;
    }
    div.stButton > button {
        min-height: 3rem;
        width: 100%;
        border-radius: 0.6rem;
        font-weight: 700;
    }
    .section-heading {
        font-size: 1.35rem;
        font-weight: 750;
        margin: 1.7rem 0 1rem 0;
    }
    .helper-text {
        color: #777;
        font-size: 0.85rem;
        margin-top: -0.4rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown('<div class="app-title">📈 Auto Trade</div>', unsafe_allow_html=True)

# DELTA
st.markdown('<div class="section-heading">Delta</div>', unsafe_allow_html=True)
min_delta = st.number_input(
    "Min",
    min_value=0.05,
    max_value=0.90,
    value=0.05,
    step=0.01,
    format="%.2f",
    key="min_delta",
)
max_delta = st.number_input(
    "Max",
    min_value=0.05,
    max_value=0.90,
    value=0.90,
    step=0.01,
    format="%.2f",
    key="max_delta",
)

# RATIO
ratio = st.selectbox(
    "Ratio",
    ["1:3", "3:10", "1:4", "2:7"],
    index=0,
    key="ratio",
)

# OPTION
option = st.selectbox(
    "Option",
    ["CE (Call)", "PE (Put)", "Both"],
    index=0,
    key="option",
)

st.divider()

# EXPIRY
st.markdown('<div class="section-heading">Expiry</div>', unsafe_allow_html=True)
expiry_placeholder = ["Expiry dates will load after API integration"]
current_expiry = st.selectbox(
    "Current Month", expiry_placeholder, key="current_expiry"
)
far_expiry = st.selectbox(
    "Far Month", expiry_placeholder, key="far_expiry"
)
third_expiry = st.selectbox(
    "Third Month", expiry_placeholder, key="third_expiry"
)

# RESULT AND COST
result_value = st.number_input(
    "Result",
    min_value=-50000,
    max_value=50000,
    value=0,
    step=100,
    key="result_value",
    help="Enter any value from -50,000 to +50,000.",
)
spread_cost = st.number_input(
    "Cost of Spread",
    min_value=-50000,
    max_value=50000,
    value=0,
    step=100,
    key="spread_cost",
    help="Enter any value from -50,000 to +50,000.",
)

# VOL GAP
vol_gap = st.number_input(
    "VOL Gap (%)",
    min_value=1.0,
    max_value=30.0,
    value=5.0,
    step=0.5,
    format="%.1f",
    key="vol_gap",
    help="Enter a percentage from 1% to 30%.",
)

st.divider()

# AUTO / MANUAL CONTROLS
st.markdown('<div class="section-heading">Auto Scan</div>', unsafe_allow_html=True)
auto_scan = st.toggle("Auto ON / OFF", value=False, key="auto_scan")
if auto_scan:
    st.info("Auto Scan ON — scanner/API logic will be connected in the next stage.")
else:
    st.caption("Auto Scan OFF")

st.markdown('<div class="section-heading">Manual Scan</div>', unsafe_allow_html=True)
if st.button("Manual Scan", type="primary", use_container_width=True):
    st.info("UI તૈયાર છે. Scanner logic અને API હજી જોડેલાં નથી.")

# Input validation
if min_delta < 0.05 or min_delta > 0.90:
    st.error("Min Delta 0.05 થી 0.90 વચ્ચે હોવો જોઈએ.")
elif max_delta < 0.05 or max_delta > 0.90:
    st.error("Max Delta 0.05 થી 0.90 વચ્ચે હોવો જોઈએ.")
elif min_delta > max_delta:
    st.error("Min Delta, Max Delta કરતાં મોટું ન હોઈ શકે.")

st.markdown(
    '<p class="helper-text">UI-only build • Scanner logic અને API હજી જોડેલાં નથી.</p>',
    unsafe_allow_html=True,
)
