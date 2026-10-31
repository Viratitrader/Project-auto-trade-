import streamlit as st
import requests
import gzip
import json
import re
import pandas as pd
from datetime import date
from concurrent.futures import ThreadPoolExecutor, as_completed


# =========================================================
# PAGE
# =========================================================

st.set_page_config(
    page_title="NSE F&O 1:3 Call Ratio Spread Scanner",
    page_icon="📊",
    layout="wide"
)

st.markdown("""
<style>
.block-container {
    padding-top: 0.8rem;
    padding-left: 0.7rem;
    padding-right: 0.7rem;
    max-width: 1100px;
}

h1 {
    font-size: 1.45rem !important;
    margin-bottom: 0.7rem !important;
}

/* Scan button */
.stButton > button {
    width: 100%;
    min-height: 48px;
    font-size: 17px;
    font-weight: 700;
    border-radius: 10px;
}

/* RESULT CARD */
.result-card {
    border-radius: 12px;
    padding: 12px;
    margin: 8px 0;
    color: #111111;
    font-size: 14px;
    line-height: 1.45;
}

.debit-card {
    background: #ffdada;
    border: 2px solid #e00000;
}

.credit-card {
    background: #d9f7d9;
    border: 2px solid #008000;
}

.stock-title {
    font-size: 20px;
    font-weight: 800;
    margin-bottom: 6px;
}

.big-value {
    font-size: 16px;
    font-weight: 800;
    margin-top: 3px;
}

.small-line {
    font-size: 13px;
    margin-top: 3px;
}

.section-title {
    font-size: 15px;
    font-weight: 800;
    margin-top: 7px;
}
</style>
""", unsafe_allow_html=True)


# =========================================================
# CONSTANTS
# =========================================================

OPTION_CHAIN_URL = "https://api.upstox.com/v2/option/chain"

INSTRUMENT_URLS = [
    "https://assets.upstox.com/market-quote/instruments/exchange/complete.json.gz",
    "https://assets.upstox.com/market-quote/instruments/exchange/NSE.json.gz"
]

TODAY = date.today()


# =========================================================
# TITLE
# =========================================================

st.title("NSE F&O 1:3 Call Ratio Spread Scanner")


# =========================================================
# ACCESS TOKEN
# =========================================================


# =========================================================
# UPSTOX ACCESS TOKEN
# LOAD FROM STREAMLIT SECRETS
# =========================================================

secret_token = st.secrets.get(
    "UPSTOX_ACCESS_TOKEN",
    ""
)

if secret_token:

    access_token = str(
        secret_token
    ).strip()

else:

    if "upstox_access_token" not in st.session_state:
        st.session_state.upstox_access_token = ""

    token_input = st.text_input(
        "Upstox Access Token",
        type="password",
        key="upstox_token_input",
        placeholder="Paste Upstox access token"
    )

    if token_input.strip():
        st.session_state.upstox_access_token = (
            token_input.strip()
        )

    access_token = st.session_state.get(
        "upstox_access_token",
        ""
    )

# =========================================================
# INPUT PARSERS
# =========================================================

def parse_amount_range(text, label):
    """
    500       -> 0 to 500
    5000      -> 0 to 5000
    10000     -> 0 to 10000
    500-5000  -> 500 to 5000
    0         -> 0 to 0
    """

    text = str(text).strip().replace(",", "")

    if not text:
        raise ValueError(
            f"{label} cannot be empty."
        )

    # Single value
    if re.fullmatch(
        r"\d+(?:\.\d+)?",
        text
    ):
        high = float(text)

        if high > 10000:
            raise ValueError(
                f"{label} maximum is ₹10,000."
            )

        return 0.0, high

    # Range
    match = re.fullmatch(
        r"(\d+(?:\.\d+)?)\s*-\s*(\d+(?:\.\d+)?)",
        text
    )

    if match:
        low = float(match.group(1))
        high = float(match.group(2))

        if low > 10000 or high > 10000:
            raise ValueError(
                f"{label} maximum is ₹10,000."
            )

        if low > high:
            low, high = high, low

        return low, high

    raise ValueError(
        f"Invalid {label}. Use 500, 5000 or 500-5000."
    )


def parse_delta_range(text):

    text = str(text).strip().replace(" ", "")

    if not text:
        raise ValueError("Delta cannot be empty.")

    # 10-35
    if re.fullmatch(
        r"\d+(?:\.\d+)?-\d+(?:\.\d+)?",
        text
    ):
        a, b = text.split("-")

        low = float(a)
        high = float(b)

        if low < 0 or high > 100:
            raise ValueError(
                "Delta must be between 0 and 100."
            )

        if low > high:
            low, high = high, low

        return [(low, high)]

    # 5,10,15,20,35
    if "," in text:

        values = []

        for x in text.split(","):

            if not re.fullmatch(
                r"\d+(?:\.\d+)?",
                x
            ):
                raise ValueError(
                    "Invalid Delta."
                )

            value = float(x)

            if value < 0 or value > 100:
                raise ValueError(
                    "Delta must be between 0 and 100."
                )

            values.append(value)

        values = sorted(set(values))

        if len(values) == 1:
            return [(0, values[0])]

        return [
            (values[i], values[i + 1])
            for i in range(len(values) - 1)
        ]

    # 25
    if re.fullmatch(
        r"\d+(?:\.\d+)?",
        text
    ):
        value = float(text)

        if value < 0 or value > 100:
            raise ValueError(
                "Delta must be between 0 and 100."
            )

        return [(0, value)]

    raise ValueError(
        "Invalid Delta. Use 25, 10-35 or 5,10,15,20,35."
    )


def delta_passes(delta, ranges):

    value = abs(float(delta))

    for low, high in ranges:
        if low <= value <= high:
            return True

    return False


# =========================================================
# INSTRUMENT MASTER
# =========================================================

@st.cache_data(ttl=3600)
def load_instruments():

    last_error = None

    for url in INSTRUMENT_URLS:

        try:
            response = requests.get(
                url,
                timeout=30,
                headers={
                    "User-Agent": "Mozilla/5.0"
                }
            )

            response.raise_for_status()

            raw = gzip.decompress(
                response.content
            )

            data = json.loads(
                raw.decode("utf-8")
            )

            if isinstance(data, dict):

                if "data" in data:
                    data = data["data"]
                else:
                    data = list(data.values())

            df = pd.DataFrame(data)

            if not df.empty:
                return df

        except Exception as e:
            last_error = e

    raise RuntimeError(
        f"Unable to load Upstox instruments: {last_error}"
    )


# =========================================================
# BUILD ORIGINAL NSE F&O UNIVERSE
# =========================================================

@st.cache_data(ttl=3600)
def build_universe():

    df = load_instruments().copy()

    required = [
        "segment",
        "instrument_type",
        "underlying_type",
        "underlying_key",
        "expiry",
        "lot_size"
    ]

    for col in required:
        if col not in df.columns:
            raise RuntimeError(
                f"Instrument master missing column: {col}"
            )

    df = df[
        (df["segment"].astype(str) == "NSE_FO")
        &
        (df["instrument_type"].astype(str) == "CE")
        &
        (df["underlying_type"].astype(str) == "EQUITY")
        &
        (
            df["underlying_key"]
            .astype(str)
            .str.startswith("NSE_EQ|")
        )
    ].copy()

    # Expiry can be date text or timestamp
    raw_expiry = df["expiry"]

    numeric_expiry = pd.to_numeric(
        raw_expiry,
        errors="coerce"
    )

    text_expiry = pd.to_datetime(
        raw_expiry,
        errors="coerce"
    )

    timestamp_expiry = pd.to_datetime(
        numeric_expiry,
        unit="ms",
        errors="coerce"
    )

    df["expiry_dt"] = text_expiry

    mask = numeric_expiry.notna()

    df.loc[mask, "expiry_dt"] = (
        timestamp_expiry[mask]
    )

    df["expiry"] = (
        df["expiry_dt"].dt.date
    )

    df["lot_size"] = pd.to_numeric(
        df["lot_size"],
        errors="coerce"
    )

    df = df[
        df["expiry"].notna()
        &
        (df["expiry"] >= TODAY)
        &
        (df["lot_size"] > 0)
    ].copy()

    if df.empty:
        raise RuntimeError(
            "No current/future NSE F&O expiry found."
        )

    # Keep actual symbol if Upstox provides it.
    # This is ONLY for display; scanner logic is unchanged.
    symbol_column = None

    for col in [
        "underlying_symbol",
        "trading_symbol"
    ]:
        if col in df.columns:
            symbol_column = col
            break

    if symbol_column:
        universe = df[
            [
                "underlying_key",
                symbol_column,
                "expiry",
                "lot_size"
            ]
        ].drop_duplicates().copy()

        universe["symbol"] = (
            universe[symbol_column]
            .astype(str)
            .str.strip()
        )

    else:
        universe = df[
            [
                "underlying_key",
                "expiry",
                "lot_size"
            ]
        ].drop_duplicates().copy()

        universe["symbol"] = (
            universe["underlying_key"]
            .astype(str)
            .str.replace(
                "NSE_EQ|",
                "",
                regex=False
            )
        )

    return universe


# =========================================================
# OPTION CHAIN
# =========================================================

