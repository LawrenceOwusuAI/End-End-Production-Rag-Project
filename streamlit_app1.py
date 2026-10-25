import os
import re
import uuid
from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd
import requests
import streamlit as st

BASE_API_URL = os.getenv("BASE_API_URL","http://rag-backend:8000")
OBSERVABILITY_BASE_URL = os.getenv("OBSERVABILITY_BASE_URL","http://127.0.0.1:8003")
API_URL = f"{BASE_API_URL}/query"
DOCUMENTS_API_URL = f"{BASE_API_URL}/documents"
REGISTER_API_URL = f"{BASE_API_URL}/auth/register"
LOGIN_API_URL = f"{BASE_API_URL}/auth/login"
ME_API_URL = f"{BASE_API_URL}/auth/me"
WEATHER_BASE_URL = os.getenv("WEATHER_API_URL", "http://ghana-weather-api:8085").rstrip("/")
WEATHER_CHAT_API_URL = f"{WEATHER_BASE_URL}/api/v1/chat"

# OBSERVABILITY AGENT BACKEND
OBSERVABILITY_BASE_URL = os.getenv("OBSERVABILITY_BASE_URL","http://127.0.0.1:8003")
OBSERVABILITY_API_URL = f"{OBSERVABILITY_BASE_URL}/observe"
OBSERVABILITY_HEALTH_URL = f"{OBSERVABILITY_BASE_URL}/health"

# PAGE CONFIGURATION
st.set_page_config(page_title=
       "AI Research Assistant",
       page_icon="🤖",
       layout="wide",
       initial_sidebar_state="expanded",
)

# SESSION STATE
if "access_token" not in st.session_state:
    st.session_state["access_token"] = None
if "user" not in st.session_state:
    st.session_state["user"] = None
if "observability_messages" not in st.session_state:
    st.session_state["observability_messages"] = []
if "weather_messages" not in st.session_state:
    st.session_state["weather_messages"] = []
if "weather_conversation_id" not in st.session_state:
    st.session_state["weather_conversation_id"] = None

if "weather_forecast_data" not in st.session_state:
    st.session_state["weather_forecast_data"] = None
if "weather_location_name" not in st.session_state:
    st.session_state["weather_location_name"] = None
if "weather_pending_prompt" not in st.session_state:
    st.session_state["weather_pending_prompt"] = None

# CUSTOM CSS
st.markdown(
    """
<style>
.stApp {

    background:

        radial-gradient(
            circle at 10% 10%,
            rgba(91, 124, 250, 0.13),
            transparent 30%
        ),

        radial-gradient(
            circle at 90% 15%,
            rgba(151, 117, 250, 0.10),
            transparent 28%
        ),

        linear-gradient(
            135deg,
            #edf4fb 0%,
            #e6eef8 45%,
            #edf1f8 100%
        );

    color:
        #172033;
}

.block-container {

    max-width:
        1100px;

    padding-top:
        2rem;

    padding-bottom:
        4rem;
}


header[data-testid="stHeader"] {

    background:
        transparent;
}

.main-title {

    text-align:
        center;

    font-size:
        3.2rem;

    font-weight:
        800;

    margin-bottom:
        0.4rem;

    background:
        linear-gradient(
            90deg,
            #304ffe,
            #5f3dc4,
            #7048e8
        );

    -webkit-background-clip:
        text;

    -webkit-text-fill-color:
        transparent;
}


.subtitle {

    text-align:
        center;

    color:
        #526375;

    font-size:
        1.05rem;

    margin-bottom:
        1rem;
}

.status-box {

    text-align:
        center;

    margin-bottom:
        2rem;

    color:
        #526375;

    font-size:
        0.92rem;

    font-weight:
        500;
}


.status-dot {

    display:
        inline-block;

    width:
        9px;

    height:
        9px;

    border-radius:
        50%;

    background:
        #2f9e44;

    margin-right:
        7px;

    box-shadow:
        0 0 8px
        rgba(47, 158, 68, 0.50);
}

.section-card {

    background:
        rgba(
            255,
            255,
            255,
            0.88
        );

    border:
        1px solid #d9e2ec;

    border-radius:
        20px;

    padding:
        20px 24px;

    margin-top:
        1rem;

    margin-bottom:
        1rem;

    box-shadow:
        0 10px 30px
        rgba(30, 50, 80, 0.08);
}


.section-title {

    color:
        #172033;

    font-size:
        1.35rem;

    font-weight:
        700;

    margin-bottom:
        5px;
}


.section-description {

    color:
        #536273;

    font-size:
        0.95rem;

    line-height:
        1.6;
}


.stMarkdown,
.stCaption {

    color:
        #26364a;
}

button[data-baseweb="tab"] {

    font-size:
        1rem;

    font-weight:
        700;

    color:
        #344054;
}


button[data-baseweb="tab"][aria-selected="true"] {

    color:
        #4338ca;
}


[data-testid="stFileUploader"] {

    background:
        #ffffff;

    border:
        1px solid #d7e0ea;

    border-radius:
        16px;

    padding:
        15px;
}


[data-testid="stFileUploader"] label {

    color:
        #172033 !important;
}


[data-testid="stFileUploader"] section {

    background:
        #f8fafc !important;

    border:
        1px dashed #9fb1c5 !important;

    border-radius:
        12px !important;
}


[data-testid="stFileUploader"] section div {

    color:
        #26364a !important;
}

.stTextInput input {

    background-color:
        #ffffff !important;

    color:
        #172033 !important;

    border-radius:
        12px !important;

    border:
        1px solid #cbd6e2 !important;
}

.stTextArea textarea {

    background-color:
        #ffffff !important;

    color:
        #172033 !important;

    border-radius:
        15px !important;

    border:
        1px solid #cbd6e2 !important;

    font-size:
        1rem !important;

    min-height:
        125px !important;

    padding:
        16px !important;

    box-shadow:
        0 4px 15px
        rgba(30, 50, 80, 0.05) !important;
}


.stTextArea textarea:focus {

    border:
        1px solid #5c7cfa !important;

    box-shadow:
        0 0 0 2px
        rgba(92, 124, 250, 0.15) !important;
}


.stTextArea textarea::placeholder {

    color:
        #8291a3 !important;

    opacity:
        1 !important;
}

.stButton button,
div[data-testid="stFormSubmitButton"] button {

    width:
        100%;

    height:
        3rem;

    border:
        none !important;

    border-radius:
        12px !important;

    font-size:
        1rem !important;

    font-weight:
        700 !important;

    color:
        white !important;

    background:
        linear-gradient(
            90deg,
            #4263eb,
            #6741d9
        ) !important;

    box-shadow:
        0 6px 18px
        rgba(66, 99, 235, 0.20);

    transition:
        all 0.2s ease;
}


.stButton button:hover,
div[data-testid="stFormSubmitButton"] button:hover {

    transform:
        translateY(-1px);

    box-shadow:
        0 10px 24px
        rgba(66, 99, 235, 0.28);
}


.stButton button p,
div[data-testid="stFormSubmitButton"] button p {

    color:
        white !important;
}

[data-testid="stChatMessage"] {

    background:
        #ffffff !important;

    border:
        1px solid #d7e0ea !important;

    border-radius:
        18px !important;

    padding:
        16px !important;

    margin-top:
        12px !important;

    margin-bottom:
        14px !important;

    box-shadow:
        0 6px 20px
        rgba(30, 50, 80, 0.07) !important;
}


[data-testid="stChatMessage"] p,
[data-testid="stChatMessage"] span,
[data-testid="stChatMessage"] li {

    color:
        #1c2735 !important;

    font-size:
        1rem !important;

    line-height:
        1.75 !important;
}


[data-testid="stChatMessage"]
[data-testid="stMarkdownContainer"] {

    color:
        #1c2735 !important;
}


[data-testid="stChatMessage"] h1,
[data-testid="stChatMessage"] h2,
[data-testid="stChatMessage"] h3,
[data-testid="stChatMessage"] h4 {

    color:
        #172033 !important;
}


[data-testid="stChatMessage"] strong {

    color:
        #111827 !important;

    font-weight:
        700 !important;
}


[data-testid="stChatMessage"] a {

    color:
        #364fc7 !important;

    font-weight:
        600;
}


[data-testid="stChatMessage"] code {

    color:
        #b42318 !important;

    background:
        #f2f4f7 !important;

    padding:
        2px 5px;

    border-radius:
        5px;
}

[data-testid="stMetric"] {

    background:
        rgba(
            255,
            255,
            255,
            0.90
        );

    border:
        1px solid #d7e0ea;

    padding:
        14px;

    border-radius:
        14px;
}

[data-testid="stCaptionContainer"] p {

    color:
        #617285 !important;
}


[data-testid="stSpinner"] {

    color:
        #253858 !important;
}

[data-testid="stForm"] {

    background:
        rgba(
            255,
            255,
            255,
            0.30
        );

    border:
        1px solid
        rgba(
            190,
            205,
            220,
            0.55
        );

    border-radius:
        18px;

    padding:
        14px;
}

.observability-info {

    background:
        rgba(
            238,
            242,
            255,
            0.95
        );

    border:
        1px solid #c7d2fe;

    border-radius:
        16px;

    padding:
        18px;

    margin-top:
        1rem;

    margin-bottom:
        1rem;

    color:
        #312e81;
}


.observability-info strong {

    color:
        #312e81;
}

footer {

    visibility:
        hidden;
}


/* ========================================================
   PROFESSIONAL PROFILE / PORTFOLIO TAB
   ======================================================== */
.profile-hero {
    background: linear-gradient(135deg, rgba(255,255,255,0.98), rgba(238,242,255,0.95));
    border: 1px solid #d9e2ec;
    border-radius: 24px;
    padding: 30px;
    margin: 1rem 0 1.5rem 0;
    box-shadow: 0 14px 38px rgba(30, 50, 80, 0.10);
}

.profile-name {
    color: #172033;
    font-size: 2.2rem;
    font-weight: 800;
    margin-bottom: 0.2rem;
}

.profile-role {
    color: #4338ca;
    font-size: 1.12rem;
    font-weight: 750;
    margin-bottom: 1rem;
}

.profile-summary {
    color: #405166;
    font-size: 1rem;
    line-height: 1.75;
}

.badge-wrap {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    margin-top: 14px;
}

.skill-badge {
    display: inline-block;
    background: #eef2ff;
    color: #3730a3;
    border: 1px solid #c7d2fe;
    border-radius: 999px;
    padding: 7px 12px;
    font-size: 0.88rem;
    font-weight: 700;
}

.portfolio-card {
    background: rgba(255,255,255,0.94);
    border: 1px solid #d9e2ec;
    border-radius: 18px;
    padding: 20px;
    margin: 0.7rem 0;
    box-shadow: 0 8px 22px rgba(30, 50, 80, 0.06);
}

.portfolio-card h3 {
    color: #172033;
    margin-top: 0;
    margin-bottom: 0.55rem;
}

.portfolio-card p,
.portfolio-card li {
    color: #46576a;
    line-height: 1.7;
}

.portfolio-card a {
    color: #364fc7 !important;
    font-weight: 700;
    text-decoration: none;
}

.portfolio-card a:hover {
    text-decoration: underline;
}

.highlight-number {
    font-size: 1.8rem;
    font-weight: 800;
    color: #4338ca;
}

.highlight-label {
    color: #607085;
    font-size: 0.9rem;
}

</style>
""",

    unsafe_allow_html=True,
)


