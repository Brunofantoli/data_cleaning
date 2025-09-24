import streamlit as st
import pandas as pd

st.title("General File Import for Opinum Upload")
st.write("This page allows you to upload any data file (CSV, Excel) and convert selected variables into the Opinum standard format for easy upload.")
st.write("Please ensure your data includes a date/time column and the variables you wish to upload in different columns.")

uploaded_file = st.file_uploader("Upload your data file (CSV, Excel, etc.)", type=["csv", "xlsx", "xls"]) 

df = None
if uploaded_file:
    if uploaded_file.name.endswith('.csv'):
        df = pd.read_csv(uploaded_file)
    elif uploaded_file.name.endswith(('.xlsx', '.xls')):
        df = pd.read_excel(uploaded_file)
    else:
        st.error("Unsupported file type.")

if df is not None:
    #st.write("Preview of uploaded data:")
    #st.dataframe(df.head())
    columns = list(df.columns)
    variable_columns = st.multiselect(
        "Select variables to upload (including date/time column):",
        columns
    )
    if variable_columns:
        #st.write("You selected:", variable_columns)
        date_col = st.selectbox("Select the date/time column:", columns, key="date_col")
        for var in variable_columns:
            if var == date_col:
                continue
            st.subheader(f"Settings for variable: {var}")
            source_id = st.text_input(f"Source ID for {var}", key=f"source_{var}")
            variable_id = st.text_input(f"Variable ID for {var}", key=f"varid_{var}")
            file_name = st.text_input(f"Optional file name for {var}", key=f"fname_{var}")
            # Prepare Opinum format: Date, Value, Source ID, Variable ID
            out_df = pd.DataFrame({
                "date": df[date_col],
                "value": df[var],
                "source_id": source_id,
                "variable_id": variable_id
            })
            # File naming as in EnergyBox: OpisenseStandardDataFile_<name>.csv
            out_file_name = f"OpisenseStandardDataFile_{file_name if file_name else var}.csv"
            csv_data = out_df.to_csv(index=False)
            st.download_button(
                label=f"Download CSV for '{var}'",
                data=csv_data,
                file_name=out_file_name,
                mime="text/csv",
                key=f"download_{var}",
                disabled=not (source_id and variable_id)
            )

else:
    st.info("Please upload a file to begin.")