def get_option_chain(
    underlying_key,
    expiry,
    token
):

    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {token}"
    }

    params = {
        "instrument_key": underlying_key,
        "expiry_date": expiry.isoformat()
    }

    response = requests.get(
        OPTION_CHAIN_URL,
        params=params,
        headers=headers,
        timeout=15
    )

    if response.status_code != 200:
        return []

    data = response.json().get(
        "data",
        []
    )

    if not isinstance(data, list):
        return []

    return data


# =========================================================
# EXTRACT CALLS
# =========================================================

def extract_calls(chain):

    calls = []

    for row in chain:

        try:

            strike = float(
                row.get(
                    "strike_price",
                    0
                )
            )

            call = row.get(
                "call_options",
                {}
            )

            market_data = call.get(
                "market_data",
                {}
            )

            greeks = call.get(
                "option_greeks",
                {}
            )

            ltp = float(
                market_data.get(
                    "ltp",
                    0
                ) or 0
            )

            delta = float(
                greeks.get(
                    "delta",
                    0
                ) or 0
            )

            instrument_key = call.get(
                "instrument_key"
            )

            if strike <= 0:
                continue

            if ltp <= 0:
                continue

            if not instrument_key:
                continue

            calls.append({
                "strike": strike,
                "ltp": ltp,
                "delta": delta,
                "instrument_key": instrument_key
            })

        except Exception:
            continue

    calls.sort(
        key=lambda x: x["strike"]
    )

    return calls


# =========================================================
# SUPPORTING SPREAD
# =========================================================

def find_supporting_spread(
    calls,
    b
):

    b_strike = b["strike"]
    b_ltp = b["ltp"]

    lower = [
        x for x in calls
        if x["strike"] < b_strike
    ]

    lower.sort(
        key=lambda x: x["strike"],
        reverse=True
    )

    for a in lower:

        # ORIGINAL RULE
        if a["ltp"] > 3 * b_ltp:

            gap = (
                b_strike
                - a["strike"]
            )

            c_strike = (
                b_strike
                + gap
            )

            c_list = [
                x for x in calls
                if abs(
                    x["strike"]
                    - c_strike
                ) < 0.01
            ]

            if not c_list:
                continue

            c = c_list[0]

            return a, c, gap

    return None


# =========================================================
# AMOUNT FILTER
# =========================================================

def amount_passes(
    target_net,
    lot_size,
    debit_range,
    credit_range
):

    total = abs(
        target_net * lot_size
    )

    # CREDIT
    if target_net > 0:

        low, high = credit_range

        return (
            low <= total <= high,
            total,
            "CREDIT"
        )

    # DEBIT
    if target_net < 0:

        low, high = debit_range

        return (
            low <= total <= high,
            total,
            "DEBIT"
        )

    return (
        (
            debit_range[0] <= 0 <= debit_range[1]
            or
            credit_range[0] <= 0 <= credit_range[1]
        ),
        0,
        "ZERO"
    )


# =========================================================
# SCAN ONE STOCK
# =========================================================

def scan_stock(
    item,
    expiry,
    delta_ranges,
    debit_range,
    credit_range,
    token
):

    symbol = item["symbol"]
    underlying_key = item["underlying_key"]
    lot_size = int(item["lot_size"])

    try:

        chain = get_option_chain(
            underlying_key,
            expiry,
            token
        )

        calls = extract_calls(chain)

        if len(calls) < 5:
            return []

        results = []

        for b in calls:

            delta_percent = (
                abs(b["delta"]) * 100
            )

            if not delta_passes(
                delta_percent,
                delta_ranges
            ):
                continue

            support = find_supporting_spread(
                calls,
                b
            )

            if support is None:
                continue

            a, c, gap = support

            # ORIGINAL:
            # BUY 1 B CE
            # SELL 3 C CE

            target_net = (
                3 * c["ltp"]
                - b["ltp"]
            )

            passed, total, side = amount_passes(
                target_net,
                lot_size,
                debit_range,
                credit_range
            )

            if not passed:
                continue

            ratio = (
                a["ltp"] / b["ltp"]
                if b["ltp"] > 0
                else 0
            )

            difference = (
                a["ltp"]
                - 3 * b["ltp"]
            )

            results.append({
                "symbol": symbol,
                "expiry": expiry,
                "buy_strike": b["strike"],
                "buy_ltp": b["ltp"],
                "delta": delta_percent,
                "sell_strike": c["strike"],
                "sell_ltp": c["ltp"],
                "target_net": target_net,
                "total_amount": total,
                "side": side,
                "gap": gap,
                "lot_size": lot_size,
                "support_a": a["strike"],
                "support_a_ltp": a["ltp"],
                "support_b": b["strike"],
                "support_b_ltp": b["ltp"],
                "ratio": ratio,
                "difference": difference
            })

        return results

    except Exception:
        return []


# =========================================================
# LOAD UNIVERSE
# =========================================================

try:

    universe = build_universe()

except Exception as e:

    st.error(str(e))
    st.stop()


# =========================================================
# EXPIRY
# =========================================================

available_expiries = sorted(
    universe["expiry"]
    .dropna()
    .unique()
)

if not available_expiries:

    st.error(
        "No valid NSE F&O expiry found."
    )

    st.stop()


expiry = st.selectbox(
    "Expiry",
    available_expiries,
    format_func=lambda x:
        x.strftime("%d-%b-%Y")
)


# =========================================================
# SCANNER UI
# =========================================================

st.markdown("### Scanner")

delta_input = st.text_input(
    "Delta",
    value="25",
    placeholder="25"
)

debit_input = st.text_input(
    "Debit",
    value="500",
    placeholder="500 or 500-5000"
)

credit_input = st.text_input(
    "Credit",
    value="0",
    placeholder="500 or 500-5000"
)


# =========================================================
# SCAN BUTTON
# =========================================================

scan_clicked = st.button(
    "🔍 SCAN ALL",
    type="primary",
    use_container_width=True
)


# =========================================================
# SCAN
# =========================================================

if scan_clicked:

    if not access_token:

        st.error(
            "Please enter your Upstox Access Token."
        )

        st.stop()

    try:

        delta_ranges = parse_delta_range(
            delta_input
        )

        debit_range = parse_amount_range(
            debit_input,
            "Debit"
        )

        credit_range = parse_amount_range(
            credit_input,
            "Credit"
        )

    except ValueError as e:

        st.error(str(e))
        st.stop()

    scan_universe = universe[
        universe["expiry"] == expiry
    ].drop_duplicates(
        subset=["underlying_key"]
    ).reset_index(drop=True)

    total_stocks = len(
        scan_universe
    )

    st.write(
        f"Scanning **{total_stocks} stocks...**"
    )

    progress = st.progress(0)

    results = []

    # ORIGINAL 5 WORKERS
    with ThreadPoolExecutor(
        max_workers=5
    ) as executor:

        futures = {}

        for _, item in scan_universe.iterrows():

            future = executor.submit(
                scan_stock,
                item,
                expiry,
                delta_ranges,
                debit_range,
                credit_range,
                access_token
            )

            futures[future] = item["symbol"]

        completed = 0

        for future in as_completed(
            futures
        ):

            completed += 1

            progress.progress(
                completed / total_stocks
            )

            try:

                output = future.result()

                if output:
                    results.extend(output)

            except Exception:
                pass

    progress.empty()

    if not results:

        st.warning(
            "No matching setups found."
        )

        st.stop()

    results.sort(
        key=lambda x: (
            0 if x["side"] == "CREDIT" else 1,
            -x["total_amount"]
        )
    )

    st.success(
        f"Found {len(results)} matching setups."
    )


    # =====================================================
    # RESULT PREVIEW
    # ONLY LAYOUT CHANGED HERE
    # =====================================================

    for r in results:

        if r["side"] == "CREDIT":

            card_class = "credit-card"

            net_text = (
                f"CREDIT ₹{r['total_amount']:,.2f}"
            )

        else:

            card_class = "debit-card"

            net_text = (
                f"DEBIT ₹{r['total_amount']:,.2f}"
            )

        # IMPORTANT:
        # Use markdown HTML as ONE complete string.
        # This prevents raw <div> tags from appearing.

        result_html = f"""
<div class="result-card {card_class}">

<div class="stock-title">
{r["symbol"]}
</div>

<div class="big-value">
BUY 1 CE: {r["buy_strike"]:g} @ ₹{r["buy_ltp"]:.2f}
</div>

<div class="small-line">
Delta: <b>{r["delta"]:.2f}</b>
</div>

<div class="big-value">
SELL 3 CE: {r["sell_strike"]:g} @ ₹{r["sell_ltp"]:.2f}
</div>

<div class="big-value">
{net_text}
</div>

<div class="small-line">
Gap: <b>{r["gap"]:g}</b>
&nbsp;&nbsp; | &nbsp;&nbsp;
Lot: <b>{r["lot_size"]}</b>
</div>

<div class="section-title">
Supporting Spread
</div>

<div class="small-line">
A: <b>{r["support_a"]:g}</b>
@ ₹{r["support_a_ltp"]:.2f}
&nbsp; → &nbsp;
B: <b>{r["support_b"]:g}</b>
@ ₹{r["support_b_ltp"]:.2f}
</div>

<div class="small-line">
A &gt; 3 × B
&nbsp; | &nbsp;
Ratio: <b>{r["ratio"]:.2f}x</b>
&nbsp; | &nbsp;
Difference: <b>₹{r["difference"]:.2f}</b>
</div>

</div>
"""

        st.markdown(
            result_html,
            unsafe_allow_html=True
        )


