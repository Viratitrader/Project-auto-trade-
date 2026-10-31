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
        padding: 1.2rem 1rem 2rem 1rem;
    }
    .app-title {
        text-align: center;
        font-size: 2rem;
        font-weight: 800;
        margin: 0.2rem 0 1.3rem 0;
    }
    div[data-testid="stWidgetLabel"] p {
        font-weight: 700;
        font-size: 1rem;
    }
    div[data-testid="stNumberInput"] input,
    div[data-testid="stSelectbox"] div[role="combobox"] {
        min-height: 2.8rem;
    }
    div.stButton > button {
        min-height: 2.9rem;
        width: 100%;
        font-weight: 700;
        border-radius: 0.55rem;
    }
    .section-note {
        color: #777;
        font-size: 0.85rem;
        text-align: center;
        margin-top: 0.25rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown('<div class="app-title">📈 Auto Trade</div>', unsafe_allow_html=True)

# Row 1: Delta / Ratio / Option
row1 = st.columns(3, gap="medium")

with row1[0]:
    st.markdown("**Delta**")
    d1, d2 = st.columns(2, gap="small")
    with d1:
        min_delta = st.number_input(
            "Min", min_value=0.05, max_value=0.90, value=0.05,
            step=0.01, format="%.2f", key="min_delta"
        )
    with d2:
        max_delta = st.number_input(
            "Max", min_value=0.05, max_value=0.90, value=0.90,
            step=0.01, format="%.2f", key="max_delta"
        )

with row1[1]:
    ratio = st.selectbox("Ratio", ["1:3", "3:10", "1:4", "2:7"], key="ratio")

with row1[2]:
    option = st.selectbox("Option", ["CE (Call)", "PE (Put)", "Both"], key="option")

st.divider()

# Row 2: Expiry / Result / Cost of Spread
row2 = st.columns(3, gap="medium")

with row2[0]:
    st.markdown("**Expiry**")
    current_expiry = st.selectbox(
        "Current Month", ["Expiry dates will load after API integration"],
        key="current_expiry"
    )
    far_expiry = st.selectbox(
        "Far Month", ["Expiry dates will load after API integration"],
        key="far_expiry"
    )
    third_expiry = st.selectbox(
        "Third Month", ["Expiry dates will load after API integration"],
        key="third_expiry"
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

# Row 3: VOL Gap / Auto Scan / Manual Scan
row3 = st.columns(3, gap="medium")

with row3[0]:
    vol_gap = st.number_input(
        "VOL Gap (%)", min_value=1.0, max_value=30.0, value=5.0,
        step=0.5, format="%.1f", key="vol_gap"
    )

with row3[1]:
    st.markdown("**Auto Scan**")
    auto_scan = st.toggle("Auto ON / OFF", value=False, key="auto_scan")
    st.caption("Auto Scan is ON" if auto_scan else "Auto Scan is OFF")

with row3[2]:
    st.markdown("**Manual Scan**")
    if st.button("Manual Scan", type="primary", use_container_width=True):
        st.info("UI તૈયાર છે. Scanner logic અને API હજી જોડેલાં નથી.")

if min_delta > max_delta:
    st.error("Min Delta, Max Delta કરતાં મોટું ન હોઈ શકે. કૃપા કરીને રેન્જ સુધારો.")

st.markdown(
    '<div class="section-note">UI-only build • Scanner/API logic is intentionally not connected yet.</div>',
    unsafe_allow_html=True,
)
