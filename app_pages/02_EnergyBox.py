# -*- coding: utf-8 -*-
"""
Created on Tue Jun  3 14:46:13 2025

@author: BrunoFantoli
"""
import streamlit as st
import pandas as pd
import re
import io
import zipfile

st.title("Energy Box Data Cleaning")
st.write("This page is designed to help you manage and analyze data from the Energy Box.")
st.write("You can upload a CSV file downloaded from the Energy Box, select the data you want to import into Opinum, and download the cleaned data in the correct format.")
st.write("You can also download an Excel file from the Electricity analysis template.")

# Load the CSV
used_in_opinum = st.checkbox("The data will be used in Opinum")
used_in_excel = st.checkbox("The data will be used in excel")

uploaded_file = st.file_uploader("Choose a file")

if uploaded_file is not None:
    # Can be used wherever a "file-like" object is accepted:
    dataframe = pd.read_csv(uploaded_file,skiprows=[0])
    df = dataframe

    # Clean the DataFrame
    df_cleaned = df.drop(columns=['No.'])
    df_cleaned = df_cleaned.iloc[:, :-1]
    df_cleaned = df_cleaned.rename(columns={"Time Stamp": "date"})
    # Remove '(float)' from all column names
    df_cleaned.columns = df_cleaned.columns.str.replace('(float)', '', regex=False).str.strip()
    
    file_name = st.text_input("Enter the base name for the files (optionnal)")
    if not file_name:
        file_name = "EnergyBox"

    # Download Excel file with all columns (selected and unselected)
    if used_in_excel:
        st.markdown("#### Download file for Excel")
        st.markdown("###### Specify Occupancy Profile for a Typical Week")
        week_days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        occupancy_profiles = []

        add_profile = True
        profile_idx = 0
        used_days = set()
        while add_profile:
            available_days = [d for d in week_days if d not in used_days]
            if not available_days:
                break
            selected_days = st.multiselect(
                f"Select days for occupancy profile #{profile_idx+1}",
                options=available_days,
                key=f"occ_days_{profile_idx}"
            )
            if selected_days:
                open_time = st.time_input(
                    f"Opening time for {', '.join(selected_days)}",
                    value=pd.to_datetime("08:00").time(),
                    key=f"open_{profile_idx}"
                )
                close_time = st.time_input(
                    f"Closing time for {', '.join(selected_days)}",
                    value=pd.to_datetime("18:00").time(),
                    key=f"close_{profile_idx}"
                )
                occupancy_profiles.append({
                    "days": selected_days,
                    "open": open_time,
                    "close": close_time
                })
                used_days.update(selected_days)
            add_profile = st.checkbox(
                "Add another occupancy profile",
                key=f"add_profile_{profile_idx}"
            )
            if add_profile:
                profile_idx += 1

        # --- Compute 'occupied' column for Excel export ---
        def is_occupied(row, profiles):
            weekday = row['date'].strftime("%A")
            time = row['date'].time()
            for prof in profiles:
                if weekday in prof['days']:
                    if prof['open'] <= time <= prof['close']:
                        return True
            return False

        st.markdown("###### Specify On-Peak Hours")
        if st.checkbox("The peak-time is different from 7:00 to 22:00"):
            on_peak_start = st.time_input("On-peak start time", value=pd.to_datetime("07:00").time(), key="on_peak_start")
            on_peak_end = st.time_input("On-peak end time", value=pd.to_datetime("22:00").time(), key="on_peak_end")
        else:
            on_peak_start = pd.to_datetime("07:00").time()
            on_peak_end = pd.to_datetime("22:00").time()

        weekends_on_peak = st.checkbox("Weekends are considered on-peak", key="weekends_on_peak", value=False)

        excel_buffer = io.BytesIO()
        # Use the full df (not just selected columns)
        df_excel = df_cleaned.copy()
        df_excel = df_excel.rename(columns={"Time Stamp": "date"})
        df_excel.columns = df_excel.columns.str.replace('(float)', '', regex=False).str.strip()
        df_excel['date'] = pd.to_datetime(df_excel['date'], errors='coerce')
        df_excel['is_weekend'] = df_excel['date'].dt.weekday >= 5

        if weekends_on_peak:
            df_excel['on_peak'] = df_excel['date'].dt.time.between(on_peak_start, on_peak_end) # type: ignore
        else:
            df_excel['on_peak'] = (~df_excel['is_weekend']) & df_excel['date'].dt.time.between(on_peak_start, on_peak_end) # type: ignore

        df_excel['occupied'] = df_excel.apply(lambda row: is_occupied(row, occupancy_profiles), axis=1)
        # Insert 'occupied' after 'date'
        cols = list(df_excel.columns)
        if 'occupied' in cols:
            cols.insert(cols.index('date') + 1, cols.pop(cols.index('occupied')))
            df_excel = df_excel[cols]

        # Update desired_order to include 'occupied' after 'date'
        desired_order = [
            "date", "occupied", "on_peak", "Frequency  [Hz]", "I A  [A]", "I B  [A]", "I C  [A]", "I N  [A]", "I Average  [A]",
            "Pwr Factor A", "Pwr Factor B", "Pwr Factor C", "Pwr Factor Total",
            "VA A  [kVA]", "VA B  [kVA]", "VA C  [kVA]", "VA Total  [kVA]",
            "Volts AN  [V]", "Volts BN  [V]", "Volts CN  [V]", "Volts LN Average  [V]",
            "Volts AB  [V]", "Volts BC  [V]", "Volts CA  [V]", "Volts LL Average  [V]",
            "Watt A  [kW]", "Watt B  [kW]", "Watt C  [kW]", "Watt Total  [kW]"
        ]

        # Ensure all columns in desired_order are present, fill missing with blanks
        for col in desired_order:
            if col not in df_excel.columns:
                df_excel[col] = ""
        final_cols = desired_order  # Only use desired_order, no extras
        
        # Reorder the DataFrame to match the desired order
        df_excel = df_excel[final_cols]

        df_excel.to_excel(excel_buffer, index=False)
        excel_buffer.seek(0)
        st.download_button(
            label="Download file for Excel",
            data=excel_buffer,
            file_name=f"{file_name}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="download_excel"
        )

    st.markdown('--------------------------------------')
    # Let user select columns (except 'date')
    available_columns = [col for col in df_cleaned.columns if col != "date"]
    selected_columns = st.multiselect(
        "Select the data you want to import into Opinum",
        options=available_columns
    )

    # Always include 'date' column
    columns_to_show = ["date"] + selected_columns
    df_cleaned = df_cleaned[columns_to_show]



    previous_source_id = None
    for idx, col in enumerate(selected_columns):
        # Remove unit in brackets from variable name
        col_no_unit = re.sub(r"\s*\[.*?\]", "", col).strip()
        st.markdown(f"#### Settings for `{col_no_unit}`")
        if idx > 0:
            same_as_prev = st.checkbox(
                f"Source ID for '{col}' same as previous ('{selected_columns[idx-1]}')",
                key=f"same_prev_{col}",
                value=True 
            )
        else:
            same_as_prev = False

        if same_as_prev and previous_source_id is not None:
            source_id = previous_source_id
            st.info(f"Source ID for '{col}' set to '{source_id}' (same as previous)")
        else:
            source_id = st.text_input(f"Source ID for '{col}'", key=f"src_{col}")

        variable_id = st.text_input(f"Variable ID for '{col}'", key=f"var_{col}")

        previous_source_id = source_id  # Update for next iteration

        df_out = pd.DataFrame({
            "date": df_cleaned["date"],
            "value": df_cleaned[col],
            "source_id": source_id,
            "variable_id": variable_id
        })

        output = df_out.to_csv(index=False)
        st.download_button(
            label=f"Download CSV for '{col}'",
            icon = ":material/download:",
            data=output,
            file_name=f"OpisenseStandardDataFile_{file_name}_{col}.csv",
            mime="text/csv",
            key=f"download_{col}",
            disabled=not (source_id and variable_id)
        )
    st.markdown('--------------------------------------')
    # Download all files for Opinum as ZIP
    if used_in_opinum and selected_columns:
        # Check if all source_id and variable_id are set
        all_ids_set = True
        previous_source_id = None
        for idx, col in enumerate(selected_columns):
            if idx > 0:
                same_as_prev = st.session_state.get(f"same_prev_{col}", False)
            else:
                same_as_prev = False
            if same_as_prev and previous_source_id is not None:
                source_id = previous_source_id
            else:
                source_id = st.session_state.get(f"src_{col}", "")
            variable_id = st.session_state.get(f"var_{col}", "")
            if not source_id or not variable_id:
                all_ids_set = False
            previous_source_id = source_id

        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w") as zip_file:
            previous_source_id = None
            for idx, col in enumerate(selected_columns):
                col_no_unit = re.sub(r"\s*\[.*?\]", "", col).strip()
                if idx > 0:
                    same_as_prev = st.session_state.get(f"same_prev_{col}", False)
                else:
                    same_as_prev = False
                if same_as_prev and previous_source_id is not None:
                    source_id = previous_source_id
                else:
                    source_id = st.session_state.get(f"src_{col}", "")
                variable_id = st.session_state.get(f"var_{col}", "")
                previous_source_id = source_id
                df_out = pd.DataFrame({
                    "date": df_cleaned["date"],
                    "value": df_cleaned[col],
                    "source_id": source_id,
                    "variable_id": variable_id
                })
                csv_bytes = df_out.to_csv(index=False).encode("utf-8")
                zip_file.writestr(f"OpisenseStandardDataFile_{file_name}_{col}.csv", csv_bytes)
        zip_buffer.seek(0)
        st.download_button(
            label="Download all files for Opinum (ZIP)",
            data=zip_buffer,
            file_name=f"{file_name}_Opinum.zip",
            mime="application/zip",
            key="download_all_opinum",
            disabled=not all_ids_set
        )
        if not all_ids_set:
            st.warning("Fill in all Source ID and Variable ID fields to download the files.")