# =========================================================
# FOOTER
# =========================================================

st.caption(
    "BUY 1 B CE / SELL 3 C CE • A LTP > 3 × B LTP"
)
# =========================================================
# NEW 3:10 RATIO SCANNER
# OLD 1:3 CODE ABOVE REMAINS UNTOUCHED
# =========================================================

def find_supporting_spread_3_10(calls, b):

    b_strike = b["strike"]
    b_ltp = b["ltp"]

    lower = [
        x for x in calls
        if x["strike"] < b_strike
    ]

    lower.sort(
        key=lambda x: x["strike"],
        reverse=True
    )

    required_ratio = 10 / 3

    for a in lower:

        # 3:10 proportional supporting rule
        if a["ltp"] > required_ratio * b_ltp:

            gap = (
                b_strike
                - a["strike"]
            )

            c_strike = (
                b_strike
                + gap
            )

            c_list = [
                x for x in calls
                if abs(
                    x["strike"]
                    - c_strike
                ) < 0.01
            ]

            if not c_list:
                continue

            c = c_list[0]

            return a, c, gap

    return None


def amount_passes_3_10(
    target_net,
    lot_size,
    debit_range,
    credit_range
):

    total = abs(
        target_net * lot_size
    )

    # CREDIT
    if target_net > 0:

        low, high = credit_range

        return (
            low <= total <= high,
            total,
            "CREDIT"
        )

    # DEBIT
    if target_net < 0:

        low, high = debit_range

        return (
            low <= total <= high,
            total,
            "DEBIT"
        )

    # ZERO
    passed = (
        debit_range[0] <= 0 <= debit_range[1]
        or
        credit_range[0] <= 0 <= credit_range[1]
    )

    return (
        passed,
        0,
        "ZERO"
    )


def scan_stock_3_10(
    item,
    expiry,
    delta_ranges,
    debit_range,
    credit_range,
    token
):

    symbol = item["symbol"]
    underlying_key = item["underlying_key"]
    lot_size = int(item["lot_size"])

    try:

        chain = get_option_chain(
            underlying_key,
            expiry,
            token
        )

        calls = extract_calls(chain)

        if len(calls) < 5:
            return []

        results = []

        for b in calls:

            delta_percent = (
                abs(b["delta"]) * 100
            )

            if not delta_passes(
                delta_percent,
                delta_ranges
            ):
                continue

            support = find_supporting_spread_3_10(
                calls,
                b
            )

            if support is None:
                continue

            a, c, gap = support

            # 3:10 TARGET
            # BUY 3 B CE
            # SELL 10 C CE

            target_net = (
                10 * c["ltp"]
                - 3 * b["ltp"]
            )

            passed, total, side = amount_passes_3_10(
                target_net,
                lot_size,
                debit_range,
                credit_range
            )

            if not passed:
                continue

            ratio = (
                a["ltp"] / b["ltp"]
                if b["ltp"] > 0
                else 0
            )

            difference = (
                a["ltp"]
                - (10 / 3) * b["ltp"]
            )

            results.append({
                "symbol": symbol,
                "expiry": expiry,
                "buy_strike": b["strike"],
                "buy_ltp": b["ltp"],
                "delta": delta_percent,
                "sell_strike": c["strike"],
                "sell_ltp": c["ltp"],
                "target_net": target_net,
                "total_amount": total,
                "side": side,
                "gap": gap,
                "lot_size": lot_size,
                "support_a": a["strike"],
                "support_a_ltp": a["ltp"],
                "support_b": b["strike"],
                "support_b_ltp": b["ltp"],
                "ratio": ratio,
                "difference": difference
            })

        return results

    except Exception:
        return []


# =========================================================
# 3:10 SCAN BUTTON
# =========================================================

scan_3_10_clicked = st.button(
    "🔍 3:10 SCAN",
    type="primary",
    use_container_width=True
)


# =========================================================
# 3:10 SCAN
# =========================================================

if scan_3_10_clicked:

    if not access_token:

        st.error(
            "Please enter your Upstox Access Token."
        )

        st.stop()

    try:

        delta_ranges = parse_delta_range(
            delta_input
        )

        debit_range = parse_amount_range(
            debit_input,
            "Debit"
        )

        credit_range = parse_amount_range(
            credit_input,
            "Credit"
        )

    except ValueError as e:

        st.error(str(e))
        st.stop()

    scan_universe_3_10 = universe[
        universe["expiry"] == expiry
    ].drop_duplicates(
        subset=["underlying_key"]
    ).reset_index(drop=True)

    total_stocks = len(
        scan_universe_3_10
    )

    st.write(
        f"3:10 Scanning **{total_stocks} stocks...**"
    )

    progress_3_10 = st.progress(0)

    results_3_10 = []

    with ThreadPoolExecutor(
        max_workers=5
    ) as executor:

        futures = {}

        for _, item in scan_universe_3_10.iterrows():

            future = executor.submit(
                scan_stock_3_10,
                item,
                expiry,
                delta_ranges,
                debit_range,
                credit_range,
                access_token
            )

            futures[future] = item["symbol"]

        completed = 0

        for future in as_completed(
            futures
        ):

            completed += 1

            progress_3_10.progress(
                completed / total_stocks
            )

            try:

                output = future.result()

                if output:
                    results_3_10.extend(output)

            except Exception:
                pass

    progress_3_10.empty()

    if not results_3_10:

        st.warning(
            "No matching 3:10 setups found."
        )

    else:

        results_3_10.sort(
            key=lambda x: (
                0 if x["side"] == "CREDIT" else 1,
                -x["total_amount"]
            )
        )

        st.success(
            f"Found {len(results_3_10)} matching 3:10 setups."
        )

        for r in results_3_10:

            if r["side"] == "CREDIT":

                card_class = "credit-card"

                net_text = (
                    f"CREDIT ₹{r['total_amount']:,.2f}"
                )

            else:

                card_class = "debit-card"

                net_text = (
                    f"DEBIT ₹{r['total_amount']:,.2f}"
                )

            result_html_3_10 = f"""
<div class="result-card {card_class}">

<div class="stock-title">
{r["symbol"]}
</div>

<div class="big-value">
BUY 3 CE: {r["buy_strike"]:g} @ ₹{r["buy_ltp"]:.2f}
</div>

<div class="small-line">
Delta: <b>{r["delta"]:.2f}</b>
</div>

<div class="big-value">
SELL 10 CE: {r["sell_strike"]:g} @ ₹{r["sell_ltp"]:.2f}
</div>

<div class="big-value">
{net_text}
</div>

<div class="small-line">
Gap: <b>{r["gap"]:g}</b>
&nbsp;&nbsp; | &nbsp;&nbsp;
Lot: <b>{r["lot_size"]}</b>
</div>

<div class="section-title">
3:10 Supporting Spread
</div>

<div class="small-line">
A: <b>{r["support_a"]:g}</b>
@ ₹{r["support_a_ltp"]:.2f}
&nbsp; → &nbsp;
B: <b>{r["support_b"]:g}</b>
@ ₹{r["support_b_ltp"]:.2f}
</div>

<div class="small-line">
A &gt; (10/3) × B
&nbsp; | &nbsp;
Ratio: <b>{r["ratio"]:.2f}x</b>
&nbsp; | &nbsp;
Difference: <b>₹{r["difference"]:.2f}</b>
</div>

<div class="small-line">
<b>3:10 Ratio</b>
</div>

</div>
"""

            st.markdown(
                result_html_3_10,
                unsafe_allow_html=True
            )
# =========================================================
# NEW 1:4 RATIO SCANNER
# OLD 1:3 AND 3:10 CODE ABOVE REMAINS UNTOUCHED
# =========================================================

def find_supporting_spread_1_4(calls, b):

    b_strike = b["strike"]
    b_ltp = b["ltp"]

    lower = [
        x for x in calls
        if x["strike"] < b_strike
    ]

    lower.sort(
        key=lambda x: x["strike"],
        reverse=True
    )

    required_ratio = 4 / 1

    for a in lower:

        # 1:4 proportional supporting rule
        if a["ltp"] > required_ratio * b_ltp:

            gap = (
                b_strike
                - a["strike"]
            )

            c_strike = (
                b_strike
                + gap
            )

            c_list = [
                x for x in calls
                if abs(
                    x["strike"]
                    - c_strike
                ) < 0.01
            ]

            if not c_list:
                continue

            c = c_list[0]

            return a, c, gap

    return None


def amount_passes_1_4(
    target_net,
    lot_size,
    debit_range,
    credit_range
):

    total = abs(
        target_net * lot_size
    )

    # CREDIT
    if target_net > 0:

        low, high = credit_range

        return (
            low <= total <= high,
            total,
            "CREDIT"
        )

    # DEBIT
    if target_net < 0:

        low, high = debit_range

        return (
            low <= total <= high,
            total,
            "DEBIT"
        )

    # ZERO
    passed = (
        debit_range[0] <= 0 <= debit_range[1]
        or
        credit_range[0] <= 0 <= credit_range[1]
    )

    return (
        passed,
        0,
        "ZERO"
    )


