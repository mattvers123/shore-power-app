import streamlit as st

# --- Mapping umbrella cases to use cases ---
use_case_options = {
    "Umbrella 1: Charging anchored ships and charging barge from offshore plants": [
        "UC1: Anchored Vessels",
        "UC4: Marine Protected Areas (MPAs)",
        "UC5: Charging small transport vessels",
        "UC6: Leisure boats",
        "UC8: Charging from offshore wind farms",
        "UC10: Charging BlueBARGE from anchored vessels"
    ],
    "Umbrella 2: Barge as OPS (Onshore Power Supply) for moored vessels": [
        "UC2: Moored Vessels"
    ],
    "Umbrella 3: From barge to land and offshore structures": [
        "UC3: Isolated inhabited areas",
        "UC7: Offshore platforms – oil rigs",
        "UC9: Power to land after disasters"
    ]
}

# --- Sidebar for navigation ---
st.sidebar.title("Use Case Selection")
umbrella = st.sidebar.selectbox("Select Umbrella Case", list(use_case_options.keys()))
use_case = st.sidebar.selectbox("Select Specific Use Case", use_case_options[umbrella])

# --- Main display ---
st.title("Shore Power Compatibility Analysis")

st.subheader("Selected Umbrella Case:")
st.markdown(f"**{umbrella}**")

st.subheader("Selected Use Case:")
st.markdown(f"**{use_case}**")

st.info("Inputs and analysis will be displayed here based on the selected use case.")
############read from google sheets###########################################
import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd

# Setup Google Sheets connection
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("my-project-web-novosim-8ce6158fd7b6.json.json", scope)
client = gspread.authorize(creds)

# Open the sheet
sheet = client.open("Bluebarge_Comp_Texts").sheet1  # or .worksheet("Sheet1")
data = pd.DataFrame(sheet.get_all_records())

# Sidebar inputs
st.sidebar.title("Use Case Selection")
umbrella = st.sidebar.selectbox("Select Umbrella Case", data["umbrella_name"].unique())
filtered = data[data["umbrella_name"] == umbrella]
use_case = st.sidebar.selectbox("Select Use Case", filtered["use_case_name"].unique())

# Main output
st.title("Shore Power Compatibility Analysis")
st.subheader(f"Umbrella Case: {umbrella}")
st.subheader(f"Use Case: {use_case}")

# Fetch description
desc_row = data[(data["umbrella_name"] == umbrella) & (data["use_case_name"] == use_case)]
if not desc_row.empty:
    st.markdown(f"**Description:**\n\n{desc_row.iloc[0]['description']}")
else:
    st.warning("Description not found.")