# REGISTER USER
def register_user(full_name,email,password,):
    try:
        response = requests.post(
            REGISTER_API_URL,
            json={"full_name":full_name,
                "email":email,
                "password":password,
            },
            timeout= 15,
        )
        return response
    except requests.RequestException:
        return None

# LOGIN USER
def login_user(email,password):
    try:
        response = requests.post(
            LOGIN_API_URL,
            json={
                "email":email,
                "password":password,
            },
            timeout=15,
        )
        return response
    except requests.RequestException:
        return None

# WEATHER AGENT CLIENT - REUSES THE RAG LOGIN JWT
def ask_weather_agent(message: str, conversation_id=None):
    token = st.session_state.get("access_token")
    if not token:
        raise RuntimeError("Your session has expired. Please log in again.")

    payload = {"message": message}
    if conversation_id:
        payload["conversation_id"] = conversation_id

    response = requests.post(
        WEATHER_CHAT_API_URL,
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
        timeout=90,
    )
    if response.status_code == 401:
        raise RuntimeError("Your session has expired. Please log in again.")
    response.raise_for_status()
    return response.json()


# WEATHER FORECAST HELPERS FROM THE ORIGINAL GHANA WEATHER INTELLIGENCE APP
GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
GHANA_TIMEZONE = "Africa/Accra"

WEATHER_CODES = {
    0: ("☀️", "Clear sky"),
    1: ("🌤️", "Mainly clear"),
    2: ("⛅", "Partly cloudy"),
    3: ("☁️", "Overcast"),
    45: ("🌫️", "Fog"),
    48: ("🌫️", "Depositing rime fog"),
    51: ("🌦️", "Light drizzle"),
    53: ("🌦️", "Moderate drizzle"),
    55: ("🌧️", "Dense drizzle"),
    56: ("🌧️", "Light freezing drizzle"),
    57: ("🌧️", "Dense freezing drizzle"),
    61: ("🌦️", "Slight rain"),
    63: ("🌧️", "Moderate rain"),
    65: ("🌧️", "Heavy rain"),
    66: ("🌧️", "Light freezing rain"),
    67: ("🌧️", "Heavy freezing rain"),
    71: ("🌨️", "Slight snow"),
    73: ("🌨️", "Moderate snow"),
    75: ("❄️", "Heavy snow"),
    77: ("❄️", "Snow grains"),
    80: ("🌦️", "Slight rain showers"),
    81: ("🌧️", "Moderate rain showers"),
    82: ("⛈️", "Violent rain showers"),
    85: ("🌨️", "Slight snow showers"),
    86: ("🌨️", "Heavy snow showers"),
    95: ("⛈️", "Thunderstorm"),
    96: ("⛈️", "Thunderstorm with slight hail"),
    99: ("⛈️", "Thunderstorm with heavy hail"),
}


def describe_weather(code):
    try:
        return WEATHER_CODES.get(
            int(code),
            ("🌤️", "Unknown"),
        )
    except (ValueError, TypeError):
        return ("🌤️", "Unavailable")


# ============================================================
# 5. GEOCODING
# ============================================================

@st.cache_data(ttl=86400, show_spinner=False)
def get_coordinates(city):
    response = requests.get(
        GEOCODING_URL,
        params={
            "name": city,
            "count": 20,
            "language": "en",
            "format": "json",
            "countryCode": "GH",
        },
        timeout=20,
    )

    response.raise_for_status()

    results = response.json().get("results", [])

    if not results:
        raise ValueError(
            f"Could not find '{city}' in Ghana."
        )

    # Prefer a populated match; do not silently
    # select a different country.
    results.sort(
        key=lambda item: item.get("population") or 0,
        reverse=True,
    )

    return results[0]


# ============================================================
# 6. HOURLY WEATHER API
# ============================================================

