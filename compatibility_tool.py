############read from google sheets###########################################
import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from google.oauth2.service_account import Credentials
import pandas as pd
import json
import tempfile
import matplotlib.pyplot as plt
import numpy as np
import requests
import folium
from streamlit_folium import st_folium
from datetime import datetime, timedelta
from timezonefinder import TimezoneFinder
import pytz


def compute_score_contribution(required, provided, weight):
    if required == 0:
        return 0.0
    ratio = min(provided / required, 1.0)
    return round(ratio * weight, 4)


@st.cache_data(ttl=600)
def load_equipment_data():
    spreadsheet = client.open("Bluebarge_Comp_Texts")
    equipment_sheet = spreadsheet.worksheet("Equipment List")
    equipment_data = pd.DataFrame(equipment_sheet.get_all_records())
    return equipment_data


@st.cache_data(ttl=600)  # 10 dakika cache
def load_param_config():
    spreadsheet = client.open("Bluebarge_Comp_Texts")
    param_config_sheet = spreadsheet.worksheet("Analysis")
    param_config_df = pd.DataFrame(param_config_sheet.get_all_records())
    return param_config_df


@st.cache_data(ttl=600)
def load_ship_demand():
    spreadsheet = client.open("Bluebarge_Comp_Texts")
    ship_sheet = spreadsheet.worksheet("Ship Demand")
    ship_demand_df = pd.DataFrame(ship_sheet.get_all_records())
    return ship_demand_df


@st.cache_data(ttl=600)
def load_weather_thresholds():
    spreadsheet = client.open("Bluebarge_Comp_Texts")
    weather_sheet = spreadsheet.worksheet("Weather Thresholds")
    df = pd.DataFrame(weather_sheet.get_all_records())
    df.set_index("Parameter", inplace=True)
    return df


columns_to_keep = {
    "Parameter ID": "Parameter ID",
    "Name": "Name",
    "Description": "Description",
    "Type": "Type",
    "Default Weight": "Default Weight",
    "Editable": "Editable",
    "Param Type": "Parameter Type",
}


st.set_page_config(layout="wide")

with open("bluebarge-logo-white.svg", "r") as f:
    svg_logo = f.read()

st.sidebar.markdown(svg_logo, unsafe_allow_html=True)

from google.oauth2.service_account import Credentials
import gspread

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