def scan_stock_1_4(
    item,
    expiry,
    delta_ranges,
    debit_range,
    credit_range,
    token
):

    symbol = item["symbol"]
    underlying_key = item["underlying_key"]
    lot_size = int(item["lot_size"])

    try:

        chain = get_option_chain(
            underlying_key,
            expiry,
            token
        )

        calls = extract_calls(chain)

        if len(calls) < 5:
            return []

        results = []

        for b in calls:

            delta_percent = (
                abs(b["delta"]) * 100
            )

            if not delta_passes(
                delta_percent,
                delta_ranges
            ):
                continue

            support = find_supporting_spread_1_4(
                calls,
                b
            )

            if support is None:
                continue

            a, c, gap = support

            # 1:4 TARGET
            # BUY 1 B CE
            # SELL 4 C CE

            target_net = (
                4 * c["ltp"]
                - 1 * b["ltp"]
            )

            passed, total, side = amount_passes_1_4(
                target_net,
                lot_size,
                debit_range,
                credit_range
            )

            if not passed:
                continue

            ratio = (
                a["ltp"] / b["ltp"]
                if b["ltp"] > 0
                else 0
            )

            difference = (
                a["ltp"]
                - 4 * b["ltp"]
            )

            results.append({
                "symbol": symbol,
                "expiry": expiry,
                "buy_strike": b["strike"],
                "buy_ltp": b["ltp"],
                "delta": delta_percent,
                "sell_strike": c["strike"],
                "sell_ltp": c["ltp"],
                "target_net": target_net,
                "total_amount": total,
                "side": side,
                "gap": gap,
                "lot_size": lot_size,
                "support_a": a["strike"],
                "support_a_ltp": a["ltp"],
                "support_b": b["strike"],
                "support_b_ltp": b["ltp"],
                "ratio": ratio,
                "difference": difference
            })

        return results

    except Exception:
        return []


# =========================================================
# 1:4 SCAN BUTTON
# =========================================================

scan_1_4_clicked = st.button(
    "🔍 1:4 SCAN",
    type="primary",
    use_container_width=True
)


# =========================================================
# 1:4 SCAN
# =========================================================

if scan_1_4_clicked:

    if not access_token:

        st.error(
            "Please enter your Upstox Access Token."
        )

        st.stop()

    try:

        delta_ranges = parse_delta_range(
            delta_input
        )

        debit_range = parse_amount_range(
            debit_input,
            "Debit"
        )

        credit_range = parse_amount_range(
            credit_input,
            "Credit"
        )

    except ValueError as e:

        st.error(str(e))
        st.stop()

    scan_universe_1_4 = universe[
        universe["expiry"] == expiry
    ].drop_duplicates(
        subset=["underlying_key"]
    ).reset_index(drop=True)

    total_stocks = len(
        scan_universe_1_4
    )

    st.write(
        f"1:4 Scanning **{total_stocks} stocks...**"
    )

    progress_1_4 = st.progress(0)

    results_1_4 = []

    with ThreadPoolExecutor(
        max_workers=5
    ) as executor:

        futures = {}

        for _, item in scan_universe_1_4.iterrows():

            future = executor.submit(
                scan_stock_1_4,
                item,
                expiry,
                delta_ranges,
                debit_range,
                credit_range,
                access_token
            )

            futures[future] = item["symbol"]

        completed = 0

        for future in as_completed(
            futures
        ):

            completed += 1

            progress_1_4.progress(
                completed / total_stocks
            )

            try:

                output = future.result()

                if output:
                    results_1_4.extend(output)

            except Exception:
                pass

    progress_1_4.empty()

    if not results_1_4:

        st.warning(
            "No matching 1:4 setups found."
        )

    else:

        results_1_4.sort(
            key=lambda x: (
                0 if x["side"] == "CREDIT" else 1,
                -x["total_amount"]
            )
        )

        st.success(
            f"Found {len(results_1_4)} matching 1:4 setups."
        )

        for r in results_1_4:

            if r["side"] == "CREDIT":

                card_class = "credit-card"

                net_text = (
                    f"CREDIT ₹{r['total_amount']:,.2f}"
                )

            else:

                card_class = "debit-card"

                net_text = (
                    f"DEBIT ₹{r['total_amount']:,.2f}"
                )

            result_html_1_4 = f"""
<div class="result-card {card_class}">

<div class="stock-title">
{r["symbol"]}
</div>

<div class="big-value">
BUY 1 CE: {r["buy_strike"]:g} @ ₹{r["buy_ltp"]:.2f}
</div>

<div class="small-line">
Delta: <b>{r["delta"]:.2f}</b>
</div>

<div class="big-value">
SELL 4 CE: {r["sell_strike"]:g} @ ₹{r["sell_ltp"]:.2f}
</div>

<div class="big-value">
{net_text}
</div>

<div class="small-line">
Gap: <b>{r["gap"]:g}</b>
&nbsp;&nbsp; | &nbsp;&nbsp;
Lot: <b>{r["lot_size"]}</b>
</div>

<div class="section-title">
1:4 Supporting Spread
</div>

<div class="small-line">
A: <b>{r["support_a"]:g}</b>
@ ₹{r["support_a_ltp"]:.2f}
&nbsp; → &nbsp;
B: <b>{r["support_b"]:g}</b>
@ ₹{r["support_b_ltp"]:.2f}
</div>

<div class="small-line">
A &gt; 4 × B
&nbsp; | &nbsp;
Ratio: <b>{r["ratio"]:.2f}x</b>
&nbsp; | &nbsp;
Difference: <b>₹{r["difference"]:.2f}</b>
</div>

<div class="small-line">
<b>1:4 Ratio</b>
</div>

</div>
"""

            st.markdown(
                result_html_1_4,
                unsafe_allow_html=True
            )


# =========================================================
# NEW 2:7 RATIO SCANNER
# =========================================================

def find_supporting_spread_2_7(calls, b):

    b_strike = b["strike"]
    b_ltp = b["ltp"]

    lower = [
        x for x in calls
        if x["strike"] < b_strike
    ]

    lower.sort(
        key=lambda x: x["strike"],
        reverse=True
    )

    required_ratio = 7 / 2

    for a in lower:

        # 2:7 proportional supporting rule
        if a["ltp"] > required_ratio * b_ltp:

            gap = (
                b_strike
                - a["strike"]
            )

            c_strike = (
                b_strike
                + gap
            )

            c_list = [
                x for x in calls
                if abs(
                    x["strike"]
                    - c_strike
                ) < 0.01
            ]

            if not c_list:
                continue

            c = c_list[0]

            return a, c, gap

    return None


def amount_passes_2_7(
    target_net,
    lot_size,
    debit_range,
    credit_range
):

    total = abs(
        target_net * lot_size
    )

    # CREDIT
    if target_net > 0:

        low, high = credit_range

        return (
            low <= total <= high,
            total,
            "CREDIT"
        )

    # DEBIT
    if target_net < 0:

        low, high = debit_range

        return (
            low <= total <= high,
            total,
            "DEBIT"
        )

    # ZERO
    passed = (
        debit_range[0] <= 0 <= debit_range[1]
        or
        credit_range[0] <= 0 <= credit_range[1]
    )

    return (
        passed,
        0,
        "ZERO"
    )


def scan_stock_2_7(
    item,
    expiry,
    delta_ranges,
    debit_range,
    credit_range,
    token
):

    symbol = item["symbol"]
    underlying_key = item["underlying_key"]
    lot_size = int(item["lot_size"])

    try:

        chain = get_option_chain(
            underlying_key,
            expiry,
            token
        )

        calls = extract_calls(chain)

        if len(calls) < 5:
            return []

        results = []

        for b in calls:

            delta_percent = (
                abs(b["delta"]) * 100
            )

            if not delta_passes(
                delta_percent,
                delta_ranges
            ):
                continue

            support = find_supporting_spread_2_7(
                calls,
                b
            )

            if support is None:
                continue

            a, c, gap = support

            # 2:7 TARGET
            # BUY 2 B CE
            # SELL 7 C CE

            target_net = (
                7 * c["ltp"]
                - 2 * b["ltp"]
            )

            passed, total, side = amount_passes_2_7(
                target_net,
                lot_size,
                debit_range,
                credit_range
            )

            if not passed:
                continue

            ratio = (
                a["ltp"] / b["ltp"]
                if b["ltp"] > 0
                else 0
            )

            difference = (
                a["ltp"]
                - (7 / 2) * b["ltp"]
            )

            results.append({
                "symbol": symbol,
                "expiry": expiry,
                "buy_strike": b["strike"],
                "buy_ltp": b["ltp"],
                "delta": delta_percent,
                "sell_strike": c["strike"],
                "sell_ltp": c["ltp"],
                "target_net": target_net,
                "total_amount": total,
                "side": side,
                "gap": gap,
                "lot_size": lot_size,
                "support_a": a["strike"],
                "support_a_ltp": a["ltp"],
                "support_b": b["strike"],
                "support_b_ltp": b["ltp"],
                "ratio": ratio,
                "difference": difference
            })

        return results

    except Exception:
        return []


# =========================================================
# 2:7 SCAN BUTTON
# =========================================================

scan_2_7_clicked = st.button(
    "🔍 2:7 SCAN",
    type="primary",
    use_container_width=True
)


# =========================================================
# 2:7 SCAN
# =========================================================

