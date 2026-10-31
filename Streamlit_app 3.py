import streamlit as st

st.set_page_config(
    page_title="Auto Trade",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
    <style>
    .block-container {
        max-width: 1100px;
        padding: 0.65rem 0.8rem 1rem 0.8rem;
    }
    .app-title {
        text-align: center;
        font-size: 1.8rem;
        line-height: 1.15;
        font-weight: 800;
        margin: 0.1rem 0 1rem 0;
    }
    .row-gap { margin-top: 0.15rem; }
    div[data-testid="stWidgetLabel"] p {
        font-size: 0.9rem;
        font-weight: 650;
        margin-bottom: 0.2rem;
    }
    div[data-testid="stNumberInput"] input,
    div[data-testid="stSelectbox"] div[role="combobox"] {
        min-height: 2.45rem;
        font-size: 0.9rem;
    }
    div[data-testid="stNumberInput"] button {
        min-height: 2.35rem;
    }
    div.stButton > button {
        min-height: 2.7rem;
        width: 100%;
        border-radius: 0.5rem;
        font-weight: 700;
        padding: 0.25rem 0.4rem;
    }
    div[data-testid="stToggle"] {
        padding-top: 0.4rem;
    }
    .stDivider { margin: 0.55rem 0; }
    @media (max-width: 700px) {
        .block-container {
            padding-left: 0.45rem;
            padding-right: 0.45rem;
        }
        /* Keep the hand-drawn 3-column layout on phones. */
        div[data-testid="stHorizontalBlock"] {
            flex-wrap: nowrap !important;
            gap: 0.45rem !important;
        }
        div[data-testid="stHorizontalBlock"] > div[data-testid="column"] {
            min-width: 0 !important;
            width: 33.333% !important;
            flex: 1 1 0 !important;
        }
        div[data-testid="stNumberInput"] input {
            padding-left: 0.35rem;
            padding-right: 0.1rem;
            font-size: 0.82rem;
        }
        div[data-testid="stSelectbox"] div[role="combobox"] {
            font-size: 0.78rem;
        }
        div[data-testid="stWidgetLabel"] p {
            font-size: 0.78rem;
        }
        div.stButton > button {
            font-size: 0.78rem;
            padding-left: 0.15rem;
            padding-right: 0.15rem;
        }
        .app-title { font-size: 1.55rem; margin-bottom: 0.7rem; }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown('<div class="app-title">📈 Auto Trade</div>', unsafe_allow_html=True)

# Row 1: Delta | Ratio | Option
r1 = st.columns(3, gap="small")

with r1[0]:
    st.markdown("**Delta**")
    dmin, dmax = st.columns(2, gap="small")
    with dmin:
        min_delta = st.number_input(
            "Min", min_value=0.05, max_value=0.90, value=0.05,
            step=0.01, format="%.2f", key="min_delta"
        )
    with dmax:
        max_delta = st.number_input(
            "Max", min_value=0.05, max_value=0.90, value=0.90,
            step=0.01, format="%.2f", key="max_delta"
        )

with r1[1]:
    ratio = st.selectbox("Ratio", ["1:3", "3:10", "1:4", "2:7"], key="ratio")

with r1[2]:
    option = st.selectbox("Option", ["CE", "PE", "Both"], key="option")

st.divider()

# Row 2: Expiry | Result | Cost of Spread
r2 = st.columns(3, gap="small")

with r2[0]:
    expiry_month = st.selectbox(
        "Expiry",
        ["Current Month", "Far Month", "Third Month"],
        key="expiry_month",
    )

with r2[1]:
    result_value = st.number_input(
        "Result", min_value=-50000, max_value=50000, value=0,
        step=100, key="result_value"
    )

with r2[2]:
    spread_cost = st.number_input(
        "Cost of Spread", min_value=-50000, max_value=50000, value=0,
        step=100, key="spread_cost"
    )

st.divider()

# Row 3: VOL Gap | Auto ON/OFF | Manual Scan
r3 = st.columns(3, gap="small")

with r3[0]:
    vol_gap = st.number_input(
        "VOL Gap (%)", min_value=1.0, max_value=30.0, value=5.0,
        step=0.5, format="%.1f", key="vol_gap"
    )

with r3[1]:
    st.markdown("**Auto Scan**")
    auto_scan = st.toggle("Auto ON/OFF", value=False, key="auto_scan")

with r3[2]:
    st.markdown("**Manual Scan**")
    if st.button("Manual Scan", type="primary", use_container_width=True):
        st.info("UI તૈયાર છે. Scanner logic અને API હજી જોડેલાં નથી.")

if min_delta > max_delta:
    st.error("Min Delta, Max Delta કરતાં મોટું ન હોઈ શકે.")

# No scanner/API logic in this UI-only build.
