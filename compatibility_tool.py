import streamlit as st

st.title("Shore Power Compatibility Analyzer")

# Step 1: Select application
application = st.selectbox("Select Application", ["Ship", "Island", "Disaster Relief", "Offshore Platform"])

# Step 2: Define power demand
st.header("Power Requirements")
power_kw = st.number_input("Total Power Demand (kW)", min_value=0)

# Conditional inputs based on app
if application == "Ship":
    st.subheader("Ship-specific Inputs")
    voltage = st.selectbox("Voltage Level", ["440V", "6.6kV", "11kV"])
    freq = st.selectbox("Frequency", ["50 Hz", "60 Hz"])

# Placeholder for compatibility output
if st.button("Analyze Compatibility"):
    st.success("Analysis complete! (placeholder)")
