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

############################compatibility analysis status###
if "show_analysis" not in st.session_state:
    st.session_state.show_analysis = False

# Sidebar: Compatibility button
if st.sidebar.button("🔍 Compatibility Analysis"):
    st.session_state.show_analysis = True
    st.rerun()

# ✅ Page routing
if st.session_state.show_analysis:
	
    st.title("⚙️ Compatibility Analysis Panel")
    st.markdown("Compare ship-side demand, port capabilities, and BlueBARGE specs.") 

    # 1️⃣ 🚢 Ship Type Selector
    try:
        ship_sheet = client.open("Bluebarge_Comp_Texts").worksheet("Ship Demand")
        ship_demand_df = pd.DataFrame(ship_sheet.get_all_records())
        ship_type = st.selectbox("Select Ship Type", ship_demand_df["ship_type"].unique())
        selected_ship = ship_demand_df[ship_demand_df["ship_type"] == ship_type].iloc[0]

	# Load Voltage Compatibility data
        voltage_sheet = client.open("Bluebarge_Comp_Texts").worksheet("Voltage Compatibility")
        voltage_df = pd.DataFrame(voltage_sheet.get_all_records())
    
    except Exception as e:
        st.warning(f"Could not load ship demand data: {e}")
        selected_ship = None

    # 2️⃣ If a ship type is selected, define the UC demand profile 
    if selected_ship is not None:
        method = st.radio("Select estimation method for power/energy:", ["IMO", "EMSA", "LF", "Average"])
	    
        if method == "IMO":
            power = selected_ship["power_imo_mw"]
            energy = selected_ship["energy_imo_mwh"]
        elif method == "EMSA":
            power = selected_ship["power_emsa_mw"]
            energy = selected_ship["energy_emsa_mwh"]
        elif method == "LF":
            power = selected_ship["power_lf_mw"]
            energy = selected_ship["energy_lf_mwh"]
        elif method == "Average":
            power = round(np.mean([
            selected_ship["power_imo_mw"],
            selected_ship["power_emsa_mw"],
            selected_ship["power_lf_mw"]
            ]), 2)  # ⬅️ round to 2 decimal places

            energy = round(np.mean([
            selected_ship["energy_imo_mwh"],
            selected_ship["energy_emsa_mwh"],
            selected_ship["energy_lf_mwh"]
            ]), 2)

        uc_demand = {
   	 	"required_power_mw": power,
    	 	"required_energy_mwh": energy,
    	 	"required_standard": None,
    	 	"required_voltage": None
        }

	# Radio button to choose power/energy estimation method
	# Lookup HV/LV capabilities from voltage compatibility sheet
        voltage_row = voltage_df[voltage_df["ship_type"] == ship_type]
        supports_hv = voltage_row.iloc[0]["supports HV"] == "Yes"
        supports_lv = voltage_row.iloc[0]["supports LV"] == "Yes"

        required_power = uc_demand["required_power_mw"]

        # Decide voltage
        if supports_hv and supports_lv:
            if required_power > 1.0:
                selected_voltage = "HV"
                st.info(f"⚡ Required power is {required_power:.2f} MW > 1 MW → High Voltage (HV) enforced.")
            else:
                selected_voltage = st.radio(
                    "Select connection voltage for this ship:",
                    ["HV", "LV"]
                )
        elif supports_hv:
            selected_voltage = "HV"
            st.info("⚡ Ship supports only High Voltage (HV).")
        elif supports_lv:
            selected_voltage = "LV"
            st.info("⚡ Ship supports only Low Voltage (LV).")
        else:
            selected_voltage = None
            st.error("No voltage connection option available.")

        # ✅ Now set the final voltage into demand profile
        uc_demand["required_voltage"] = selected_voltage

	
        # 🛡 Set standard dynamically based on voltage
        if selected_voltage == "HV":
            uc_demand["required_standard"] = "IEC 80005-1"
        elif selected_voltage == "LV":
            uc_demand["required_standard"] = "IEC 80005-3"
        else:
            uc_demand["required_standard"] = None

    with st.expander("🧪 Try a Compatibility Match (Sample)", expanded=True):
    	
    	barge = {
	    "power_mw": 6.5,
	    "energy_mwh": 30,
	    "standards": ["IEC 80005-3"],
	    "voltage_levels": ["LV"],
	}
	
	# Manual input for soft parameter
    	user_operational_fit = st.slider("Operational Fit (0 = poor, 1 = perfect)", 0.0, 1.0, 0.7)

	# Calculate scores
    	def scaled_score(barge_val, required_val):
	    	if required_val == 0:
	        	return 0
	    	return min((barge_val / required_val), 1.0) * 100
	
    	def binary_score(barge_val, required_val):
	    	return 100 if required_val in barge_val else 0
	
	# Match scoring
    	score_data = [
	    {
	        "Factor": "Power Capacity",
	        "Match (%)": scaled_score(barge["power_mw"], uc_demand["required_power_mw"]),
	        "Barge Value": f"{barge['power_mw']} MW",
	        "UC Requirement": f"{uc_demand['required_power_mw']} MW"
	    },
	    {
	        "Factor": "Energy Autonomy",
	        "Match (%)": scaled_score(barge["energy_mwh"], uc_demand["required_energy_mwh"]),
	        "Barge Value": f"{barge['energy_mwh']} MWh",
	        "UC Requirement": f"{uc_demand['required_energy_mwh']} MWh"
	    },
	    {
	        "Factor": "Standards Compliance",
	        "Match (%)": binary_score(barge["standards"], uc_demand["required_standard"]),
	        "Barge Value": ", ".join(barge["standards"]),
	        "UC Requirement": uc_demand["required_standard"]
	    },
	    {
	        "Factor": "HV/LV Match",
	        "Match (%)": binary_score(barge["voltage_levels"], uc_demand["required_voltage"]),
	        "Barge Value": ", ".join(barge["voltage_levels"]),
	        "UC Requirement": uc_demand["required_voltage"]
	    },
	    {
	        "Factor": "Operational Fit (user-rated)",
	        "Match (%)": user_operational_fit * 100,
	        "Barge Value": f"{user_operational_fit:.2f}",
	        "UC Requirement": "User-defined"
	    }
	]
	
    	score_df = pd.DataFrame(score_data)
    	st.table(score_df)
	
	# Total weighted score (simple equal weight for now)
    	total_score = score_df["Match (%)"].mean()
    	st.success(f"🔢 **Total Compatibility Score:** {total_score:.1f} / 100")

	
    # --- Load editable parameters from Google Sheet -- 
    try:
    	param_config_sheet = client.open("Bluebarge_Comp_Texts").worksheet("Analysis")
    	param_config_df = pd.DataFrame(param_config_sheet.get_all_records())
    	st.subheader("All Compatibility Parameters")
    	st.dataframe(param_config_df)

    except Exception as e:
    	st.warning(f"Could not load editable parameter definitions: {e}")

    if st.button("⬅️ Back to Use Case Selection"):
        st.session_state.show_analysis = False
        st.rerun()

    # Placeholder for scoring UI
    st.write("Scoring UI coming soon...")
