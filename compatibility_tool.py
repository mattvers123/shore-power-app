############read from google sheets###########################################
import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
import json
import tempfile
import matplotlib.pyplot as plt
import numpy as np

######pagew laput wide##########
st.set_page_config(layout="wide")

####logo###########################
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

if "show_analysis" not in st.session_state:
    st.session_state.show_analysis = False
    
st.sidebar.title("Use Case Selection")
umbrella = st.sidebar.selectbox("Select Umbrella Case", data["umbrella_name"].unique())
filtered = data[data["umbrella_name"] == umbrella]
use_case = st.sidebar.selectbox("Select Use Case", filtered["use_case_name"].unique())

if st.sidebar.button("🔍 Compatibility Analysis"):
    st.session_state.show_analysis = True
####compatibility analysis page visible#####################
if st.session_state.show_analysis:
    st.title("⚙️ Compatibility Analysis Panel")
    st.markdown("Here we'll compare ship, port, and barge data to compute a compatibility score.")

    # Later: add dropdowns to select UC, barge type, port
    # Pull data from lookup tables
    # Run scoring logic
else:
    # Show your main UC selection interface
    # This is your current app UI
    st.title("🔌 BlueBARGE Compatibility Tool")

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

        col1, col2 = st.columns([1, 2])  # You can adjust ratio if needed
    with col1:
        
        st.markdown(f"**Average Anchorage Time**: `{selected['avg_time_h']} hours`")
        st.markdown(f"**Total Number of Calls**: `{selected['port_calls (no.)']} `")
        
        st.markdown(f"**Power Demand (MW):**")
        st.write(f"• IMO: `{selected['power_imo_mw']}`")
        st.write(f"• EMSA: `{selected['power_emsa_mw']}`")
        st.write(f"• Load Factor: `{selected['power_lf_mw']}`")

        st.markdown(f"**Energy Demand (MWh):**")
        st.write(f"• IMO: `{selected['energy_imo_mwh']}`")
        st.write(f"• EMSA: `{selected['energy_emsa_mwh']}`")
        st.write(f"• Load Factor: `{selected['energy_lf_mwh']}`")

        st.markdown("---")

    with col2:
        st.markdown("### Comparison Chart")
        # Radio button to select the metric
        metric = st.radio("Select Metric to Compare", [
            "Anchorage Time (h)",
            "Number of Port Calls",
            "Power Demand (MW)",
            "Energy Demand (MWh)"
        ])

        fig, ax = plt.subplots(figsize=(15, 10))
        x = np.arange(len(ship_demand_df))
        bar_labels = ship_demand_df["ship_type"]
        highlight_color = "#FF5733"
        default_color = "#AAAAAA"

        method_colors = {
            "IMO": "#1f77b4",   # blue
            "EMSA": "#2ca02c",  # green
            "LF": "#d62728"     # red
        }
        width = 0.25
        
        if metric == "Anchorage Time (h)":
            values = ship_demand_df["avg_time_h"]
            bar_colors = [highlight_color if s == ship_type else default_color for s in ship_demand_df["ship_type"]]
            ax.bar(x, values, color=bar_colors)
            ax.set_ylabel("Hours")
            ax.set_title("Average Anchorage Time by Ship Type")

        elif metric == "Number of Port Calls":
            values = ship_demand_df["port_calls (no.)"]
            bar_colors = [highlight_color if s == ship_type else default_color for s in ship_demand_df["ship_type"]]
            ax.bar(x, values, color=bar_colors)
            ax.set_ylabel("Calls")
            ax.set_title("Annual Port Calls")

        elif metric == "Power Demand (MW)":
            methods = ["power_imo_mw", "power_emsa_mw", "power_lf_mw"]

            for i, method in enumerate(methods):
                label = method.split("_")[1].upper()
                values = ship_demand_df[method]
                bar_colors = []
                for idx, s in enumerate(ship_demand_df["ship_type"]):
                    alpha = 1.0 if s == ship_type else 0.3
                    bar_colors.append(method_colors[label])
                bar_alphas = [1.0 if s == ship_type else 0.3 for s in ship_demand_df["ship_type"]]
                bars = ax.bar(x + (i - 1)*width, values, width, label=label,
                              color=method_colors[label], alpha=0.8)
                # Apply transparency per bar
                for bar, alpha in zip(bars, bar_alphas):
                    bar.set_alpha(alpha)

            ax.set_ylabel("MW")
            ax.set_title("Power Demand by Ship Type and Method")
            ax.legend()

        elif metric == "Energy Demand (MWh)":
            methods = ["energy_imo_mwh", "energy_emsa_mwh", "energy_lf_mwh"]

            for i, method in enumerate(methods):
                label = method.split("_")[1].upper()
                values = ship_demand_df[method]
                bar_colors = []
                for idx, s in enumerate(ship_demand_df["ship_type"]):
                    alpha = 1.0 if s == ship_type else 0.3
                    bar_colors.append(method_colors[label])
                bar_alphas = [1.0 if s == ship_type else 0.3 for s in ship_demand_df["ship_type"]]
                bars = ax.bar(x + (i - 1)*width, values, width, label=label,
                              color=method_colors[label], alpha=0.8)
                for bar, alpha in zip(bars, bar_alphas):
                    bar.set_alpha(alpha)


            ax.set_ylabel("MWh")
            ax.set_title("Energy Demand by Ship Type and Method")
            ax.legend()

        ax.set_xticks(x)
        ax.set_xticklabels(ship_demand_df["ship_type"], rotation=15)
        st.pyplot(fig)

    