@st.cache_data(ttl=900, show_spinner=False)
def get_hourly_forecast(
    latitude,
    longitude,
    forecast_days,
):
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "timezone": GHANA_TIMEZONE,
        "forecast_days": forecast_days,
        "current": [
            "temperature_2m",
            "relative_humidity_2m",
            "apparent_temperature",
            "precipitation",
            "rain",
            "weather_code",
            "wind_speed_10m",
        ],
        "hourly": [
            "temperature_2m",
            "apparent_temperature",
            "relative_humidity_2m",
            "precipitation_probability",
            "precipitation",
            "rain",
            "showers",
            "weather_code",
            "cloud_cover",
            "wind_speed_10m",
            "wind_gusts_10m",
        ],
        "daily": [
            "weather_code",
            "temperature_2m_max",
            "temperature_2m_min",
            "precipitation_sum",
            "precipitation_probability_max",
            "wind_speed_10m_max",
        ],
    }

    response = requests.get(
        FORECAST_URL,
        params=params,
        timeout=30,
    )

    response.raise_for_status()

    return response.json()


# ============================================================
# 7. DATAFRAME PREPARATION
# ============================================================

def prepare_hourly_dataframe(data):
    hourly = data.get("hourly", {})

    df = pd.DataFrame(hourly)

    if df.empty:
        return df

    df["time"] = pd.to_datetime(df["time"])
    df["date"] = df["time"].dt.date
    df["hour"] = df["time"].dt.strftime("%I:%M %p")

    df["condition"] = df["weather_code"].apply(
        lambda code: " ".join(
            describe_weather(code)
        )
    )

    return df


def prepare_daily_dataframe(data):
    daily = data.get("daily", {})

    df = pd.DataFrame(daily)

    if df.empty:
        return df

    df["time"] = pd.to_datetime(
        df["time"]
    ).dt.date

    df["condition"] = df["weather_code"].apply(
        lambda code: " ".join(
            describe_weather(code)
        )
    )

    return df


# ============================================================
# 8. AI AGENT COMMUNICATION
# ============================================================

# ============================================================
# 9. FORMAT AI ANSWERS WITH WEATHER ICONS
# ============================================================

WEATHER_LABELS = [
    (
        r"rain probability|precipitation probability|"
        r"chance of rain",
        "🌧️",
    ),
    (
        r"rainfall|precipitation amount",
        "💧",
    ),
    (
        r"humidity",
        "💦",
    ),
    (
        r"wind|gust",
        "💨",
    ),
    (
        r"temperature|max temp|min temp|feels.like",
        "🌡️",
    ),
    (
        r"condition|weather",
        "🌤️",
    ),
]


def format_ai_answer(answer):
    lines = []

    for line in answer.splitlines():
        stripped = line.strip()

        if not stripped:
            lines.append("")
            continue

        # Handle Markdown list items.
        match = re.match(
            r"^(\s*(?:[-*]\s+|\d+\.\s+)?)(.*)$",
            line,
        )

        if not match:
            lines.append(line)
            continue

        prefix, content = match.groups()

        plain = content.replace("**", "").strip()
        label = plain.split(":", 1)[0]

        if len(label) > 65:
            lines.append(line)
            continue

        icon = None

        for pattern, symbol in WEATHER_LABELS:
            if re.search(
                pattern,
                label,
                re.IGNORECASE,
            ):
                icon = symbol
                break

        if icon:
            lines.append(
                f"{prefix}{icon} {content}"
            )
        else:
            lines.append(line)

    return "\n".join(lines)




# Scoped weather dashboard styling (preserves existing RAG theme)
st.markdown("""<style>
.ghana-weather-hero {background:linear-gradient(115deg,#dbeafe,#dcfce7);padding:28px 32px;border-radius:20px;border:1px solid #bfdbfe;margin-bottom:20px;}
.ghana-weather-hero h1 {color:#075985;font-size:2.2rem;font-weight:800;margin:0;}
.ghana-weather-hero p {color:#334155;margin-top:10px;}
</style>""",unsafe_allow_html=True)

# AUTHENTICATION PAGE
if not st.session_state["access_token"]:
    st.markdown(
        """
<div class="main-title">
AI Research Assistant
</div>
        """,

        unsafe_allow_html=True,
    )


    st.markdown(
        """
<div class="subtitle">

Sign in or create an account
to access your research assistant.

</div>
        """,

        unsafe_allow_html=True,
    )


    login_tab, register_tab = (
        st.tabs(
            [
                "🔐 Login",
                "👤 Create Account",
            ]
        )
    )

    # LOGIN TAB
    with login_tab:
        st.subheader("Welcome Back")
        with st.form("login_form"):
            login_email = st.text_input("Email Address",key="login_email",)
            login_password = st.text_input("Password",
                    type="password",
                    key="login_password")
            
            login_button = (
                st.form_submit_button(

                    "Login",

                    use_container_width=
                        True,
                )
            )


        if login_button:

            response = login_user(

                login_email,

                login_password,
            )


            if response is None:

                st.error(
                    "Unable to connect "
                    "to the authentication server."
                )


            elif (
                response.status_code
                ==
                200
            ):

                data = (
                    response.json()
                )


                st.session_state[
                    "access_token"
                ] = (
                    data[
                        "access_token"
                    ]
                )


                st.session_state[
                    "user"
                ] = (
                    data[
                        "user"
                    ]
                )


                st.rerun()


            else:

                try:

                    message = (

                        response
                        .json()
                        .get(
                            "detail",
                            "Login failed.",
                        )
                    )


                except Exception:

                    message = (
                        "Login failed."
                    )


                st.error(
                    message
                )

    # REGISTER TAB
   
    with register_tab:

        st.subheader("Create Your Account")

        with st.form("registration_form"):

            full_name = (
                st.text_input(
                    "Full Name",
                    key="register_full_name",
                )
            )

            register_email = (
                st.text_input(
                    "Email Address",
                    key="register_email",
                )
            )

            register_password = (
                st.text_input(
                    "Password",
                    type="password",
                    key="register_password"
                )
            )

            confirm_password = st.text_input(
                    "Confirm Password",
                    type="password",
                    key="confirm_password",
                )
            
            register_button = st.form_submit_button(
                    "Create Account",
                    use_container_width=True
                )
            
        if register_button:

            if not full_name.strip():

                st.error("Please enter your full name.")

            elif not register_email.strip():

                st.error("Please enter your email.")

            elif register_password != confirm_password:

                st.error("Passwords do not match.")

            elif len(register_password) < 8:

                st.error("Password must contain at least 8 characters.")

            else:

                response = register_user(
                        full_name,

                        register_email,

                        register_password,
                    )
                
                if response is None:

                    st.error("Unable to connect to the authentication server.")

                elif response.status_code == 201:

                    st.success("Account created successfully. Please log in.")

                else:

                    try:

                        message = response.json().get(
                                "detail",
                                "Registration failed.",
                            )
                        
                    except Exception:

                        message = ("Registration failed.")

                    st.error(message)

    # Stop rendering authenticated application
    st.stop()

# AUTHENTICATED USER
current_user = st.session_state["user"]


