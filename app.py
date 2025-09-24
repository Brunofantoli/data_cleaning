import streamlit as st
pages = [
    st.Page("app_pages/01_Welcome.py", title="Welcome", icon=":material/home:"),
    st.Page("app_pages/02_EnergyBox.py", title="Energy Box", icon=":material/bolt:"),
    st.Page("app_pages/03_Temperature_sensors.py", title="Temperature Sensors", icon=":material/device_thermostat:"),
    st.Page("app_pages/04_ConsumptionData.py", title="Consumption Data", icon=":material/attach_money:"),
    st.Page("app_pages/05_ImportAnyFile.py", title="Import Any File", icon=":material/all_inclusive:")
]

pg = st.navigation(pages, position="sidebar")

pg.run()