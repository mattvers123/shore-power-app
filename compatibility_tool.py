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
