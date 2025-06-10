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

    # Let user select columns (except 'date')
    available_columns = [col for col in df_cleaned.columns if col != "date"]
    selected_columns = st.multiselect(
        "Select the data you want to import into Opinum",
        options=available_columns
    )

    # Always include 'date' column
    columns_to_show = ["date"] + selected_columns
    df_cleaned = df_cleaned[columns_to_show]

    file_name = st.text_input("Enter the base name for the files (optionnal)")
    if not file_name:
        file_name = "EnergyBox"

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

    # Download Excel file with all selected columns
    if used_in_excel and selected_columns:
        excel_buffer = io.BytesIO()
        df_excel = df_cleaned.copy()
        # Convert 'date' column to datetime for Excel compatibility
        df_excel['date'] = pd.to_datetime(df_excel['date'], errors='coerce')
        # Optionally, format as string if you want a specific format:
        # df_excel['date'] = df_excel['date'].dt.strftime('%Y-%m-%d %H:%M:%S')
        df_excel.to_excel(excel_buffer, index=False)
        excel_buffer.seek(0)
        st.download_button(
            label="Download file for Excel",
            data=excel_buffer,
            file_name=f"{file_name}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="download_excel"
        )