# SIDEBAR
with st.sidebar:

    st.markdown("### 👤 Account")

    st.write(current_user["full_name"])

    st.caption(current_user["email"])

    st.divider()

    st.markdown("### 🔗 Services")

    st.caption(f"RAG Backend:\n{BASE_API_URL}")

    st.caption(
        "Observability Agent:\n"
        f"{OBSERVABILITY_BASE_URL}"
    )

    st.divider()

    if st.button(

        "🚪 Logout",

        key="sidebar_logout_button",

        use_container_width=True):

        st.session_state["access_token"] = None

        st.session_state["user"] = None

        st.session_state["observability_messages"] = []
        st.session_state["weather_messages"] = []
        st.session_state["weather_conversation_id"] = None
        st.session_state["weather_forecast_data"] = None
        st.session_state["weather_location_name"] = None
        st.session_state["weather_pending_prompt"] = None

        st.rerun()

    st.divider()
    with st.expander("🇬🇭 Ghana Weather · Location & Forecast", expanded=True):
        weather_cities = ["Accra", "Kumasi", "Tamale", "Takoradi", "Cape Coast",
            "Koforidua", "Ho", "Sunyani", "Bolgatanga", "Wa", "Tema",
            "Obuasi", "Techiman", "Akim Oda", "Paga", "Other location"]
        weather_selected_city = st.selectbox("📍 Select a location", weather_cities, key="weather_selected_city")
        weather_custom_city = ""
        if weather_selected_city == "Other location":
            weather_custom_city = st.text_input("Enter a town or city in Ghana",
                placeholder="e.g. Tarkwa, Nsawam", key="weather_custom_city")
        weather_location = (weather_custom_city.strip() if weather_selected_city == "Other location"
            else weather_selected_city)
        weather_forecast_days = st.slider("📅 Forecast duration (days)", 1, 10, 3,
            key="weather_forecast_days")
        weather_get_forecast = st.button("🌤️ Get hourly forecast",
            use_container_width=True, type="primary", key="weather_get_forecast")

# HEADER

st.markdown(
    """
<div class="main-title">
AI Research Assistant
</div>
    """,

    unsafe_allow_html=True,
)


st.markdown(
    """
<div class="subtitle">

Query your documents and monitor the health,
metrics, logs and traces of your RAG application.

</div>
    """,

    unsafe_allow_html=True,
)


st.markdown(
    """
<div class="status-box">

<span class="status-dot"></span>

AI Research Platform Online

</div>
    """,

    unsafe_allow_html=True,
)

# MAIN APPLICATION TABS

rag_tab, observability_tab, profile_tab, weather_tab = (
    st.tabs(
        [
            "📚 RAG Assistant",
            "📊 Observability Assistant",
            "👨🏾‍💻 About Lawrence",
            "🌤️ Ghana Weather AI",
        ]
    )
)


# TAB 1 RAG ASSISTANT

with rag_tab:

    # DOCUMENT UPLOAD SECTION
  
    st.markdown(
        """
<div class="section-card">

<div class="section-title">
📄 Upload Document
</div>

<div class="section-description">

Upload a PDF document. The document will be sent
to the FastAPI backend, processed by Docling,
divided into RAG chunks, embedded, and stored
in Pinecone.

</div>

</div>
        """,

        unsafe_allow_html=True,
    )


    uploaded_file = (
        st.file_uploader(

            "Upload your PDF",

            type=[
                "pdf"
            ],

            accept_multiple_files=
                False,

            key=
                "rag_pdf_uploader",
        )
    )

    # PROCESS DOCUMENT
  
    if uploaded_file is not None:

        st.caption(
            f"Selected document: "
            f"{uploaded_file.name}"
        )


        process_document = (
            st.button(

                "📚 Process Document",

                use_container_width=
                    True,

                key=
                    "process_document_button",
            )
        )


        if process_document:

            with st.spinner( "Processing document..."):

                try:

                    files = {

                        "file": (

                            uploaded_file.name,

                            uploaded_file.getvalue(),

                            "application/pdf",
                        )
                    }


                    headers = {

                        "Authorization":

                            f"Bearer "
                            f"{st.session_state.access_token}"
                    }


                    response = requests.post(

                            DOCUMENTS_API_URL,

                            files=files,

                            headers=headers,

                            timeout=900,
                        )
                    


                    
                    # EXPIRED AUTH TOKEN
                    if response.status_code == 401:

                        st.session_state["access_token"] = None

                        st.session_state["user"] = None

                        st.error("Your session has expired. Please log in again.")

                        st.rerun()

                    response.raise_for_status()

                    # RESPONSE

                    data = response.json()
                    
                    st.success("Document processed successfully.")


                    col1, col2, col3 = st.columns(3)
                    
                    with col1:

                        st.metric(

                            "Chunks Created",

                            data.get(
                                "chunks_created",
                                0,
                            ),
                        )


                    with col2:

                        st.metric(

                            "Index",

                            data.get(
                                "index",
                                "N/A",
                            ),
                        )


                    with col3:

                        st.metric(

                            "Namespace",

                            data.get(
                                "namespace",
                                "N/A",
                            ),
                        )


                    st.info(
                        f"Uploaded file: "
                        f"{data.get('filename')}"
                    )


                except requests.exceptions.ConnectionError:

                    st.error(
                        "Unable to connect to the "
                        "FastAPI RAG backend at "
                        f"{BASE_API_URL}."
                    )


                except requests.exceptions.Timeout:

                    st.error(
                        "Document processing "
                        "took too long."
                    )


                except requests.exceptions.HTTPError:

                    try:

                        error_data = (
                            response.json()
                        )


                        error_message = (
                            error_data.get(
                                "detail",
                                "Document processing failed.",
                            )
                        )


                    except Exception:

                        error_message = (
                            "Document processing failed."
                        )


                    st.error(
                        error_message
                    )


                except Exception as e:

                    st.error(
                        "Something went wrong: "
                        f"{str(e)}"
                    )

    # DIVIDER
    
    st.divider()

    # RAG QUERY SECTION
 
    st.markdown(
        """
<div class="section-card">

<div class="section-title">
💬 Ask Your Document
</div>

<div class="section-description">

Ask a question about the uploaded document.
The answer will be generated only from retrieved
document evidence.

</div>

</div>
        """,

        unsafe_allow_html=True,
    )

    # RAG QUERY FORM

    with st.form("query_form",clear_on_submit=True):

        query = (
            st.text_area(

                "Your question",

                placeholder=(
                    "Ask a question "
                    "about your document..."
                ),

                label_visibility="collapsed",

                key="rag_query"
            )
        )


        submit_button = (
            st.form_submit_button(

                "✨ Ask Question",

                use_container_width=
                    True,
            )
        )


    # SEND QUERY TO FASTAPI RAG BACKEND


    if submit_button:

        query = query.strip()
        
        if not query:

            st.warning("Please enter a question before submitting.")

        else:

            with st.spinner("Retrieving documents and generating an answer..."):

                try:

                    headers = {

                        "Authorization":

                            f"Bearer "
                            f"{st.session_state.access_token}"
                    }


                    response = (
                        requests.post(

                            API_URL,

                            json={
                                "query":query
                            },

                            headers=headers,

                            timeout=120,
                        )
                    )

                    # EXPIRED AUTH TOKEN

                    if response.status_code == 401:

                        st.session_state["access_token"] = None

                        st.session_state["user"] = None

                        st.error("Your session has expired. Please log in again.")

                        st.rerun()

                    response.raise_for_status()

                    data = response.json()
                    

                    answer = data["answer"]
                    
                    # USER QUESTION
                 
                    with st.chat_message("user"):

                        st.markdown(query)

                    # RAG ANSWER
                    
                    with st.chat_message("assistant"):

                        st.markdown(answer)

                except requests.exceptions.ConnectionError:

                    st.error(
                        "Unable to connect to the "
                        "FastAPI RAG backend at "
                        f"{BASE_API_URL}."
                    )


                except requests.exceptions.Timeout:

                    st.error("The RAG request took too long. Please try again.")

                except requests.exceptions.HTTPError:

                    try:

                        error_data = response.json()
                        

                        error_message = error_data.get("detail",
                                "FastAPI returned an error.",
                            )
                        
                    except Exception:

                        error_message = ("FastAPI returned an error.")

                    st.error(error_message)

                except Exception as e:

                    st.error(
                        "Something went wrong: "
                        f"{str(e)}"
                    )