if scan_2_7_clicked:

    if not access_token:

        st.error(
            "Please enter your Upstox Access Token."
        )

        st.stop()

    try:

        delta_ranges = parse_delta_range(
            delta_input
        )

        debit_range = parse_amount_range(
            debit_input,
            "Debit"
        )

        credit_range = parse_amount_range(
            credit_input,
            "Credit"
        )

    except ValueError as e:

        st.error(str(e))
        st.stop()

    scan_universe_2_7 = universe[
        universe["expiry"] == expiry
    ].drop_duplicates(
        subset=["underlying_key"]
    ).reset_index(drop=True)

    total_stocks = len(
        scan_universe_2_7
    )

    st.write(
        f"2:7 Scanning **{total_stocks} stocks...**"
    )

    progress_2_7 = st.progress(0)

    results_2_7 = []

    with ThreadPoolExecutor(
        max_workers=5
    ) as executor:

        futures = {}

        for _, item in scan_universe_2_7.iterrows():

            future = executor.submit(
                scan_stock_2_7,
                item,
                expiry,
                delta_ranges,
                debit_range,
                credit_range,
                access_token
            )

            futures[future] = item["symbol"]

        completed = 0

        for future in as_completed(
            futures
        ):

            completed += 1

            progress_2_7.progress(
                completed / total_stocks
            )

            try:

                output = future.result()

                if output:
                    results_2_7.extend(output)

            except Exception:
                pass

    progress_2_7.empty()

    if not results_2_7:

        st.warning(
            "No matching 2:7 setups found."
        )

    else:

        results_2_7.sort(
            key=lambda x: (
                0 if x["side"] == "CREDIT" else 1,
                -x["total_amount"]
            )
        )

        st.success(
            f"Found {len(results_2_7)} matching 2:7 setups."
        )

        for r in results_2_7:

            if r["side"] == "CREDIT":

                card_class = "credit-card"

                net_text = (
                    f"CREDIT ₹{r['total_amount']:,.2f}"
                )

            else:

                card_class = "debit-card"

                net_text = (
                    f"DEBIT ₹{r['total_amount']:,.2f}"
                )

            result_html_2_7 = f"""
<div class="result-card {card_class}">

<div class="stock-title">
{r["symbol"]}
</div>

<div class="big-value">
BUY 2 CE: {r["buy_strike"]:g} @ ₹{r["buy_ltp"]:.2f}
</div>

<div class="small-line">
Delta: <b>{r["delta"]:.2f}</b>
</div>

<div class="big-value">
SELL 7 CE: {r["sell_strike"]:g} @ ₹{r["sell_ltp"]:.2f}
</div>

<div class="big-value">
{net_text}
</div>

<div class="small-line">
Gap: <b>{r["gap"]:g}</b>
&nbsp;&nbsp; | &nbsp;&nbsp;
Lot: <b>{r["lot_size"]}</b>
</div>

<div class="section-title">
2:7 Supporting Spread
</div>

<div class="small-line">
A: <b>{r["support_a"]:g}</b>
@ ₹{r["support_a_ltp"]:.2f}
&nbsp; → &nbsp;
B: <b>{r["support_b"]:g}</b>
@ ₹{r["support_b_ltp"]:.2f}
</div>

<div class="small-line">
A &gt; (7/2) × B
&nbsp; | &nbsp;
Ratio: <b>{r["ratio"]:.2f}x</b>
&nbsp; | &nbsp;
Difference: <b>₹{r["difference"]:.2f}</b>
</div>

<div class="small-line">
<b>2:7 Ratio</b>
</div>

</div>
"""

            st.markdown(
                result_html_2_7,
                unsafe_allow_html=True
            )
# =========================================================
# PUT SIDE RATIO SCANNERS
# 1:3 • 3:10 • 1:4 • 2:7
# CALL SIDE CODE ABOVE REMAINS UNTOUCHED
# =========================================================


# =========================================================
# EXTRACT PUTS
# =========================================================

def extract_puts(chain):

    puts = []

    for row in chain:

        try:

            strike = float(
                row.get(
                    "strike_price",
                    0
                )
            )

            put = row.get(
                "put_options",
                {}
            )

            market_data = put.get(
                "market_data",
                {}
            )

            greeks = put.get(
                "option_greeks",
                {}
            )

            ltp = float(
                market_data.get(
                    "ltp",
                    0
                ) or 0
            )

            delta = float(
                greeks.get(
                    "delta",
                    0
                ) or 0
            )

            instrument_key = put.get(
                "instrument_key"
            )

            if strike <= 0:
                continue

            if ltp <= 0:
                continue

            if not instrument_key:
                continue

            puts.append({
                "strike": strike,
                "ltp": ltp,
                "delta": delta,
                "instrument_key": instrument_key
            })

        except Exception:
            continue

    puts.sort(
        key=lambda x: x["strike"]
    )

    return puts


# =========================================================
# GENERIC PUT SUPPORTING SPREAD
# =========================================================

def find_supporting_put_spread(
    puts,
    b,
    buy_qty,
    sell_qty
):

    b_strike = b["strike"]
    b_ltp = b["ltp"]

    higher = [
        x for x in puts
        if x["strike"] > b_strike
    ]

    higher.sort(
        key=lambda x: x["strike"]
    )

    required_ratio = (
        sell_qty / buy_qty
    )

    for a in higher:

        if a["ltp"] > required_ratio * b_ltp:

            gap = (
                a["strike"]
                - b_strike
            )

            c_strike = (
                b_strike
                - gap
            )

            c_list = [
                x for x in puts
                if abs(
                    x["strike"]
                    - c_strike
                ) < 0.01
            ]

            if not c_list:
                continue

            c = c_list[0]

            return a, c, gap

    return None


# =========================================================
# GENERIC PUT SCANNER
# =========================================================

def scan_stock_put_ratio(
    item,
    expiry,
    delta_ranges,
    debit_range,
    credit_range,
    token,
    buy_qty,
    sell_qty,
    ratio_name
):

    symbol = item["symbol"]
    underlying_key = item["underlying_key"]
    lot_size = int(item["lot_size"])

    try:

        chain = get_option_chain(
            underlying_key,
            expiry,
            token
        )

        puts = extract_puts(chain)

        if len(puts) < 5:
            return []

        results = []

        for b in puts:

            delta_percent = (
                abs(b["delta"]) * 100
            )

            if not delta_passes(
                delta_percent,
                delta_ranges
            ):
                continue

            support = find_supporting_put_spread(
                puts,
                b,
                buy_qty,
                sell_qty
            )

            if support is None:
                continue

            a, c, gap = support

            target_net = (
                sell_qty * c["ltp"]
                - buy_qty * b["ltp"]
            )

            total = abs(
                target_net * lot_size
            )

            if target_net > 0:

                low, high = credit_range
                side = "CREDIT"

            elif target_net < 0:

                low, high = debit_range
                side = "DEBIT"

            else:

                low = min(
                    debit_range[0],
                    credit_range[0]
                )

                high = max(
                    debit_range[1],
                    credit_range[1]
                )

                side = "ZERO"

            if not (
                low <= total <= high
            ):
                continue

            ratio = (
                a["ltp"] / b["ltp"]
                if b["ltp"] > 0
                else 0
            )

            required_ratio = (
                sell_qty / buy_qty
            )

            difference = (
                a["ltp"]
                - required_ratio * b["ltp"]
            )

            results.append({

                "symbol": symbol,
                "expiry": expiry,

                "buy_strike": b["strike"],
                "buy_ltp": b["ltp"],

                "delta": delta_percent,

                "sell_strike": c["strike"],
                "sell_ltp": c["ltp"],

                "target_net": target_net,
                "total_amount": total,
                "side": side,

                "gap": gap,
                "lot_size": lot_size,

                "support_a": a["strike"],
                "support_a_ltp": a["ltp"],

                "support_b": b["strike"],
                "support_b_ltp": b["ltp"],

                "ratio": ratio,
                "difference": difference,

                "buy_qty": buy_qty,
                "sell_qty": sell_qty,
                "ratio_name": ratio_name

            })

        return results

    except Exception:

        return []


# =========================================================
# PUT SCAN BUTTONS
# =========================================================

scan_put_1_3_clicked = st.button(
    "🔍 PUT 1:3 SCAN",
    type="primary",
    use_container_width=True
)

scan_put_3_10_clicked = st.button(
    "🔍 PUT 3:10 SCAN",
    type="primary",
    use_container_width=True
)

scan_put_1_4_clicked = st.button(
    "🔍 PUT 1:4 SCAN",
    type="primary",
    use_container_width=True
)

scan_put_2_7_clicked = st.button(
    "🔍 PUT 2:7 SCAN",
    type="primary",
    use_container_width=True
)


# =========================================================
# RUN SELECTED PUT SCAN
# =========================================================

put_scan_config = None

if scan_put_1_3_clicked:

    put_scan_config = (
        1,
        3,
        "1:3"
    )

elif scan_put_3_10_clicked:

    put_scan_config = (
        3,
        10,
        "3:10"
    )

elif scan_put_1_4_clicked:

    put_scan_config = (
        1,
        4,
        "1:4"
    )

elif scan_put_2_7_clicked:

    put_scan_config = (
        2,
        7,
        "2:7"
    )


# =========================================================
# PUT SCAN ENGINE
# =========================================================

