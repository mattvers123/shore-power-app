
############read from google sheets###########################################
import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
import json
import tempfile
import matplotlib.pyplot as plt
import numpy as np

st.set_page_config(layout="wide")

with open("bluebarge-logo-white.svg", "r") as f:
    svg_logo = f.read()
st.sidebar.markdown(svg_logo, unsafe_allow_html=True)

gcp_secrets = st.secrets["gcp_service_account"]
with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as tmp:
    json.dump(gcp_secrets, tmp)
    tmp_path = tmp.name

scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name(tmp_path, scope)
client = gspread.authorize(creds)

sheet = client.open("Bluebarge_Comp_Texts").sheet1
data = pd.DataFrame(sheet.get_all_records())

if "show_analysis" not in st.session_state:
    st.session_state.show_analysis = False

if st.sidebar.button("\U0001F50D Compatibility Analysis"):
    st.session_state.show_analysis = True
    st.rerun()

if st.session_state.show_analysis:
    st.title("\u2699\ufe0f Compatibility Analysis Panel")
    st.markdown("Compare ship-side demand, port capabilities, and BlueBARGE specs.")

    try:
        ship_sheet = client.open("Bluebarge_Comp_Texts").worksheet("Ship Demand")
        ship_demand_df = pd.DataFrame(ship_sheet.get_all_records())
        ship_type = st.selectbox("Select Ship Type", ship_demand_df["ship_type"].unique())
        selected_ship = ship_demand_df[ship_demand_df["ship_type"] == ship_type].iloc[0]

        voltage_sheet = client.open("Bluebarge_Comp_Texts").worksheet("Voltage Compatibility")
        voltage_df = pd.DataFrame(voltage_sheet.get_all_records())

    except Exception as e:
        st.warning(f"Could not load ship demand data: {e}")
        selected_ship = None

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
            ]), 2)
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

        st.markdown("<h6>\ud83d\udcdd Regulatory Compliance Declaration</h5>", unsafe_allow_html=True)
        regulation_ack = st.checkbox(
            "Confirm: Vessel is over 5000 GT **and** will stay more than 2 hours at port (Mandatory Shore Power Connection applies)"
        )

        if regulation_ack:
            st.success("\u26a0\ufe0f **Mandatory Shore Power Connection applies.**")
        else:
            st.info("Shore power connection **not mandatory**.")

        voltage_row = voltage_df[voltage_df["ship_type"] == ship_type]
        supports_hv = voltage_row.iloc[0]["supports HV"] == "Yes"
        supports_lv = voltage_row.iloc[0]["supports LV"] == "Yes"

        required_power = uc_demand["required_power_mw"]

        if supports_hv and supports_lv:
            if required_power > 1.0:
                selected_voltage = "HV"
                st.info(f"\u26a1 Required power is {required_power:.2f} MW > 1 MW → High Voltage (HV) enforced.")
            else:
                selected_voltage = st.radio("Select connection voltage for this ship:", ["HV", "LV"])
        elif supports_hv:
            selected_voltage = "HV"
            st.info("\u26a1 Ship supports only High Voltage (HV).")
        elif supports_lv:
            selected_voltage = "LV"
            st.info("\u26a1 Ship supports only Low Voltage (LV).")
        else:
            selected_voltage = None
            st.error("No voltage connection option available.")

        uc_demand["required_voltage"] = selected_voltage

        if selected_voltage == "HV":
            uc_demand["required_standard"] = "IEC 80005-1"
        elif selected_voltage == "LV":
            uc_demand["required_standard"] = "IEC 80005-3"

        with st.expander("\ud83e\uddea Try a Compatibility Match (Sample)", expanded=True):
            barge = {
                "power_mw": 6.5,
                "energy_mwh": 30,
                "standards": ["IEC 80005-3"],
                "voltage_levels": ["LV"],
            }

            user_operational_fit = st.slider("Operational Fit (0 = poor, 1 = perfect)", 0.0, 1.0, 0.7)

            def scaled_score(barge_val, required_val):
                if required_val == 0:
                    return 0
                return min((barge_val / required_val), 1.0) * 100

            def binary_score(barge_val, required_val):
                return 100 if required_val in barge_val else 0

            score_data = [
                {"Factor": "Power Capacity", "Match (%)": scaled_score(barge["power_mw"], uc_demand["required_power_mw"]),
                 "Barge Value": f"{barge['power_mw']} MW", "UC Requirement": f"{uc_demand['required_power_mw']} MW"},
                {"Factor": "Energy Autonomy", "Match (%)": scaled_score(barge["energy_mwh"], uc_demand["required_energy_mwh"]),
                 "Barge Value": f"{barge['energy_mwh']} MWh", "UC Requirement": f"{uc_demand['required_energy_mwh']} MWh"},
                {"Factor": "Standards Compliance", "Match (%)": binary_score(barge["standards"], uc_demand["required_standard"]),
                 "Barge Value": ", ".join(barge["standards"]), "UC Requirement": uc_demand["required_standard"]},
                {"Factor": "HV/LV Match", "Match (%)": binary_score(barge["voltage_levels"], uc_demand["required_voltage"]),
                 "Barge Value": ", ".join(barge["voltage_levels"]), "UC Requirement": uc_demand["required_voltage"]},
                {"Factor": "Operational Fit (user-rated)", "Match (%)": user_operational_fit * 100,
                 "Barge Value": f"{user_operational_fit:.2f}", "UC Requirement": "User-defined"}
            ]

            score_df = pd.DataFrame(score_data)
            st.table(score_df)

            hv_lv_score = score_df.loc[score_df["Factor"] == "HV/LV Match", "Match (%)"].values[0]
            if hv_lv_score == 0:
                total_score = 0
                st.error("\u274c Critical: Voltage mismatch (HV/LV) detected. Barge not compatible!")
            else:
                total_score = score_df["Match (%)"].mean()

            if total_score >= 80:
                st.success(f"\u2705 **Total Compatibility Score: {total_score:.1f} / 100**")
            else:
                st.error(f"\u26a0\ufe0f **Total Compatibility Score: {total_score:.1f} / 100 — Needs Attention!**")

        # PARAMETER TABLE ONLY INSIDE THIS BLOCK
        try:
            param_config_sheet = client.open("Bluebarge_Comp_Texts").worksheet("Analysis")
            param_config_df = pd.DataFrame(param_config_sheet.get_all_records())

            columns_to_keep = {
                "Parameter ID": "Parameter ID",
                "Name": "Name",
                "Description": "Description",
                "Type": "Type",
                "Default Weight": "Default Weight",
                "Editable": "Editable",
                "Param Type": "Parameter Type"
            }
            param_config_df = param_config_df[list(columns_to_keep.keys())].copy()
            param_config_df.rename(columns=columns_to_keep, inplace=True)
            param_config_df["Selection"] = False

            st.markdown("""
                <style>
                div[data-testid="column"] {
                    padding-top: 0.15rem;
                    padding-bottom: 0.15rem;
                    border-bottom: 1px solid #ddd;
                }
                th, td {
                    padding: 2px 6px !important;
                }
                </style>
            """, unsafe_allow_html=True)

            st.markdown("## \u2699\ufe0f Parameter Selection Table")
            with st.form("parameter_form"):
                headers = ["Parameter ID", "Name", "Description", "Type", "Default Weight", "Editable", "Parameter Type", "Include?"]
                header_cols = st.columns([1, 2, 3, 1, 1, 1, 1, 1])
                for col, header in zip(header_cols, headers):
                    col.markdown(f"**{header}**")

                for idx, row in param_config_df.iterrows():
                    cols = st.columns([1, 2, 3, 1, 1, 1, 1, 1])
                    for i, key in zip(range(7), list(columns_to_keep.values())):
                        cols[i].markdown(str(row[key]))
                    if str(row["Editable"]).strip().lower() == "true":
                        choice = cols[7].checkbox("", key=f"checkbox_{idx}")
                        param_config_df.at[idx, "Selection"] = choice
                    else:
                        cols[7].markdown("\ud83d\udd12")

                submitted = st.form_submit_button("\u2705 Show Selected Parameters")
            if submitted:
                selected_df = param_config_df[param_config_df["Selection"] == True].drop(columns=["Selection"])
                if not selected_df.empty:
                    st.markdown("### \u2705 Selected Parameters")
                    st.dataframe(selected_df)
                else:
                    st.info("No parameters were selected.")

        except Exception as e:
            st.error(f"\u274c Error loading parameter definitions: {e}")

    if st.button("\u2b05\ufe0f Back to Use Case Selection"):
        st.session_state.show_analysis = False
        st.rerun()

else:
    st.sidebar.title("Use Case Selection")
    umbrella = st.sidebar.selectbox("Select Umbrella Case", data["umbrella_name"].unique())
    filtered = data[data["umbrella_name"] == umbrella]
    use_case = st.sidebar.selectbox("Select Use Case", filtered["use_case_name"].unique())

    st.title("Shore Power Compatibility Analysis")
    st.subheader(f"Umbrella Case: {umbrella}")
    st.subheader(f"Use Case: {use_case}")

    desc_row = data[(data["umbrella_name"] == umbrella) & (data["use_case_name"] == use_case)]
    if not desc_row.empty:
        st.markdown(f"**Description:**\n\n{desc_row.iloc[0]['description']}")
    else:
        st.warning("Description not found.")