# TAB 2 OBSERVABILITY ASSISTANT
with observability_tab:

    st.markdown(
        """
<div class="section-card">

<div class="section-title">
📊 RAG Observability Assistant
</div>

<div class="section-description">

Ask natural-language questions about the
performance, metrics, logs, traces, errors and
health of your RAG application.

Your question is sent to a LangChain tool-calling
agent. The agent automatically chooses approved
Prometheus MCP and OpenSearch MCP tools.

</div>

</div>
        """,

        unsafe_allow_html=True,
    )

    st.markdown(
        """
<div class="observability-info">

<strong>How it works</strong><br><br>

You ask a natural-language question.<br>

Streamlit → LangChain Observability Agent →
Prometheus MCP / OpenSearch MCP →
Prometheus / AWS OpenSearch.

<br><br>

The LLM does <strong>not</strong> create arbitrary
PromQL or OpenSearch queries. It can only call
the approved MCP tools exposed by your servers.

</div>
        """,

        unsafe_allow_html=True,
    )


    
    # EXAMPLE OBSERVABILITY QUESTIONS

    st.markdown(
        "### 💡 Example Questions"
    )


    example_col1, example_col2 = (
        st.columns(2)
    )


    with example_col1:

        st.markdown(
            """
**Metrics**
- How many nodes are in the Kubernetes cluster?
- What is the CPU utilization of each node in the Kubernetes cluster?
- Which pod is consuming the most CPU?
- Are there any CrashLoopBackOff pods?
- How much memory is the rag namespace consuming?
- Is my RAG application healthy?
- What is my retrieval latency?
- Are all Prometheus targets healthy?

            """
        )


    with example_col2:

        st.markdown(
            """
**Logs and Traces**
- Why did the last request fail?
- Show me recent RAG errors.
- Show me recent Pinecone errors.
- What was the latest user query?
- What documents were retrieved?
- What answer did the RAG generate?
- Why did the last request fail?
- Show me recent slow traces.
            """
        )

    st.divider()

    # DISPLAY OBSERVABILITY CHAT HISTORY
    
    for message in st.session_state["observability_messages"]:

        with st.chat_message(message["role"]):

            st.markdown(message["content"])

    # OBSERVABILITY QUERY FORM

    with st.form("observability_query_form",clear_on_submit=True):

        observability_question = st.text_area(

                "Observability question",

                placeholder=(
                    "Example: Why has my RAG "
                    "application been slow during "
                    "the last 30 minutes?"
                ),

                label_visibility="collapsed",

                key="observability_question",
            )
        

        investigate_button = (
            st.form_submit_button(

                "🔎 Investigate System",

                use_container_width=True,
            )
        )

    # SEND QUERY TO OBSERVABILITY AGENT
   
    if investigate_button:

        observability_question = observability_question.strip()
        
        if not observability_question:

            st.warning("Please enter an observability question.")

        else:

            st.session_state["observability_messages"].append(
                {
                    "role":"user",

                    "content": observability_question,
                }
            )

            # DISPLAY USER MESSAGE

            with st.chat_message("user"):

                st.markdown(observability_question)

            # CALL LANGCHAIN OBSERVABILITY AGENT
           
            with st.spinner("Investigating metrics, logs and traces..."):

                try:

                    response = requests.post(

                            OBSERVABILITY_API_URL,

                            json={
                                "question":observability_question
                            },

                            timeout=180,
                        )
                    
                    response.raise_for_status()

                    data = response.json()
                    
                    observability_answer = data["answer"]
                    
                    # STORE AGENT RESPONSE
                    st.session_state["observability_messages"].append(
                        {
                            "role":"assistant",

                            "content":observability_answer,
                        }
                    )

                    # DISPLAY AGENT RESPONSE
                    with st.chat_message("assistant"):

                        st.markdown(observability_answer)

                # CONNECTION ERROR
                except requests.exceptions.ConnectionError:

                    error_message = (
                        "Unable to connect to the "
                        "observability agent at "
                        f"{OBSERVABILITY_BASE_URL}."
                    )

                    st.error(error_message)

                    st.session_state["observability_messages"].append(
                        {
                            "role":"assistant",

                            "content":
                                (
                                    "⚠️ "
                                    f"{error_message}"
                                ),
                        }
                    )

                # TIMEOUT
                except requests.exceptions.Timeout:

                    error_message = ("The observability investigation took too long.")

                    st.error(error_message)

                # HTTP ERROR

                except requests.exceptions.HTTPError:

                    try:

                        error_data = response.json()
                    
                        error_message = (
                            error_data.get(
                                "detail",
                                (
                                    "Observability "
                                    "request failed."
                                ),
                            )
                        )


                    except Exception:

                        error_message = (
                            "Observability "
                            "request failed."
                        )

                    st.error(error_message)

                # GENERAL ERROR

                except Exception as e:

                    st.error(
                        "Something went wrong: "
                        f"{str(e)}"
                    )


    # CLEAR OBSERVABILITY CHAT
  
    if st.session_state["observability_messages"]:

        st.divider()

        clear_col1, clear_col2, clear_col3 = (
            st.columns(
                [
                    1,
                    2,
                    1,
                ]
            )
        )


        with clear_col2:

            if st.button(

                "🗑️ Clear Observability Chat",

                key="clear_observability_chat",

                use_container_width=True,
            ):

                st.session_state["observability_messages"] = []

                st.rerun()

