############read from google sheets###########################################
import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
import json
import tempfile

# Step 1: Load the service account JSON from secrets
gcp_secrets = st.secrets["gcp_service_account"]

# Step 2: Save to a temporary JSON file
with tempfile.NamedTemporaryFile(mode="w",delete=False, suffix=".json") as tmp:
    gcp_secrets = {k: v for k, v in st.secrets["gcp_service_account"].items()}
    json.dump(dict(st.secrets["gcp_service_account"]), tmp)
    tmp_path = tmp.name

# Setup Google Sheets connection
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name(tmp_path, scope)
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

