import streamlit as st

pages = [
    st.Page("app_pages/01_Welcome.py", title="Welcome", icon=":material/home:"),
    st.Page("app_pages/02_EnergyBox.py", title="Energy Box", icon=":material/bolt:"),
    st.Page("app_pages/03_Temperature_sensors.py", title="Temperature Sensors", icon=":material/device_thermostat:")
]

pg = st.navigation(pages, position="sidebar")

pg.run()