print("✅ Google Sheets bağlantısı başarılı!")

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

    st.title(" Compatibility Analysis Panel")
    st.markdown("Compare ship-side demand, port capabilities, and BlueBARGE specs.")
    try:
        # Load param_config_df into session state
        if "param_config_df" not in st.session_state:
            param_config_df = load_param_config()

            columns_to_keep = {
                "Parameter ID": "Parameter ID",
                "Name": "Name",
                "Description": "Description",
                "Type": "Type",
                "Default Weight": "Default Weight",
                "Editable": "Editable",
                "Param Type": "Parameter Type",
            }
            param_config_df = param_config_df[list(columns_to_keep.keys())].copy()
            param_config_df.rename(columns=columns_to_keep, inplace=True)
            param_config_df["Selection"] = False
            st.session_state.param_config_df = param_config_df
        else:
            param_config_df = st.session_state.param_config_df

        # 👇👇👇 sadece görünürlüğü kontrol eden blok 👇👇👇
        if st.session_state.get("show_analysis", False):

            # CSS: Satır aralıklarını azalt
            st.markdown(
                """
                <style>
                .stForm .block-container {
                    padding-top: 0rem;
                    padding-bottom: 0rem;
                }
                div[data-testid="column"] {
                    padding-top: 0.15rem;
                    padding-bottom: 0.15rem;
                    border-bottom: 1px solid #ddd;
                }
                .stRadio > div {
                    gap: 4px !important;
                }
                th, td {
                    padding: 2px 6px !important;
                }
                </style>
            """,
                unsafe_allow_html=True,
            )

            st.markdown("##  Parameter Selection Table")

            with st.form("parameter_form"):
                headers = [
                    "Parameter ID",
                    "Name",
                    "Description",
                    "Type",
                    "Default Weight",
                    "Editable",
                    "Parameter Type",
                    "Include?",
                ]
                header_cols = st.columns([1, 2, 3, 1, 1, 1, 1, 1])
                for col, header in zip(header_cols, headers):
                    col.markdown(f"**{header}**")

                for idx, row in param_config_df.iterrows():
                    cols = st.columns([1, 2, 3, 1, 1, 1, 1, 1])
                    for i, key in zip(range(7), list(columns_to_keep.values())):
                        cols[i].markdown(str(row[key]))

                    editable = str(row["Editable"]).strip().lower() == "true"
                    if editable:
                        choice = cols[7].checkbox("", key=f"checkbox_{idx}")
                        param_config_df.at[idx, "Selection"] = choice
                    else:
                        cols[7].markdown("🔒")

                submitted = st.form_submit_button("✅ Show Selected Parameters")

            if submitted:
                selected_df = param_config_df[
                    param_config_df["Selection"] == True
                ].drop(columns=["Selection"])
                has_user_params = (
                    "user_params" in st.session_state
                    and len(st.session_state.user_params) > 0
                )

                if not selected_df.empty:
                    st.markdown("### ✅ Selected Parameters")
                    st.dataframe(
                        selected_df.style.set_properties(
                            **{"text-align": "left", "border": "1px solid lightgray"}
                        )
                    )

                    total_weight = selected_df["Default Weight"].sum()
                    if total_weight < 1.0:
                        st.warning(
                            f"⚠️ Selected parameters' total weight is **{total_weight:.2f}**, which is less than required minimum (1.0). Please adjust your selections."
                        )
                    else:
                        st.success(
                            f"✅ Selected parameters' total weight is **{total_weight:.2f}**. You may proceed."
                        )

                elif has_user_params:
                    st.success("✅ Custom parameters have been added successfully.")

                else:
                    st.info("No parameters were selected.")

            # 👤 User-defined parameters section
            st.markdown("##  User-defined Parameters")

            user_param_container = st.container()

            with user_param_container:
                st.markdown(
                    """
                You can add custom parameters to include in the analysis.  
                These will be treated with equal importance in compatibility scoring.
                """
                )

                user_param_df = pd.DataFrame(columns=["Name", "Value", "Weight (0-1)"])

                if "user_params" not in st.session_state:
                    st.session_state.user_params = []

            with st.form("add_user_param"):
                col1, col2, col3 = st.columns(3)
                with col1:
                    name_input = st.text_input("Parameter Name")
                with col2:
                    value_input = st.number_input(
                        "Parameter Value", value=0.0, step=0.1, format="%.2f"
                    )
                with col3:
                    weight_input = st.number_input(
                        "Weight (0-1)",
                        min_value=0.0,
                        max_value=1.0,
                        step=0.01,
                        format="%.2f",
                    )

                submitted = st.form_submit_button("➕ Add Parameter")
                if submitted and name_input.strip() != "":
                    st.session_state.user_params.append(
                        {
                            "Name": name_input.strip(),
                            "Value": value_input,
                            "Weight": weight_input,
                        }
                    )

            if st.session_state.user_params:
                st.markdown("### 📌 Added Custom Parameters:")

                for idx, param in enumerate(st.session_state.user_params):
                    cols = st.columns([3, 2, 2, 1])
                    cols[0].markdown(f"**{param['Name']}**")
                    cols[1].markdown(f"{param['Value']}")
                    cols[2].markdown(f"{param['Weight']}")
                    if cols[3].button("❌", key=f"remove_user_param_{idx}"):
                        st.session_state.user_params.pop(idx)
                        st.experimental_rerun()

            if submitted:
                selected_df = param_config_df[
                    param_config_df["Selection"] == True
                ].drop(columns=["Selection"])

                if not selected_df.empty:
                    st.markdown("### ✅ Selected Parameters")
                    st.dataframe(
                        selected_df.style.set_properties(
                            **{"text-align": "left", "border": "1px solid lightgray"}
                        )
                    )
                else:
                    st.info("No parameters were selected.")
                    # 🔎 1. Must-Have Parametreleri Filtrele
            must_df = param_config_df[
                param_config_df["Parameter Type"].str.lower() == "must"
            ].copy()
            must_df.reset_index(drop=True, inplace=True)

    except Exception as e:
        st.error(f"❌ Error loading parameter definitions: {e}")

    st.title(" Real-Time Marine and Weather Data (Local Time Accurate)")

    st.markdown(
        """
        <style>
        .main > div {
            padding-bottom: 0rem !important;
        }
        .element-container:has(.folium-map) {
            margin-bottom: -80px !important;
            padding-bottom: 0px !important;
        }
        iframe {
            height: 300px !important;
            margin: 0 auto !important;
            display: block;
            padding: 0px !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    m = folium.Map(location=[41.0082, 28.9784], zoom_start=6)
    m.add_child(folium.LatLngPopup())
    map_data = st_folium(m, width=700, height=300)

    tf = TimezoneFinder()

    selected_lat = None
    selected_lon = None

    if map_data and map_data.get("last_clicked"):
        selected_lat = map_data["last_clicked"]["lat"]
        selected_lon = map_data["last_clicked"]["lng"]
        st.session_state["selected_lat"] = selected_lat
        st.session_state["selected_lon"] = selected_lon
        st.success(f"Selected Coordinates: {selected_lat:.4f}, {selected_lon:.4f}")

    # Kullanıcı form submit ettikten sonra da koordinatlar hatırlansın:
    selected_lat = st.session_state.get("selected_lat")
    selected_lon = st.session_state.get("selected_lon")

    if selected_lat and selected_lon:
        if st.button("✅ Confirm and Fetch Data"):
            timezone_str = tf.timezone_at(lng=selected_lon, lat=selected_lat)
            if not timezone_str:
                timezone_str = "UTC"
            local_tz = pytz.timezone(timezone_str)

            marine_url = f"https://marine-api.open-meteo.com/v1/marine?latitude={selected_lat}&longitude={selected_lon}&hourly=wave_height"
            marine_response = requests.get(marine_url)

            weather_url = f"https://api.open-meteo.com/v1/forecast?latitude={selected_lat}&longitude={selected_lon}&hourly=wind_speed_10m"
            weather_response = requests.get(weather_url)

            if (
                marine_response.status_code == 200
                and weather_response.status_code == 200
            ):
                marine_data = marine_response.json()
                weather_data = weather_response.json()

                try:
                    now_utc = datetime.utcnow().replace(tzinfo=pytz.utc)

                    # Marine Data
                    wave_times = [
                        datetime.fromisoformat(t).replace(tzinfo=pytz.utc)
                        for t in marine_data["hourly"]["time"]
                    ]
                    wave_values = marine_data["hourly"]["wave_height"]
                    wave_closest = [
                        (t, v) for t, v in zip(wave_times, wave_values) if t <= now_utc
                    ]
                    if wave_closest:
                        latest_wave_time_utc, latest_wave_value = wave_closest[-1]
                        latest_wave_time_local = latest_wave_time_utc.astimezone(
                            local_tz
                        ).strftime("%Y-%m-%d %H:%M")
                    else:
                        latest_wave_value = None
                        latest_wave_time_local = "N/A"

                    # Weather Data
                    wind_times = [
                        datetime.fromisoformat(t).replace(tzinfo=pytz.utc)
                        for t in weather_data["hourly"]["time"]
                    ]
                    wind_values = weather_data["hourly"]["wind_speed_10m"]
                    wind_closest = [
                        (t, v) for t, v in zip(wind_times, wind_values) if t <= now_utc
                    ]
                    if wind_closest:
                        latest_wind_time_utc, latest_wind_value = wind_closest[-1]
                        latest_wind_time_local = latest_wind_time_utc.astimezone(
                            local_tz
                        ).strftime("%Y-%m-%d %H:%M")
                    else:
                        latest_wind_value = None
                        latest_wind_time_local = "N/A"

                    # Display
                    if latest_wave_value is not None:
                        st.markdown(
                            f"### 🌊 Wave Height: `{latest_wave_value} m` (Local Time: {latest_wave_time_local} - {timezone_str})"
                        )
                    else:
                        st.warning(
                            "⚠️ No wave height data available for the selected location and time."
                        )

                    if latest_wind_value is not None:
                        st.markdown(
                            f"### 💨 Wind Speed: `{latest_wind_value} km/h` (Local Time: {latest_wind_time_local} - {timezone_str})"
                        )
                    else:
                        st.warning(
                            "⚠️ No wind speed data available for the selected location and time."
                        )

                    try:
                        weather_thresholds = load_weather_thresholds()

                        weather_results = []

                        # Wave karşılaştırması
                        wave_threshold = weather_thresholds.loc["wave_height"][
                            "Threshold"
                        ]
                        wave_status = (
                            "✅ Pass"
                            if latest_wave_value <= wave_threshold
                            else "❌ Fail"
                        )
                        weather_results.append(
                            {
                                "Parameter": "Wave Height",
                                "Value": f"{latest_wave_value:.2f} m",
                                "Threshold": f"{wave_threshold:.2f} m",
                                "Result": wave_status,
                            }
                        )

                        # Wind karşılaştırması
                        wind_threshold = weather_thresholds.loc["wind_speed"][
                            "Threshold"
                        ]
                        wind_status = (
                            "✅ Pass"
                            if latest_wind_value <= wind_threshold
                            else "❌ Fail"
                        )
                        weather_results.append(
                            {
                                "Parameter": "Wind Speed",
                                "Value": f"{latest_wind_value:.2f} km/h",
                                "Threshold": f"{wind_threshold:.2f} km/h",
                                "Result": wind_status,
                            }
                        )

                        # Sonuçları göster
                        weather_df = pd.DataFrame(weather_results)
                        st.markdown("### 🌡️ Weather Compliance Check")
                        st.table(weather_df)

                    except Exception as e:
                        st.error(f"❌ Weather compliance comparison failed: {e}")

                except Exception as e:
                    st.error(f"❌ Data processing failed: {e}")
            else:
                st.error("❌ Failed to fetch data from APIs.")
    else:
        st.info("Please click a location on the map to proceed.")

    # 1️⃣  Ship Type Selector
    try:
        ship_demand_df = load_ship_demand()
        ship_type = st.selectbox(
            "Select Ship Type", ship_demand_df["ship_type"].unique()
        )
        selected_ship = ship_demand_df[ship_demand_df["ship_type"] == ship_type].iloc[0]

        # Load Voltage Compatibility data
        voltage_sheet = client.open("Bluebarge_Comp_Texts").worksheet(
            "Voltage Compatibility"
        )
        voltage_df = pd.DataFrame(voltage_sheet.get_all_records())

    except Exception as e:
        st.warning(f"Could not load ship demand data: {e}")
        selected_ship = None

    # 2️⃣ If a ship type is selected, define the UC demand profile
    if selected_ship is not None:
        method = st.radio(
            "Select estimation method for power/energy:",
            ["IMO", "EMSA", "LF", "Average"],
        )

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
            power = round(
                np.mean(
                    [
                        selected_ship["power_imo_mw"],
                        selected_ship["power_emsa_mw"],
                        selected_ship["power_lf_mw"],
                    ]
                ),
                2,
            )  # ⬅️ round to 2 decimal places

            energy = round(
                np.mean(
                    [
                        selected_ship["energy_imo_mwh"],
                        selected_ship["energy_emsa_mwh"],
                        selected_ship["energy_lf_mwh"],
                    ]
                ),
                2,
            )

        uc_demand = {
            "required_power_mw": power,
            "required_energy_mwh": energy,
            "required_standard": None,
            "required_voltage": None,
        }

        # 🚩 Regulatory Compliance Declaration
        # st.markdown("###  Regulatory Compliance Declaration")
        regulation_choice = st.radio(
            "📌 Is this vessel over 5000 GT **and** will it stay more than 2 hours at the port? (Mandatory shore power connection applies)",
            ("Yes", "No"),
            index=None,
        )

        if regulation_choice == "Yes":
            st.success("✅ Mandatory shore power connection applies for this vessel.")
        elif regulation_choice == "No":
            st.warning("❌ Mandatory shore power connection does not apply.")
            st.stop()
        else:
            st.info("Please answer this question to proceed.")
            st.stop()

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
                st.info(
                    f"⚡ Required power is {required_power:.2f} MW > 1 MW → High Voltage (HV) enforced."
                )
            else:
                selected_voltage = st.radio(
                    "Select connection voltage for this ship:", ["HV", "LV"]
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

        def scaled_score(barge_val, required_val):
            if required_val == 0:
                return 0
            return min((barge_val / required_val), 1.0) * 100

        def binary_score(barge_val, required_val):
            return 100 if required_val in barge_val else 0

        score_data = [
            {
                "Factor": "Power Capacity",
                "Match (%)": scaled_score(
                    barge["power_mw"], uc_demand["required_power_mw"]
                ),
                "Barge Value": f"{barge['power_mw']} MW",
                "UC Requirement": f"{uc_demand['required_power_mw']} MW",
            },
            {
                "Factor": "Energy Autonomy",
                "Match (%)": scaled_score(
                    barge["energy_mwh"], uc_demand["required_energy_mwh"]
                ),
                "Barge Value": f"{barge['energy_mwh']} MWh",
                "UC Requirement": f"{uc_demand['required_energy_mwh']} MWh",
            },
            {
                "Factor": "Standards Compliance",
                "Match (%)": binary_score(
                    barge["standards"], uc_demand["required_standard"]
                ),
                "Barge Value": ", ".join(barge["standards"]),
                "UC Requirement": uc_demand["required_standard"],
            },
            {
                "Factor": "HV/LV Match",
                "Match (%)": binary_score(
                    barge["voltage_levels"], uc_demand["required_voltage"]
                ),
                "Barge Value": ", ".join(barge["voltage_levels"]),
                "UC Requirement": uc_demand["required_voltage"],
            },
        ]

        score_df = pd.DataFrame(score_data)
        st.markdown("### ⚙️ Compatibility Match Results")
        st.table(score_df)

        avg_score = round(score_df["Match (%)"].mean(), 2)
        st.markdown(f"### ✅ Average Match Score: `{avg_score} %`")

        # Normalize parameter names
        param_config_df["Name_clean"] = param_config_df["Name"].str.lower().str.strip()

        # Ensure 'Selection' column exists
        if "Selection" not in param_config_df.columns:
            param_config_df["Selection"] = False

    # --- Load editable parameters from Google Sheet --

    equipment_df = load_equipment_data()

    #  Port and Ship Compatibility Matching
    st.header(" Port and Ship Equipment Compatibility")

    available_ports = equipment_df["Port"].dropna().unique()
    selected_port = st.selectbox("Select a Port", available_ports)

    port_equipment = equipment_df[equipment_df["Port"] == selected_port].copy()

    # GEMİ → PLUG eşleşmesi
    shiptype_to_plugtype = {
        "Bulk carrier": "General Cargo",
        "Container ship": "Container",
        "Container": "Container",
        "Ro-Pax": "Ro-Pax",
        "Cruise": "Cruise",
        # gerekirse diğerleri de eklenebilir
    }
    expected_plug_type = shiptype_to_plugtype.get(ship_type, ship_type)

    #  Her eşleşme sütununu tek tek kontrol et
    port_equipment["Plug Match"] = (
        port_equipment["Plug Type"].str.lower() == expected_plug_type.lower()
    )
    port_equipment["Barge Match"] = port_equipment["Barge Service"].str.lower() == "yes"
    port_equipment["Voltage Match"] = (
        port_equipment["Voltage Level"].str.upper() == uc_demand["required_voltage"]
    )
    port_equipment["Standard Match"] = (
        port_equipment["Standard (IEC)"].str.upper() == uc_demand["required_standard"]
    )

    # ✅ Tüm kriterleri sağlayanları al
    compatible_equipment = port_equipment[
        port_equipment["Plug Match"]
        & port_equipment["Barge Match"]
        & port_equipment["Voltage Match"]
        & port_equipment["Standard Match"]
    ]

    # 🖥️ Tam tabloyu göster
    st.markdown(f"###  Equipment at {selected_port}")
    st.dataframe(
        port_equipment[
            [
                "Type",
                "Voltage Level",
                "Plug Type",
                "Standard (IEC)",
                "Barge Service",
                "Plug Match",
                "Barge Match",
                "Voltage Match",
                "Standard Match",
            ]
        ]
    )

    # 🔍 Sonuç
    st.markdown("###  Hard Parameter Check")

    if not compatible_equipment.empty:
        st.success(
            f"✅ `{ship_type}` is fully compatible with equipment at **{selected_port}**."
        )
        st.dataframe(
            compatible_equipment[
                ["Type", "Voltage Level", "Plug Type", "Standard (IEC)"]
            ]
        )

    else:
        st.error(
            f"❌ No compatible equipment found at **{selected_port}** for ship type `{ship_type}`."
        )
        st.markdown("#### ❗ Mismatch Breakdown:")
        for idx, row in port_equipment.iterrows():
            reasons = []
            if not row["Plug Match"]:
                reasons.append(
                    f"❌ Plug Type mismatch: Expected `{expected_plug_type}`, found `{row['Plug Type']}`"
                )
            if not row["Barge Match"]:
                reasons.append("❌ Barge Service not available")
            if not row["Voltage Match"]:
                reasons.append(
                    f"❌ Voltage mismatch: Expected `{uc_demand['required_voltage']}`, found `{row['Voltage Level']}`"
                )
            if not row["Standard Match"]:
                reasons.append(
                    f"❌ Standard mismatch: Expected `{uc_demand['required_standard']}`, found `{row['Standard (IEC)']}`"
                )
            if reasons:
                st.markdown(f"**Equipment {idx + 1}:**")
                for reason in reasons:
                    st.markdown(f"- {reason}")
        st.stop()

    # 🔽 MUST-HAVE PARAMETRE SEÇİMİ 🔽
    st.markdown("### 🔒 Required Parameters (Must-Have)")
    st.markdown("Please review and confirm all required parameters below.")

    must_df = param_config_df[
        param_config_df["Parameter Type"].str.lower() == "must"
    ].copy()
    must_df.reset_index(drop=True, inplace=True)

    with st.form("must_have_form"):
        headers = [
            "Parameter ID",
            "Name",
            "Description",
            "Type",
            "Default Weight",
            "Editable",
            "Parameter Type",
            "Include?",
        ]
        header_cols = st.columns([1, 2, 3, 1, 1, 1, 1, 1])
        for col, header in zip(header_cols, headers):
            col.markdown(f"**{header}**")

        for idx, row in must_df.iterrows():
            cols = st.columns([1, 2, 3, 1, 1, 1, 1, 1])
            for i, key in zip(range(7), list(columns_to_keep.values())):
                cols[i].markdown(str(row[key]))

            choice = cols[7].checkbox("", key=f"must_checkbox_{idx}")
            must_df.at[idx, "Selection"] = choice

        must_submitted = st.form_submit_button("✅ Confirm Required Parameters")

    # ✅ Eğer form gönderildiyse kontrol et
    if must_submitted:
        not_selected = must_df[must_df["Selection"] != True]
        if not not_selected.empty:
            missing_names = not_selected["Name"].tolist()
            st.error(
                f"❌ You must select all required parameters before proceeding: {', '.join(missing_names)}"
            )
            st.stop()
        else:
            st.success("✅ All required parameters confirmed.")
            show_weighted_compatibility_score = True
    else:
        show_weighted_compatibility_score = False

    # ✅ MUST-HAVE tamamlandıysa bu bölüm çalışacak
    if (
        "show_weighted_compatibility_score" in locals()
        and show_weighted_compatibility_score
    ):

        st.markdown("##  Weighted Compatibility Score")

        scoring_rows = []

        for idx, row in param_config_df.iterrows():
            if not row.get("Selection", False):
                continue

            param_name = row["Name"].strip()
            if not param_name:
                continue

            weight = float(row["Default Weight"])
            name_key = param_name.lower()

            if name_key == "power capacity match":
                required = uc_demand.get("required_power_mw", 1.0)
            elif name_key == "energy autonomy":
                required = uc_demand.get("required_energy_mwh", 1.0)
            elif name_key == "standards compliance":
                required = 1.0 if uc_demand.get("required_standard") else 0.0
            elif name_key == "vessel gross tonnage":
                required = selected_ship.get("gt", 0)
            elif name_key == "port power capacity":
                required = uc_demand.get("required_power_mw", 1.0)
            elif name_key == "port energy capacity":
                required = uc_demand.get("required_energy_mwh", 1.0)
            else:
                required = st.number_input(
                    f"{param_name} - Required Value",
                    key=f"req_{param_name}",
                    min_value=0.0,
                    value=1.0,
                )

            provided = st.number_input(
                f"{param_name} - Barge Value",
                key=f"barge_{param_name}",
                min_value=0.0,
                value=1.0,
            )
        
            score = compute_score_contribution(required, provided, weight)

            scoring_rows.append(
                {
                    "Parameter": param_name,
                    "Required Value": round(required, 4),
                    "Barge Value": round(provided, 4),
                    "Weight": round(weight, 4),
                    "Score Contribution": score,
                }
            )

        score_df = pd.DataFrame(scoring_rows)

        if not score_df.empty and "Score Contribution" in score_df.columns:
            total_score = round(score_df["Score Contribution"].sum(), 4)

            st.markdown("### 📋 Compatibility Score Table")
            st.table(score_df)

            st.markdown(
                f"### ✅ Total Compatibility Score: `{total_score * 100:.1f} %`"
            )
        else:
            st.warning(
                "⚠️ No valid scoring data. Please select parameters and enter values."
            )


import streamlit as st
import pandas as pd


if st.button("⬅️ Back to Use Case Selection"):
    st.session_state.show_analysis = False
    st.rerun()

    # Placeholder for scoring UI
    st.write("Scoring UI coming soon...")
else:
    st.sidebar.title("Use Case Selection")
    umbrella = st.sidebar.selectbox(
        "Select Umbrella Case", data["umbrella_name"].unique()
    )
    filtered = data[data["umbrella_name"] == umbrella]
    use_case = st.sidebar.selectbox(
        "Select Use Case", filtered["use_case_name"].unique()
    )

    # ✅ Bu kısmın tamamı yalnızca ana sayfada gösterilsin
    if not st.session_state.get("show_analysis", False):
        # Main output
        st.title("Shore Power Compatibility Analysis")
        st.subheader(f"Umbrella Case: {umbrella}")
        st.subheader(f"Use Case: {use_case}")

        # Fetch description
        desc_row = data[
            (data["umbrella_name"] == umbrella) & (data["use_case_name"] == use_case)
        ]
        if not desc_row.empty:
            st.markdown(f"**Description:**\n\n{desc_row.iloc[0]['description']}")
        else:
            st.warning("Description not found.")

        # UC1’e özel alt bölüm
        if use_case == "UC1: Anchored Vessels":
            st.subheader("Anchored Ship Power Demand Lookup")

            try:
                ship_sheet = client.open("Bluebarge_Comp_Texts").worksheet(
                    "Ship Demand"
                )
                ship_demand_df = pd.DataFrame(ship_sheet.get_all_records())
            except Exception as e:
                st.error(f"Failed to load ship demand data: {e}")
                ship_demand_df = None

            if ship_demand_df is not None:
                ship_type = st.selectbox(
                    "Select Ship Type at Anchorage",
                    ship_demand_df["ship_type"].unique(),
                )
                selected = ship_demand_df[
                    ship_demand_df["ship_type"] == ship_type
                ].iloc[0]

                col1, col2 = st.columns([1, 2])

                with col1:
                    st.markdown(
                        f"**Average Anchorage Time**: `{selected['avg_time_h']} hours`"
                    )
                    st.markdown(
                        f"**Total Number of Calls**: `{selected['port_calls (no.)']}`"
                    )

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

                    metric = st.radio(
                        "Select Metric to Compare",
                        [
                            "Anchorage Time (h)",
                            "Number of Port Calls",
                            "Power Demand (MW)",
                            "Energy Demand (MWh)",
                        ],
                    )

                    fig, ax = plt.subplots(figsize=(15, 10))
                    x = np.arange(len(ship_demand_df))
                    bar_labels = ship_demand_df["ship_type"]
                    highlight_color = "#FF5733"
                    default_color = "#AAAAAA"
                    method_colors = {
                        "IMO": "#1f77b4",
                        "EMSA": "#2ca02c",
                        "LF": "#d62728",
                    }
                    width = 0.25

                    if metric == "Anchorage Time (h)":
                        values = ship_demand_df["avg_time_h"]
                        bar_colors = [
                            highlight_color if s == ship_type else default_color
                            for s in ship_demand_df["ship_type"]
                        ]
                        ax.bar(x, values, color=bar_colors)
                        ax.set_ylabel("Hours")
                        ax.set_title("Average Anchorage Time by Ship Type")

                    elif metric == "Number of Port Calls":
                        values = ship_demand_df["port_calls (no.)"]
                        bar_colors = [
                            highlight_color if s == ship_type else default_color
                            for s in ship_demand_df["ship_type"]
                        ]
                        ax.bar(x, values, color=bar_colors)
                        ax.set_ylabel("Calls")
                        ax.set_title("Annual Port Calls")

                    elif metric == "Power Demand (MW)":
                        methods = ["power_imo_mw", "power_emsa_mw", "power_lf_mw"]
                        for i, method in enumerate(methods):
                            label = method.split("_")[1].upper()
                            values = ship_demand_df[method]
                            bar_alphas = [
                                1.0 if s == ship_type else 0.3
                                for s in ship_demand_df["ship_type"]
                            ]
                            bars = ax.bar(
                                x + (i - 1) * width,
                                values,
                                width,
                                label=label,
                                color=method_colors[label],
                                alpha=0.8,
                            )
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
                            bar_alphas = [
                                1.0 if s == ship_type else 0.3
                                for s in ship_demand_df["ship_type"]
                            ]
                            bars = ax.bar(
                                x + (i - 1) * width,
                                values,
                                width,
                                label=label,
                                color=method_colors[label],
                                alpha=0.8,
                            )
                            for bar, alpha in zip(bars, bar_alphas):
                                bar.set_alpha(alpha)
                        ax.set_ylabel("MWh")
                        ax.set_title("Energy Demand by Ship Type and Method")
                        ax.legend()

                    ax.set_xticks(x)
                    ax.set_xticklabels(ship_demand_df["ship_type"], rotation=15)
                    ax.grid(True, linestyle="--", linewidth=0.5, alpha=0.7)
                    st.pyplot(fig)