# ============================================================\n# TAB 3 - PROFESSIONAL PROFILE / PORTFOLIO
# ============================================================
with profile_tab:

    # LinkedIn can be overridden with an environment variable when deployed.
    LINKEDIN_URL = os.getenv(
        "LINKEDIN_URL",
        "https://www.linkedin.com/in/lawrenceowusu1",
    )

    # Other professional links remain fixed in the application for now.
    GITHUB_URL = "https://github.com/LawrenceOwusuAI"
    RESEARCHGATE_URL = "https://www.researchgate.net/profile/Lawrence-Owusu-5"
    ORCID_URL = "https://orcid.org/0009-0005-8150-2970"
    RESUME_PATH = os.getenv(
        "RESUME_PATH",
        "Lawrence_Owusu_Resume.pdf",
    )

    # --------------------------------------------------------
    # HERO / PROFESSIONAL BRAND
    # --------------------------------------------------------
    st.markdown(
        """
<div class="profile-hero">
    <div class="profile-name">Lawrence Owusu</div>
    <div class="profile-role">
        Machine Learning Engineer • Generative AI Engineer • MLOps Engineer • Data Scientist
    </div>
    <div class="profile-summary">
        Ph.D. candidate in Computational Data Science &amp; Engineering with a focus on
        building reliable, secure and production-ready AI systems. My work spans
        machine learning, generative AI, retrieval-augmented generation, MLOps,
        cloud infrastructure, model observability and privacy-preserving deep learning.
        I enjoy taking ideas from research and turning them into deployable systems.
    </div>
    <div class="badge-wrap">
        <span class="skill-badge">Machine Learning</span>
        <span class="skill-badge">Generative AI</span>
        <span class="skill-badge">MLOps</span>
        <span class="skill-badge">Data Science</span>
        <span class="skill-badge">RAG</span>
        <span class="skill-badge">LLM Systems</span>
        <span class="skill-badge">AWS</span>
        <span class="skill-badge">Kubernetes</span>
    </div>
</div>
        """,
        unsafe_allow_html=True,
    )

    # --------------------------------------------------------
    # QUICK PROFILE METRICS
    # --------------------------------------------------------
    metric_col1, metric_col2, metric_col3, metric_col4 = st.columns(4)

    with metric_col1:
        st.metric("AWS Certifications", "5×")

    with metric_col2:
        st.metric("Primary Focus", "ML / GenAI")

    with metric_col3:
        st.metric("Cloud", "AWS")

    with metric_col4:
        st.metric("Research", "AI Privacy")

    # --------------------------------------------------------
    # PROFESSIONAL LINKS
    # --------------------------------------------------------
    st.markdown("### 🔗 Professional Links")

    link_col1, link_col2, link_col3, link_col4 = st.columns(4)

    with link_col1:
        st.link_button(
            "LinkedIn",
            LINKEDIN_URL,
            use_container_width=True,
        )

    with link_col2:
        st.link_button(
            "GitHub",
            GITHUB_URL,
            use_container_width=True,
        )

    with link_col3:
        st.link_button(
            "ResearchGate",
            RESEARCHGATE_URL,
            use_container_width=True,
        )

    with link_col4:
        st.link_button(
            "ORCID",
            ORCID_URL,
            use_container_width=True,
        )


    # --------------------------------------------------------
    # ABOUT + CAREER TARGET
    # --------------------------------------------------------
    about_col, target_col = st.columns(2)

    with about_col:
        st.markdown(
            """
<div class="portfolio-card">
<h3>👋 About Me</h3>
<p>
I combine research depth with hands-on engineering. My interests include
production machine-learning systems, LLM applications, retrieval systems,
AI infrastructure, privacy-preserving machine learning and cloud-native deployment.
</p>
<p>
I am especially interested in engineering AI systems that are accurate, observable,
scalable, secure and maintainable after they move beyond the prototype stage.
</p>
</div>
            """,
            unsafe_allow_html=True,
        )

    with target_col:
        st.markdown(
            """
<div class="portfolio-card">
<h3>🎯 Professional Focus</h3>
<ul>
    <li>Machine Learning Engineering</li>
    <li>Generative AI / LLM Engineering</li>
    <li>MLOps and ML Platform Engineering</li>
    <li>Applied Data Science</li>
    <li>Cloud-native AI systems</li>
    <li>AI reliability, evaluation and observability</li>
</ul>
</div>
            """,
            unsafe_allow_html=True,
        )

    # --------------------------------------------------------
    # EDUCATION
    # --------------------------------------------------------
    st.markdown("### 🎓 Education")

    st.markdown(
        """
<div class="portfolio-card">
<h3>Ph.D. — Computational Data Science &amp; Engineering</h3>
<p><strong>North Carolina A&amp;T State University</strong></p>
<p>
Research emphasis: privacy-preserving machine learning, variational autoencoders,
information-theoretic analysis, membership-inference attacks and scalable AI systems.
</p>
<hr>
<h3>M.S. — Data Science &amp; Engineering</h3>
<p>Graduate training in data science, machine learning and computational engineering.</p>
<hr>
<h3>M.S. — Agricultural &amp; Environmental Systems</h3>
<p>Interdisciplinary graduate training connecting analytical methods with real-world systems.</p>
<hr>
<h3>B.S. — Natural Resources Management</h3>
<p>Foundation in environmental and natural-resource systems.</p>
</div>
        """,
        unsafe_allow_html=True,
    )

    # --------------------------------------------------------
    # CORE TECHNICAL SKILLS
    # --------------------------------------------------------
    st.markdown("### 🧰 Technical Skills")

    skill_col1, skill_col2, skill_col3 = st.columns(3)

    with skill_col1:
        st.markdown(
            """
<div class="portfolio-card">
<h3>🤖 ML & Data Science</h3>
<ul>
    <li>Python, SQL, NumPy, Pandas</li>
    <li>Scikit-learn</li>
    <li>TensorFlow / Keras</li>
    <li>Deep Learning</li>
    <li>Computer Vision</li>
    <li>Feature Engineering</li>
    <li>Model Evaluation</li>
    <li>Statistical Analysis</li>
</ul>
</div>
            """,
            unsafe_allow_html=True,
        )

    with skill_col2:
        st.markdown(
            """
<div class="portfolio-card">
<h3>🧠 Generative AI</h3>
<ul>
    <li>LLMs and Prompt Engineering</li>
    <li>Retrieval-Augmented Generation</li>
    <li>LangChain</li>
    <li>MCP Servers / Tool Calling</li>
    <li>Embedding Models</li>
    <li>Reranking and Hybrid Retrieval</li>
    <li>RAG Evaluation</li>
    <li>AI Guardrails</li>
</ul>
</div>
            """,
            unsafe_allow_html=True,
        )

    with skill_col3:
        st.markdown(
            """
<div class="portfolio-card">
<h3>⚙️ MLOps & Cloud</h3>
<ul>
    <li>AWS</li>
    <li>Docker / Docker Compose</li>
    <li>Kubernetes</li>
    <li>Helm / Argo CD</li>
    <li>GitHub Actions CI/CD</li>
    <li>FastAPI / Streamlit</li>
    <li>Prometheus / Grafana</li>
    <li>OpenTelemetry / Logfire</li>
</ul>
</div>
            """,
            unsafe_allow_html=True,
        )

    # --------------------------------------------------------
    # CERTIFICATIONS
    # --------------------------------------------------------
    st.markdown("### ☁️ AWS Certifications")

    st.markdown(
        """
<div class="portfolio-card">
<ul>
    <li><strong>AWS Certified Machine Learning — Specialty</strong></li>
    <li><strong>AWS Certified Data Analytics — Specialty</strong></li>
    <li><strong>AWS Certified Data Engineer — Associate</strong></li>
    <li><strong>AWS Certified AI Practitioner</strong></li>
    <li><strong>AWS Certified Cloud Practitioner</strong></li>
</ul>
</div>
        """,
        unsafe_allow_html=True,
    )

    # --------------------------------------------------------
    # EXPERIENCE / RESEARCH
    # --------------------------------------------------------
    st.markdown("### 💼 Experience & Research")

    exp_col1, exp_col2 = st.columns(2)

    with exp_col1:
        st.markdown(
            """
<div class="portfolio-card">
<h3>Graduate Research</h3>
<p>
Researching privacy-preserving deep-learning methods with emphasis on
variational autoencoders, latent-space perturbation, membership-inference
attacks and information-theoretic privacy analysis.
</p>
<p>
The work combines algorithm design, experimental evaluation, statistical
analysis and scientific publication.
</p>
</div>
            """,
            unsafe_allow_html=True,
        )

    with exp_col2:
        st.markdown(
            """
<div class="portfolio-card">
<h3>Research & Technical Service</h3>
<p>
Experience reviewing technical research papers and communicating applied
machine-learning research through journal articles, conference papers,
presentations and collaborative projects.
</p>
<p>
Research domains include cybersecurity, privacy-preserving AI, wildfire
detection and machine-learning systems.
</p>
</div>
            """,
            unsafe_allow_html=True,
        )

    # --------------------------------------------------------
    # FEATURED ENGINEERING PROJECT
    # --------------------------------------------------------
    st.markdown("### 🚀 Featured Engineering Project")

    st.markdown(
        """
<div class="portfolio-card">
<h3>Production-Grade Retrieval-Augmented Generation Platform</h3>
<p>
Designed and engineered an end-to-end production RAG platform that combines
retrieval quality, LLM reliability, security, observability and cloud-native deployment.
</p>
<ul>
    <li>Streamlit frontend and FastAPI backend</li>
    <li>Document parsing, chunking, embeddings and Pinecone vector search</li>
    <li>Query rewriting, expansion, decomposition and multi-query retrieval</li>
    <li>Reciprocal Rank Fusion and cross-encoder reranking</li>
    <li>LLM gateway routing, retries, fallback and caching</li>
    <li>Input/output safety guardrails and authentication</li>
    <li>Prometheus metrics, logs, traces and Grafana dashboards</li>
    <li>MCP-based observability agent for natural-language system diagnostics</li>
    <li>Docker, Kubernetes, Helm, Argo CD and GitHub Actions</li>
</ul>
</div>
        """,
        unsafe_allow_html=True,
    )

    st.link_button(
        "💻 View GitHub Projects",
        GITHUB_URL,
        use_container_width=True,
    )

    # --------------------------------------------------------
    # DISSERTATION / RESEARCH FOCUS
    # --------------------------------------------------------
    st.markdown("### 🔬 Current Research Focus")

    st.markdown(
        """
<div class="portfolio-card">
<h3>Latent Space Stochastic Perturbation Scheduling (LSSPS)</h3>
<p>
My doctoral research investigates privacy-preserving variational autoencoders.
LSSPS introduces scheduled stochastic perturbation into the VAE latent space to
reduce privacy leakage while preserving reconstruction utility.
</p>
<ul>
    <li>Membership-inference attack evaluation</li>
    <li>Mutual-information estimation and privacy analysis</li>
    <li>Privacy–utility trade-off analysis</li>
    <li>Variational autoencoders and representation learning</li>
    <li>Federated extensions and synthetic-data generation</li>
</ul>
</div>
        """,
        unsafe_allow_html=True,
    )

    # --------------------------------------------------------
    # PUBLICATIONS
    # --------------------------------------------------------
    st.markdown("### 📚 Selected Publications")

    st.markdown(
        """
<div class="portfolio-card">
<h3>Latent Space Stochastic Perturbation Schedule via Cosine Annealing Scheduler for Privacy-Preserving Variational Autoencoders</h3>
<p>2025 Cyber Awareness and Research Symposium (CARS), IEEE.</p>
<p>
<a href="https://doi.org/10.1109/CARS67163.2025.11337387" target="_blank">
Read publication / DOI →
</a>
</p>
</div>

<div class="portfolio-card">
<h3>Speeding Up ML-based IDSs through Data Preprocessing Techniques</h3>
<p>International Journal of Computer Applications, Vol. 187, No. 12, 2025.</p>
<p>
<a href="https://doi.org/10.5120/ijca2025925071" target="_blank">
Read publication / DOI →
</a>
</p>
</div>

<div class="portfolio-card">
<h3>Reduction of Misclassifications in Wildfire Detection: A Weighted Ensemble Deep Learning Approach</h3>
<p>International Journal of Intelligent Systems and Applications, Vol. 16, No. 5, 2024.</p>
<p>
<a href="https://doi.org/10.5815/ijisa.2024.05.05" target="_blank">
Read publication / DOI →
</a>
</p>
</div>
        """,
        unsafe_allow_html=True,
    )

    # --------------------------------------------------------
    # RESUME
    # --------------------------------------------------------
    st.markdown("### 📄 Resume")

    if os.path.isfile(RESUME_PATH):

        with open(RESUME_PATH, "rb") as resume_file:
            resume_bytes = resume_file.read()

        st.download_button(
            label="⬇️ Download Resume",
            data=resume_bytes,
            file_name=os.path.basename(RESUME_PATH),
            mime="application/pdf",
            use_container_width=True,
            key="profile_resume_download",
        )

    else:
        st.info(
            "Resume download is ready to use. Add "
            f"`{RESUME_PATH}` beside the Streamlit app, or set the "
            "`RESUME_PATH` environment variable to the PDF location."
        )

    # --------------------------------------------------------
    # CONTACT / CALL TO ACTION
    # --------------------------------------------------------
    st.markdown("### 🤝 Let's Connect")

    st.markdown(
        """
<div class="portfolio-card">
<h3>Open to ML, Generative AI, MLOps and Data Science opportunities</h3>
<p>
I am interested in opportunities where I can build production AI systems,
solve complex machine-learning problems and contribute across the full ML lifecycle —
from experimentation and evaluation to deployment, monitoring and continuous improvement.
</p>
</div>
        """,
        unsafe_allow_html=True,
    )

    contact_left, contact_center, contact_right = st.columns([1, 2, 1])

    with contact_center:
        st.link_button(
            "Connect on LinkedIn",
            LINKEDIN_URL,
            use_container_width=True,
        )