if put_scan_config is not None:

    buy_qty, sell_qty, ratio_name = (
        put_scan_config
    )

    if not access_token:

        st.error(
            "Please enter your Upstox Access Token."
        )

        st.stop()

    try:

        delta_ranges = parse_delta_range(
            delta_input
        )

        debit_range = parse_amount_range(
            debit_input,
            "Debit"
        )

        credit_range = parse_amount_range(
            credit_input,
            "Credit"
        )

    except ValueError as e:

        st.error(str(e))
        st.stop()

    scan_universe_put = universe[
        universe["expiry"] == expiry
    ].drop_duplicates(
        subset=["underlying_key"]
    ).reset_index(drop=True)

    total_stocks = len(
        scan_universe_put
    )

    st.write(
        f"PUT {ratio_name} Scanning **{total_stocks} stocks...**"
    )

    progress_put = st.progress(0)

    results_put = []

    with ThreadPoolExecutor(
        max_workers=5
    ) as executor:

        futures = {}

        for _, item in scan_universe_put.iterrows():

            future = executor.submit(
                scan_stock_put_ratio,
                item,
                expiry,
                delta_ranges,
                debit_range,
                credit_range,
                access_token,
                buy_qty,
                sell_qty,
                ratio_name
            )

            futures[future] = item["symbol"]

        completed = 0

        for future in as_completed(
            futures
        ):

            completed += 1

            progress_put.progress(
                completed / total_stocks
            )

            try:

                output = future.result()

                if output:
                    results_put.extend(
                        output
                    )

            except Exception:
                pass

    progress_put.empty()

    if not results_put:

        st.warning(
            f"No matching PUT {ratio_name} setups found."
        )

    else:

        results_put.sort(
            key=lambda x: (
                0
                if x["side"] == "CREDIT"
                else 1,
                -x["total_amount"]
            )
        )

        st.success(
            f"Found {len(results_put)} matching PUT {ratio_name} setups."
        )

        for r in results_put:

            if r["side"] == "CREDIT":

                card_class = "credit-card"

                net_text = (
                    f"CREDIT ₹{r['total_amount']:,.2f}"
                )

            else:

                card_class = "debit-card"

                net_text = (
                    f"DEBIT ₹{r['total_amount']:,.2f}"
                )

            result_html_put = f"""
<div class="result-card {card_class}">

<div class="stock-title">
{r["symbol"]}
</div>

<div class="big-value">
BUY {r["buy_qty"]} PE:
{r["buy_strike"]:g}
@ ₹{r["buy_ltp"]:.2f}
</div>

<div class="small-line">
Delta: <b>{r["delta"]:.2f}</b>
</div>

<div class="big-value">
SELL {r["sell_qty"]} PE:
{r["sell_strike"]:g}
@ ₹{r["sell_ltp"]:.2f}
</div>

<div class="big-value">
{net_text}
</div>

<div class="small-line">
Gap: <b>{r["gap"]:g}</b>
&nbsp;&nbsp; | &nbsp;&nbsp;
Lot: <b>{r["lot_size"]}</b>
</div>

<div class="section-title">
PUT {r["ratio_name"]} Supporting Spread
</div>

<div class="small-line">
A: <b>{r["support_a"]:g}</b>
@ ₹{r["support_a_ltp"]:.2f}
&nbsp; → &nbsp;
B: <b>{r["support_b"]:g}</b>
@ ₹{r["support_b_ltp"]:.2f}
</div>

<div class="small-line">
A &gt;
({r["sell_qty"]}/{r["buy_qty"]}) × B
&nbsp; | &nbsp;
Ratio: <b>{r["ratio"]:.2f}x</b>
&nbsp; | &nbsp;
Difference:
<b>₹{r["difference"]:.2f}</b>
</div>

<div class="small-line">
<b>PUT {r["ratio_name"]} Ratio</b>
</div>

</div>
"""

            st.markdown(
                result_html_put,
                unsafe_allow_html=True
            )
# =========================================================
# CE - PRICE GAP IN %
# NEW ADD-ON ONLY
# EXISTING PROJECT A PRO CODE REMAINS UNTOUCHED
# =========================================================


# =========================================================
# PRICE GAP PARSER
# =========================================================

def parse_price_gap_percent_ce(text):

    text = str(text).strip().replace(" ", "")

    if not text:
        raise ValueError(
            "Price Gap in % cannot be empty."
        )

    values = []

    # Allow one or multiple values:
    # 5
    # 5,10
    # 1,1.5,2,2.5
    for value in text.split(","):

        try:
            number = float(value)
        except Exception:
            raise ValueError(
                "Invalid Price Gap %. Use values like 5, 5.5 or 5,10,15."
            )

        if number <= 0 or number > 25:
            raise ValueError(
                "Price Gap % must be between 0.5% and 25%."
            )

        values.append(number)

    return sorted(set(values))


# =========================================================
# NORMALIZE DELTA
# =========================================================

def normalize_delta_ranges_ce(delta_ranges):

    normalized = []

    for low, high in delta_ranges:

        low = float(low)
        high = float(high)

        # Allow 0.30 = 30%
        # Existing 30 = 30%
        if high <= 1:
            low *= 100
            high *= 100

        normalized.append(
            (low, high)
        )

    return normalized


# =========================================================
# FIND CE BASE STRIKE BY DELTA
# =========================================================

def find_base_ce_by_delta(
    calls,
    delta_ranges
):

    if not calls:
        return None

    normalized_ranges = normalize_delta_ranges_ce(
        delta_ranges
    )

    candidates = []

    for call in calls:

        delta_percent = abs(
            call["delta"]
        ) * 100

        for low, high in normalized_ranges:

            if low <= delta_percent <= high:

                candidates.append(
                    (
                        abs(
                            delta_percent
                            - ((low + high) / 2)
                        ),
                        call
                    )
                )

                break

    if not candidates:
        return None

    candidates.sort(
        key=lambda x: (
            x[0],
            x[1]["strike"]
        )
    )

    return candidates[0][1]


# =========================================================
# FIND TARGET CE STRIKE
# =========================================================

def find_price_gap_ce_strike(
    calls,
    base_strike,
    cash_price,
    gap_percent
):

    gap_amount = (
        cash_price
        * gap_percent
        / 100
    )

    target_strike = (
        base_strike
        + gap_amount
    )

    # Prefer exact strike
    exact = [
        x for x in calls
        if abs(
            x["strike"]
            - target_strike
        ) < 0.01
    ]

    if exact:
        return exact[0]

    # If exact strike is not available,
    # choose the nearest available higher strike.
    higher = [
        x for x in calls
        if x["strike"] > base_strike
        and x["strike"] >= target_strike
    ]

    if higher:

        higher.sort(
            key=lambda x: (
                x["strike"] - target_strike
            )
        )

        return higher[0]

    return None


# =========================================================
# AMOUNT FILTER
# =========================================================

def amount_passes_price_gap_ce(
    target_net,
    lot_size,
    debit_range,
    credit_range
):

    total = abs(
        target_net * lot_size
    )

    # CREDIT
    if target_net > 0:

        low, high = credit_range

        return (
            low <= total <= high,
            total,
            "CREDIT"
        )

    # DEBIT
    if target_net < 0:

        low, high = debit_range

        return (
            low <= total <= high,
            total,
            "DEBIT"
        )

    # ZERO
    zero_allowed = (
        debit_range[0] <= 0 <= debit_range[1]
        or
        credit_range[0] <= 0 <= credit_range[1]
    )

    return (
        zero_allowed,
        0,
        "ZERO"
    )


# =========================================================
# SCAN ONE STOCK
# =========================================================

def scan_stock_price_gap_ce(
    item,
    expiry,
    delta_ranges,
    debit_range,
    credit_range,
    gap_percentages,
    token,
    buy_qty,
    sell_qty,
    ratio_name
):

    symbol = item["symbol"]
    underlying_key = item["underlying_key"]
    lot_size = int(item["lot_size"])

    try:

        chain = get_option_chain(
            underlying_key,
            expiry,
            token
        )

        if not chain:
            return []

        calls = extract_calls(
            chain
        )

        if len(calls) < 2:
            return []

        # -------------------------------------------------
        # CASH / SPOT PRICE
        # -------------------------------------------------

        cash_price = 0.0

        for row in chain:

            try:

                spot = float(
                    row.get(
                        "underlying_spot_price",
                        0
                    ) or 0
                )

                if spot > 0:

                    cash_price = spot
                    break

            except Exception:
                continue

        if cash_price <= 0:
            return []

        # -------------------------------------------------
        # BASE CE FROM DELTA
        # -------------------------------------------------

        base_ce = find_base_ce_by_delta(
            calls,
            delta_ranges
        )

        if base_ce is None:
            return []

        base_strike = base_ce["strike"]
        base_ltp = base_ce["ltp"]

        base_delta = (
            abs(base_ce["delta"])
            * 100
        )

        results = []

        # -------------------------------------------------
        # EACH PRICE GAP %
        # -------------------------------------------------

        for gap_percent in gap_percentages:

            sell_ce = find_price_gap_ce_strike(
                calls,
                base_strike,
                cash_price,
                gap_percent
            )

            if sell_ce is None:
                continue

            sell_strike = sell_ce["strike"]
            sell_ltp = sell_ce["ltp"]

            # -------------------------------------------------
            # RATIO CALCULATION
            # -------------------------------------------------

            target_net = (
                sell_qty * sell_ltp
                - buy_qty * base_ltp
            )

            passed, total, side = (
                amount_passes_price_gap_ce(
                    target_net,
                    lot_size,
                    debit_range,
                    credit_range
                )
            )

            if not passed:
                continue

            actual_gap_rupees = (
                sell_strike
                - base_strike
            )

            actual_gap_percent = (
                actual_gap_rupees
                / cash_price
                * 100
            )

            results.append({

                "symbol": symbol,
                "expiry": expiry,

                "cash_price": cash_price,

                "gap_percent": gap_percent,
                "actual_gap_rupees": actual_gap_rupees,
                "actual_gap_percent": actual_gap_percent,

                "buy_strike": base_strike,
                "buy_ltp": base_ltp,
                "buy_delta": base_delta,

                "sell_strike": sell_strike,
                "sell_ltp": sell_ltp,

                "buy_qty": buy_qty,
                "sell_qty": sell_qty,

                "ratio_name": ratio_name,

                "target_net": target_net,
                "total_amount": total,
                "side": side,

                "lot_size": lot_size

            })

        return results

    except Exception:

        return []