else:
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

            col1, col2 = st.columns([1, 2])

            with col1:
                st.markdown(f"**Average Anchorage Time**: `{selected['avg_time_h']} hours`")
                st.markdown(f"**Total Number of Calls**: `{selected['port_calls (no.)']}`")

                st.markdown("**Power Demand (MW):**")
                st.write(f"• IMO: `{selected['power_imo_mw']}`")
                st.write(f"• EMSA: `{selected['power_emsa_mw']}`")
                st.write(f"• Load Factor: `{selected['power_lf_mw']}`")

                st.markdown("**Energy Demand (MWh):**")
                st.write(f"• IMO: `{selected['energy_imo_mwh']}`")
                st.write(f"• EMSA: `{selected['energy_emsa_mwh']}`")
                st.write(f"• Load Factor: `{selected['energy_lf_mwh']}`")

                st.markdown("---")

            with col2:
                st.markdown("### Comparison Chart")

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
                    "IMO": "#1f77b4",
                    "EMSA": "#2ca02c",
                    "LF": "#d62728"
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
                        bar_alphas = [1.0 if s == ship_type else 0.3 for s in ship_demand_df["ship_type"]]
                        bars = ax.bar(x + (i - 1)*width, values, width, label=label,
                                      color=method_colors[label], alpha=0.8)
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
                ax.grid(True, linestyle="--", linewidth=0.5, alpha=0.7)
                st.pyplot(fig)

	
   
    

