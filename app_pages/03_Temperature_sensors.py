# -*- coding: utf-8 -*-
"""
Created on Tue Jun  3 14:46:13 2025

@author: BrunoFantoli
"""
import streamlit as st
import pandas as pd


st.title("Temperature Sensors Data Cleaning")
st.write("This page is designed to help you clean and prepare your temperature sensor data for an upload in Opinum.")
# Load the CSV
uploaded_file = st.file_uploader("Choose a file")

source_id = st.text_input("Enter the source ID")
variable_id = st.text_input("Enter the variable ID")
file_name = st.text_input("Enter the name of the data")

if uploaded_file is not None:
    file_name_lower = uploaded_file.name.lower()
    if file_name_lower.endswith('.csv'):
        # CSV-specific logic
        uploaded_file.seek(0)
        dataframe = pd.read_csv(uploaded_file, header=None, names=["Time", "Temp/°C"], skiprows=1, parse_dates=["Time"], infer_datetime_format=True) # type: ignore
        df = dataframe
        # Can be used wherever a "file-like" object is accepted:
        uploaded_file.seek(0)  # Reset the file pointer to the beginning of the file
        dataframe = pd.read_csv(uploaded_file, header=None, names=["Time", "Temp/°C"], skiprows=1, parse_dates=["Time"], infer_datetime_format=True) # type: ignore
        df = dataframe

        # Force non-parsable dates to NaT (Not a Time)
        df["Time"] = pd.to_datetime(df["Time"], errors='coerce')

        # Drop rows where parsing failed
        df_cleaned = df.dropna(subset=["Time"])

    elif file_name_lower.endswith('.txt'):
        # TXT-specific logic
        uploaded_file.seek(0)
        dataframe = pd.read_csv(uploaded_file, delimiter=",", encoding="latin1", index_col=0) # type: ignore
        df_cleaned = dataframe.reset_index()[["Time", "Celsius(°C)"]]
        

    df_cleaned["source_id"] = source_id # type: ignore
    df_cleaned["variable_id"] = variable_id # type: ignore
    df_cleaned.columns = ["date", "value","source_id", "variable_id"] # type: ignore
    
    # Save the cleaned file (optional)
    output = df_cleaned.to_csv(index=False) # type: ignore
    
    st.download_button(
        label="Download",
        data=output,  # Convert DataFrame to CSV string
        file_name="OpisenseStandardDataFile_"+file_name+".csv",
        mime="text/csv",
        disabled=not (source_id and variable_id)
    )
    if not (source_id and variable_id):
        st.warning("Fill in the Source ID and Variable ID fields to download the file.")