# =========================================================
# PRICE GAP CE UI
# =========================================================

st.markdown(
    "### CE — Price Gap in %"
)

price_gap_ce_input = st.text_input(
    "Price Gap in %",
    value="5",
    placeholder="5 or 1,1.5,2,2.5..."
)

price_gap_ce_ratio = st.selectbox(
    "Ratio",
    [
        "1:3",
        "3:10",
        "1:4",
        "2:7"
    ],
    index=0
)


# =========================================================
# RATIO QUANTITIES
# =========================================================

price_gap_ce_ratio_map = {

    "1:3": (1, 3),

    "3:10": (3, 10),

    "1:4": (1, 4),

    "2:7": (2, 7)

}

price_gap_ce_buy_qty, price_gap_ce_sell_qty = (
    price_gap_ce_ratio_map[
        price_gap_ce_ratio
    ]
)


# =========================================================
# PRICE GAP CE BUTTON
# =========================================================

price_gap_ce_clicked = st.button(
    "🔍 PRICE GAP IN PERCENTAGE",
    type="primary",
    use_container_width=True
)


# =========================================================
# PRICE GAP CE SCAN
# =========================================================

if price_gap_ce_clicked:

    if not access_token:

        st.error(
            "Please enter your Upstox Access Token."
        )

        st.stop()

    try:

        delta_ranges = parse_delta_range(
            delta_input
        )

        debit_range = parse_amount_range(
            debit_input,
            "Debit"
        )

        credit_range = parse_amount_range(
            credit_input,
            "Credit"
        )

        gap_percentages = (
            parse_price_gap_percent_ce(
                price_gap_ce_input
            )
        )

    except ValueError as e:

        st.error(str(e))
        st.stop()

    scan_universe_price_gap_ce = (
        universe[
            universe["expiry"] == expiry
        ]
        .drop_duplicates(
            subset=["underlying_key"]
        )
        .reset_index(drop=True)
    )

    total_stocks = len(
        scan_universe_price_gap_ce
    )

    st.write(
        f"CE Price Gap {price_gap_ce_ratio} "
        f"Scanning **{total_stocks} stocks...**"
    )

    progress_price_gap_ce = st.progress(
        0
    )

    results_price_gap_ce = []

    with ThreadPoolExecutor(
        max_workers=5
    ) as executor:

        futures = {}

        for _, item in (
            scan_universe_price_gap_ce
            .iterrows()
        ):

            future = executor.submit(
                scan_stock_price_gap_ce,
                item,
                expiry,
                delta_ranges,
                debit_range,
                credit_range,
                gap_percentages,
                access_token,
                price_gap_ce_buy_qty,
                price_gap_ce_sell_qty,
                price_gap_ce_ratio
            )

            futures[future] = item[
                "symbol"
            ]

        completed = 0

        for future in as_completed(
            futures
        ):

            completed += 1

            progress_price_gap_ce.progress(
                completed / total_stocks
            )

            try:

                output = future.result()

                if output:

                    results_price_gap_ce.extend(
                        output
                    )

            except Exception:
                pass

    progress_price_gap_ce.empty()

    # -----------------------------------------------------

# =========================================================
# CE PRICE GAP - PREVIOUS / ONE-GAP CALCULATION
# =========================================================

def get_previous_one_gap_ce_calculation(
    r,
    universe_df,
    expiry_date,
    token
):

    try:

        symbol = r["symbol"]
        current_buy_strike = float(r["buy_strike"])
        current_sell_strike = float(r["sell_strike"])

        current_gap = (
            current_sell_strike
            - current_buy_strike
        )

        if current_gap <= 0:
            return None

        previous_buy_strike = (
            current_buy_strike
            - current_gap
        )

        previous_sell_strike = current_buy_strike

        stock_rows = universe_df[
            universe_df["symbol"].astype(str) == str(symbol)
        ]

        if stock_rows.empty:
            return None

        underlying_key = stock_rows.iloc[0]["underlying_key"]
        lot_size = int(stock_rows.iloc[0]["lot_size"])

        chain = get_option_chain(
            underlying_key,
            expiry_date,
            token
        )

        if not chain:
            return None

        calls = extract_calls(chain)

        if not calls:
            return None

        previous_buy = min(
            calls,
            key=lambda x: abs(
                float(x["strike"]) - previous_buy_strike
            )
        )

        previous_sell = min(
            calls,
            key=lambda x: abs(
                float(x["strike"]) - previous_sell_strike
            )
        )

        if abs(
            float(previous_buy["strike"]) - previous_buy_strike
        ) > 0.01:
            return None

        if abs(
            float(previous_sell["strike"]) - previous_sell_strike
        ) > 0.01:
            return None

        buy_qty = int(r["buy_qty"])
        sell_qty = int(r["sell_qty"])

        buy_ltp = float(previous_buy["ltp"])
        sell_ltp = float(previous_sell["ltp"])

        buy_amount = (
            lot_size
            * buy_ltp
            * buy_qty
        )

        sell_amount = (
            lot_size
            * sell_ltp
            * sell_qty
        )

        net_amount = (
            sell_amount
            - buy_amount
        )

        if net_amount > 0:
            side = "CREDIT"
        elif net_amount < 0:
            side = "DEBIT"
        else:
            side = "ZERO"

        return {
            "buy_strike": float(previous_buy["strike"]),
            "sell_strike": float(previous_sell["strike"]),
            "buy_ltp": buy_ltp,
            "sell_ltp": sell_ltp,
            "buy_qty": buy_qty,
            "sell_qty": sell_qty,
            "lot_size": lot_size,
            "buy_amount": buy_amount,
            "sell_amount": sell_amount,
            "net_amount": net_amount,
            "side": side
        }

    except Exception:
        return None


# =========================================================
# RESULTS — MAIN + PREVIOUS / ONE-GAP
# =========================================================

if price_gap_ce_clicked:

    if not results_price_gap_ce:

        st.warning(
            "No matching CE Price Gap setups found."
        )

    else:

        results_price_gap_ce.sort(
            key=lambda x: (
                0
                if x["side"] == "CREDIT"
                else 1,
                -x["total_amount"]
            )
        )

        st.success(
            f"Found {len(results_price_gap_ce)} "
            f"matching CE Price Gap setups."
        )

        for r in results_price_gap_ce:

            # -------------------------------------------------
            # MAIN
            # -------------------------------------------------

            if r["side"] == "CREDIT":
                card_class = "credit-card"
                net_text = (
                    f"CREDIT ₹{r['total_amount']:,.2f}"
                )
            elif r["side"] == "DEBIT":
                card_class = "debit-card"
                net_text = (
                    f"DEBIT ₹{r['total_amount']:,.2f}"
                )
            else:
                card_class = "credit-card"
                net_text = "ZERO"

            result_html_price_gap_ce = f"""
    <div class="result-card {card_class}">

    <div class="stock-title">
    {r["symbol"]} — Main
    </div>

    <div class="small-line">
    Cash Price:
    <b>₹{r["cash_price"]:.2f}</b>
    </div>

    <div class="big-value">
    BUY {r["buy_qty"]} CE:
    {r["buy_strike"]:g}
    @ ₹{r["buy_ltp"]:.2f}
    </div>

    <div class="small-line">
    Delta:
    <b>{r["buy_delta"]:.2f}</b>
    </div>

    <div class="big-value">
    SELL {r["sell_qty"]} CE:
    {r["sell_strike"]:g}
    @ ₹{r["sell_ltp"]:.2f}
    </div>

    <div class="big-value">
    {net_text}
    </div>

    <div class="small-line">
    Price Gap:
    <b>{r["gap_percent"]:.2f}%</b>
    &nbsp;&nbsp; | &nbsp;&nbsp;
    Actual Gap:
    <b>{r["actual_gap_rupees"]:g}</b>
    </div>

    <div class="small-line">
    Actual Gap %:
    <b>{r["actual_gap_percent"]:.2f}%</b>
    &nbsp;&nbsp; | &nbsp;&nbsp;
    Lot:
    <b>{r["lot_size"]}</b>
    </div>

    <div class="section-title">
    CE Price Gap {r["ratio_name"]}
    </div>

    <div class="small-line">
    BUY {r["buy_qty"]} CE
    &nbsp; → &nbsp;
    SELL {r["sell_qty"]} CE
    </div>

    <div class="small-line">
    Target Net:
    <b>₹{r["target_net"]:.2f}</b>
    &nbsp; | &nbsp;
    Ratio:
    <b>{r["ratio_name"]}</b>
    </div>

    </div>
    """

            st.markdown(
                result_html_price_gap_ce,
                unsafe_allow_html=True
            )

            # -------------------------------------------------
            # PREVIOUS / ONE-GAP
            # -------------------------------------------------

            previous_trade = get_previous_one_gap_ce_calculation(
                r,
                universe,
                expiry,
                access_token
            )

            if previous_trade is not None:

                p = previous_trade

                if p["side"] == "DEBIT":
                    previous_card_class = "debit-card"
                    previous_net_text = (
                        f"DEBIT ₹{abs(p['net_amount']):,.2f}"
                    )
                elif p["side"] == "CREDIT":
                    previous_card_class = "credit-card"
                    previous_net_text = (
                        f"CREDIT ₹{abs(p['net_amount']):,.2f}"
                    )
                else:
                    previous_card_class = "credit-card"
                    previous_net_text = "ZERO ₹0.00"

                previous_html = f"""
    <div class="result-card {previous_card_class}">

    <div class="stock-title">
    {r["symbol"]} — Previous / One-Gap
    </div>

    <div class="small-line">
    BUY {p["buy_qty"]} CE:
    <b>{p["buy_strike"]:g}</b>
    @ ₹{p["buy_ltp"]:.2f}
    </div>

    <div class="small-line">
    {p["lot_size"]} × ₹{p["buy_ltp"]:.2f} × {p["buy_qty"]}
    =
    <b>₹{p["buy_amount"]:,.2f}</b>
    </div>

    <br>

    <div class="small-line">
    SELL {p["sell_qty"]} CE:
    <b>{p["sell_strike"]:g}</b>
    @ ₹{p["sell_ltp"]:.2f}
    </div>

    <div class="small-line">
    {p["lot_size"]} × ₹{p["sell_ltp"]:.2f} × {p["sell_qty"]}
    =
    <b>₹{p["sell_amount"]:,.2f}</b>
    </div>

    <br>

    <div class="big-value">
    {previous_net_text}
    </div>

    <div class="small-line">
    SELL ₹{p["sell_amount"]:,.2f}
    &nbsp; − &nbsp;
    BUY ₹{p["buy_amount"]:,.2f}
    =
    <b>{previous_net_text}</b>
    </div>

    <div class="small-line">
    Ratio:
    <b>{r["ratio_name"]}</b>
    &nbsp;&nbsp; | &nbsp;&nbsp;
    Lot Size:
    <b>{p["lot_size"]}</b>
    </div>

    </div>
    """

                st.markdown(
                    previous_html,
                    unsafe_allow_html=True
                )

