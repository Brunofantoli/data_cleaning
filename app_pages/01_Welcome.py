import streamlit as st

st.title("Welcome to this Data Cleaning Application!")
st.write("This app is designed to help you manage and analyze your energy data efficiently.")

st.write("Choose the sensor you want to convert data from:")
st.page_link("app_pages/02_EnergyBox.py", label="Energy Box", icon=":material/bolt:")
st.page_link("app_pages/03_Temperature_sensors.py", label="Temperature Sensors", icon=":material/device_thermostat:")