# ============================================================
# TAB 4 - GHANA WEATHER INTELLIGENCE (ORIGINAL DASHBOARD)
# ============================================================
with weather_tab:
    st.markdown(
        """
        <div class="ghana-weather-hero">
            <h1>🌤️ Ghana Weather Intelligence</h1>
            <p>
                Explore hourly weather forecasts and ask
                questions about cities and towns across Ghana.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    ghana_now = datetime.now(
        ZoneInfo(GHANA_TIMEZONE)
    )

    st.caption(
        "🇬🇭 Ghana local time: "
        + ghana_now.strftime(
            "%A, %d %B %Y • %I:%M %p"
        )
    )



    if weather_get_forecast:
        if not weather_location:
            st.sidebar.warning(
                "Please enter a Ghanaian location."
            )
        else:
            with st.spinner(
                f"Retrieving hourly forecast for {weather_location}..."
            ):
                try:
                    geo = get_coordinates(weather_location)

                    forecast = get_hourly_forecast(
                        geo["latitude"],
                        geo["longitude"],
                        weather_forecast_days,
                    )

                    st.session_state["weather_forecast_data"] = forecast

                    st.session_state["weather_location_name"] = (
                        f"{geo['name']}, "
                        f"{geo.get('admin1', 'Ghana')}"
                    )

                    st.session_state["weather_pending_prompt"] = (
                        f"Provide a detailed {weather_forecast_days}-day "
                        f"weather forecast for {weather_location}, Ghana. "
                        f"Include daily conditions, temperatures, "
                        f"rainfall, rain probability, humidity "
                        f"and wind speed where available."
                    )

                except (
                    requests.RequestException,
                    ValueError,
                    KeyError,
                ) as exc:
                    st.error(str(exc))


    # ============================================================
    # 12. MAIN HEADER
    # ============================================================

    st.markdown(
        """
        <div class="hero">
            <h1>🌤️ Ghana Weather Intelligence</h1>
            <p>
                Explore hourly weather forecasts and ask
                questions about cities and towns across Ghana.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    ghana_now = datetime.now(
        ZoneInfo(GHANA_TIMEZONE)
    )

    st.caption(
        "🇬🇭 Ghana local time: "
        + ghana_now.strftime(
            "%A, %d %B %Y • %I:%M %p"
        )
    )


    # ============================================================
    # 13. DISPLAY WEATHER DASHBOARD
    # ============================================================

    if st.session_state["weather_forecast_data"]:

        data = st.session_state["weather_forecast_data"]

        hourly_df = prepare_hourly_dataframe(data)
        daily_df = prepare_daily_dataframe(data)

        st.markdown(
            f"## 📍 {st.session_state['weather_location_name']}"
        )

        current = data.get("current", {})

        icon, condition = describe_weather(
            current.get("weather_code")
        )

        st.markdown(
            f"### {icon} Current conditions: {condition}"
        )

        metric_columns = st.columns(6)

        metrics = [
            (
                "🌡️ Temperature",
                current.get("temperature_2m"),
                "°C",
            ),
            (
                "🌡️ Feels like",
                current.get("apparent_temperature"),
                "°C",
            ),
            (
                "💦 Humidity",
                current.get("relative_humidity_2m"),
                "%",
            ),
            (
                "💧 Rainfall",
                current.get("rain"),
                "mm",
            ),
            (
                "🌧️ Precipitation",
                current.get("precipitation"),
                "mm",
            ),
            (
                "💨 Wind",
                current.get("wind_speed_10m"),
                "km/h",
            ),
        ]

        for column, (label, value, unit) in zip(
            metric_columns,
            metrics,
        ):
            with column:
                st.metric(
                    label,
                    (
                        f"{value} {unit}"
                        if value is not None
                        else "N/A"
                    ),
                )

        st.divider()

        # --------------------------------------------------------
        # DAILY FORECAST
        # --------------------------------------------------------

        st.markdown("### 📅 Daily forecast")

        if not daily_df.empty:
            daily_display = daily_df[
                [
                    "time",
                    "condition",
                    "temperature_2m_max",
                    "temperature_2m_min",
                    "precipitation_sum",
                    "precipitation_probability_max",
                    "wind_speed_10m_max",
                ]
            ].rename(
                columns={
                    "time": "📅 Date",
                    "condition": "🌤️ Condition",
                    "temperature_2m_max": "🌡️ Max °C",
                    "temperature_2m_min": "🌡️ Min °C",
                    "precipitation_sum": "💧 Rainfall mm",
                    "precipitation_probability_max": "🌧️ Rain chance %",
                    "wind_speed_10m_max": "💨 Wind km/h",
                }
            )

            st.dataframe(
                daily_display,
                use_container_width=True,
                hide_index=True,
            )

        # --------------------------------------------------------
        # SELECT DAY FOR HOURLY FORECAST
        # --------------------------------------------------------

        st.markdown("### 🕒 Hourly weather forecast")

        if not hourly_df.empty:

            available_dates = sorted(
                hourly_df["date"].unique()
            )

            selected_date = st.selectbox(
                "Choose a forecast date",
                available_dates,
                format_func=lambda date: date.strftime(
                    "%A, %d %B %Y"
                ),
            )

            day_df = hourly_df[
                hourly_df["date"] == selected_date
            ].copy()

            # ----------------------------------------------------
            # HOURLY TABLE
            # ----------------------------------------------------

            hourly_display = day_df[
                [
                    "hour",
                    "condition",
                    "temperature_2m",
                    "apparent_temperature",
                    "relative_humidity_2m",
                    "precipitation_probability",
                    "rain",
                    "showers",
                    "precipitation",
                    "cloud_cover",
                    "wind_speed_10m",
                    "wind_gusts_10m",
                ]
            ].rename(
                columns={
                    "hour": "🕒 Hour",
                    "condition": "🌤️ Condition",
                    "temperature_2m": "🌡️ Temp °C",
                    "apparent_temperature": "🌡️ Feels like °C",
                    "relative_humidity_2m": "💦 Humidity %",
                    "precipitation_probability": "🌧️ Rain chance %",
                    "rain": "💧 Rain mm",
                    "showers": "🌦️ Showers mm",
                    "precipitation": "🌧️ Total precipitation mm",
                    "cloud_cover": "☁️ Cloud cover %",
                    "wind_speed_10m": "💨 Wind km/h",
                    "wind_gusts_10m": "🌬️ Gusts km/h",
                }
            )

            st.dataframe(
                hourly_display,
                use_container_width=True,
                hide_index=True,
                height=420,
            )

            # ----------------------------------------------------
            # INTERACTIVE CHARTS
            # ----------------------------------------------------

            st.markdown("### 📈 Hourly weather trends")

            chart_tab1, chart_tab2, chart_tab3, chart_tab4 = (
                st.tabs(
                    [
                        "🌡️ Temperature",
                        "🌧️ Rainfall",
                        "💦 Humidity",
                        "💨 Wind",
                    ]
                )
            )

            chart_df = day_df.set_index("time")

            with chart_tab1:
                st.line_chart(
                    chart_df[
                        [
                            "temperature_2m",
                            "apparent_temperature",
                        ]
                    ],
                    use_container_width=True,
                )

            with chart_tab2:
                st.markdown("**Hourly rainfall (mm)**")

                st.bar_chart(
                    chart_df[["rain", "showers"]],
                    use_container_width=True,
                )

                st.markdown(
                    "**Hourly precipitation probability (%)**"
                )

                st.line_chart(
                    chart_df[
                        ["precipitation_probability"]
                    ],
                    use_container_width=True,
                )

            with chart_tab3:
                st.line_chart(
                    chart_df[
                        ["relative_humidity_2m"]
                    ],
                    use_container_width=True,
                )

            with chart_tab4:
                st.line_chart(
                    chart_df[
                        [
                            "wind_speed_10m",
                            "wind_gusts_10m",
                        ]
                    ],
                    use_container_width=True,
                )

            # ----------------------------------------------------
            # DAILY HUMIDITY SUMMARY
            # ----------------------------------------------------

            st.markdown(
                "### 💦 Daily relative humidity summary"
            )

            humidity_summary = (
                hourly_df.groupby("date")[
                    "relative_humidity_2m"
                ]
                .agg(
                    average="mean",
                    minimum="min",
                    maximum="max",
                )
                .round(1)
                .reset_index()
            )

            humidity_summary.columns = [
                "📅 Date",
                "💦 Average %",
                "💦 Minimum %",
                "💦 Maximum %",
            ]

            st.dataframe(
                humidity_summary,
                use_container_width=True,
                hide_index=True,
            )



    st.divider()
    st.markdown("## 🤖 Ask your weather assistant")
    st.caption("Ask follow-up questions about Ghana's weather. Conversation memory is managed by LangGraph and PostgreSQL.")
    if st.button("🔄 New Weather Conversation", key="weather_new_conversation"):
        st.session_state["weather_messages"] = []
        st.session_state["weather_conversation_id"] = None
        st.session_state["weather_pending_prompt"] = None
        st.rerun()
    for message in st.session_state["weather_messages"]:
        with st.chat_message(message["role"]):
            st.markdown(format_ai_answer(message["content"]) if message["role"] == "assistant" else message["content"])
    weather_user_prompt = st.chat_input("Ask about rainfall, temperature, humidity...", key="weather_chat_input")
    weather_prompt = st.session_state["weather_pending_prompt"] or weather_user_prompt
    st.session_state["weather_pending_prompt"] = None
    if weather_prompt and weather_prompt.strip():
        weather_prompt = weather_prompt.strip()
        st.session_state["weather_messages"].append({"role": "user", "content": weather_prompt})
        with st.chat_message("user"):
            st.markdown(weather_prompt)
        with st.chat_message("assistant"):
            with st.spinner("🤖 Analyzing the weather..."):
                try:
                    result = ask_weather_agent(weather_prompt, st.session_state["weather_conversation_id"])
                    answer = result.get("answer", "No response was returned.")
                    st.session_state["weather_conversation_id"] = result.get("conversation_id", st.session_state["weather_conversation_id"])
                    st.markdown(format_ai_answer(answer))
                    latency = result.get("execution_time_ms")
                    if latency is not None:
                        st.caption(f"⚡ Response time: {latency:.0f} ms")
                    st.session_state["weather_messages"].append({"role": "assistant", "content": answer})
                except RuntimeError as exc:
                    st.error(str(exc))
                except requests.Timeout:
                    st.error("The weather agent timed out.")
                except requests.ConnectionError:
                    st.error("Unable to connect to the Ghana Weather API.")
                except requests.HTTPError as exc:
                    st.error(f"Weather API error: {exc.response.status_code if exc.response is not None else 'unknown'}")
                except (ValueError, KeyError, TypeError):
                    st.error("Invalid response from the weather agent.")
    st.caption("🇬🇭 Ghana Weather Intelligence · Hourly forecasts powered by Open-Meteo · AI powered by LangGraph, FastAPI, PostgreSQL and Portkey")