# =========================================================
# PROJECT A PRO — V1 UPGRADE LAYER
# IMPORTANT: Existing Project A scanner/engine above is preserved.
# Margin is ONLY a value in the Main Result Card; no Margin Feed.
# =========================================================

st.markdown("---")
st.header("🚀 Project A Pro")
st.caption("Pro controls and result-card upgrade layer. Existing Project A engine remains protected above.")

# One ratio selector — no separate ratio buttons.
pro_ratio = st.radio(
    "Ratio Selection",
    ["1:3", "3:10", "1:4"],
    horizontal=True,
    key="pro_ratio_selection"
)

c1, c2, c3 = st.columns(3)
with c1:
    pro_option = st.radio("Option Type", ["CE", "PE"], horizontal=True, key="pro_option_type")
with c2:
    pro_scanner = st.radio("Auto Scan Scanner", ["Debit ₹0 Scanner", "% Gap Scanner"], horizontal=True, key="pro_scanner_type")
with c3:
    pro_gap = st.number_input("Gap %", min_value=0.0, max_value=100.0, value=0.0, step=0.5, key="pro_gap_percent")

c4, c5 = st.columns(2)
with c4:
    pro_debit = st.number_input("Spread Cost — Debit ₹", min_value=0.0, value=0.0, step=50.0, key="pro_debit_amount")
with c5:
    pro_credit = st.number_input("Spread Cost — Credit ₹", min_value=0.0, value=0.0, step=50.0, key="pro_credit_amount")

c6, c7, c8 = st.columns(3)
with c6:
    st.write("**Option Premium Spike**")
with c7:
    pro_spike = st.number_input("%", min_value=0.0, max_value=100.0, value=0.0, step=0.5, key="pro_spike_percent")
with c8:
    pro_spike_mode = st.radio("Mode", ["Auto", "Manual", "Scan"], horizontal=True, key="pro_spike_mode")

st.info("Main Result Card: Company + Delta + Lot Size + Buy/Sell strikes & LTP + Debit/Credit + Result Date + Margin. No separate Margin Feed.")

# The existing scan results are reused when available. This does not alter the old scan engine.
pro_results = []
for _name in ("results", "results_3_10", "results_1_4"):
    _value = globals().get(_name)
    if isinstance(_value, list) and _value:
        pro_results = _value
        break

if pro_results:
    st.subheader("Scan Results")
    st.caption("ક્રમ હાલના scanner દ્વારા મળેલા ક્રમ પ્રમાણે જ રહેશે; scanner logic બદલ્યું નથી.")

    # Display-only helpers: read optional metadata if already supplied by the engine.
    def _display_value(value, prefix=""):
        if value is None or value == "":
            return "—"
        try:
            return f"{prefix}{float(value):,.2f}"
        except (TypeError, ValueError):
            return str(value)

    for r in pro_results:
        side = str(r.get("side", "")).upper()
        amount = r.get("total_amount", r.get("net_amount", 0))
        net_text = f"{side} ₹{_display_value(amount)}" if side else _display_value(amount, "₹")
        company = str(r.get("symbol", "—"))
        delta = _display_value(r.get("delta"))
        lot = _display_value(r.get("lot_size"))
        buy_strike = _display_value(r.get("buy_strike"))
        buy_ltp = _display_value(r.get("buy_ltp"), "₹")
        sell_strike = _display_value(r.get("sell_strike"))
        sell_ltp = _display_value(r.get("sell_ltp"), "₹")
        # Never substitute expiry for Result Date. Only show a genuine result-date field.
        result_date = r.get("result_date", r.get("res_date", "")) or "—"
        # Highlight only when an existing upstream field explicitly marks the symbol as banned.
        is_banned = bool(r.get("is_banned", r.get("fo_ban", r.get("ban_status", False))))
        if isinstance(r.get("ban_status"), str):
            is_banned = r.get("ban_status", "").strip().lower() in ("ban", "banned", "yes", "true")
        card_border = "#dc2626" if is_banned else "#64748b"
        card_bg = "#fff1f2" if is_banned else "#f8fafc"
        ban_badge = "<span class='pro-ban-badge'>NSE F&amp;O BAN</span>" if is_banned else ""

        st.markdown(f"""
        <style>
        .pro-company-card {{border:1px solid {card_border};background:{card_bg};border-radius:10px;padding:9px;margin:8px 0;color:#111827;}}
        .pro-line {{display:grid;grid-template-columns:repeat(9,minmax(75px,1fr));gap:5px;align-items:center;border-bottom:1px solid #cbd5e1;padding:7px 2px;font-size:12px;}}
        .pro-line:last-child {{border-bottom:0;}}
        .pro-line-label {{font-weight:800;color:#334155;background:#e2e8f0;border-radius:5px;padding:5px;}}
        .pro-line-value {{font-weight:650;overflow-wrap:anywhere;}}
        .pro-row-title {{font-weight:800;min-width:75px;color:#1e3a8a;}}
        .pro-ban-badge {{display:inline-block;background:#b91c1c;color:white;padding:3px 7px;border-radius:5px;font-weight:800;font-size:10px;margin-left:6px;}}
        @media(max-width:700px) {{.pro-line {{grid-template-columns:repeat(3,minmax(0,1fr));}} .pro-line-label:first-child {{grid-column:1/-1;}}}}
        </style>
        <div class='pro-company-card'>
          <div class='pro-line pro-line-label'><span>Company</span><span>Delta</span><span>Lot Size</span><span>Buy Strike</span><span>Buy Price</span><span>Sell Strike</span><span>Sell Price</span><span>Debit/Credit</span><span>Result Date</span></div>
          <div class='pro-line pro-line-value'><span>{company} {ban_badge}</span><span>{delta}</span><span>{lot}</span><span>{buy_strike}</span><span>{buy_ltp}</span><span>{sell_strike}</span><span>{sell_ltp}</span><span>{net_text}</span><span>{result_date}</span></div>
          <div class='pro-line'><span class='pro-row-title'>Review-1</span><span>Strike: {_display_value(r.get('support_a'))} → {_display_value(r.get('support_b'))}</span><span>Price: {_display_value(r.get('support_a_ltp'), '₹')} → {_display_value(r.get('support_b_ltp'), '₹')}</span><span>Debit/Credit: —</span><span>Result Date: {result_date}</span></div>
          <div class='pro-line'><span class='pro-row-title'>Review-2</span><span>Strike: {_display_value(r.get('review2_buy_strike'))} → {_display_value(r.get('review2_sell_strike'))}</span><span>Price: {_display_value(r.get('review2_buy_ltp'), '₹')} → {_display_value(r.get('review2_sell_ltp'), '₹')}</span><span>Debit/Credit: —</span><span>Result Date: {result_date}</span></div>
        </div>
        """, unsafe_allow_html=True)
else:
    st.caption("No scan result is available yet. Run the existing Project A scanner above to populate the Pro result-card layer.")
