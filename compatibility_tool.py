############read from google sheets###########################################
import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
import json
import tempfile
####logo###########################33
with open("bluebarge-logo-white.svg", "r") as f:
    svg_logo = f.read()

st.sidebar.markdown(svg_logo, unsafe_allow_html=True)

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

if use_case == "UC1: Anchored Vessels":
    st.subheader("Anchored Ship Power Demand Lookup")

    # Load the correct worksheet
    try:
        ship_sheet = client.open("Bluebarge_Comp_Texts").worksheet("Ship Demand")
        ship_demand_df = pd.DataFrame(ship_sheet.get_all_records())
    except Exception as e:
        st.error(f"Failed to load ship demand data: {e}")
        ship_demand_df = None

    if ship_demand_df is not None:
        ship_type = st.selectbox("Select Ship Type at Anchorage", ship_demand_df["ship_type"].unique())

        selected = ship_demand_df[ship_demand_df["ship_type"] == ship_type].iloc[0]

        st.markdown(f"**Average Anchorage Time**: `{selected['avg_time_h']} hours`")
        st.markdown(f"**Power Demand (MW):**")
        st.write(f"• IMO: `{selected['power_imo_mw']}`")
        st.write(f"• EMSA: `{selected['power_emsa_mw']}`")
        st.write(f"• Load Factor: `{selected['power_lf_mw']}`")

        st.markdown(f"**Energy Demand (MWh):**")
        st.write(f"• IMO: `{selected['energy_imo_mwh']}`")
        st.write(f"• EMSA: `{selected['energy_emsa_mwh']}`")
        st.write(f"• Load Factor: `{selected['energy_lf_mwh']}`")

        st.markdown("---")
        st.markdown(f"**Total Annual Energy Demand (GWh)**: `{selected['total_annual_energy_gwh']}`")


