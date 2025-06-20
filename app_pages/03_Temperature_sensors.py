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
    # Can be used wherever a "file-like" object is accepted:
    uploaded_file.seek(0)  # Reset the file pointer to the beginning of the file
    dataframe = pd.read_csv(uploaded_file, header=None, names=["Time", "Temp/°C"], skiprows=1, parse_dates=["Time"], infer_datetime_format=True)
    df = dataframe

    # Force non-parsable dates to NaT (Not a Time)
    df["Time"] = pd.to_datetime(df["Time"], errors='coerce')

    # Drop rows where parsing failed
    df_cleaned = df.dropna(subset=["Time"])
    
    df_cleaned["source_id"] = source_id
    df_cleaned["variable_id"] = variable_id
    
    df_cleaned.columns = ["date", "value","source_id", "variable_id"]
    
    # Save the cleaned file (optional)
    output = df_cleaned.to_csv(index=False)
    
    st.download_button(
        label="Download",
        data=output,  # Convert DataFrame to CSV string
        file_name="OpisenseStandardDataFile_"+file_name+".csv",
        mime="text/csv",
        disabled=not (source_id and variable_id)
    )
    if not (source_id and variable_id):
        st.warning("Fill in the Source ID and Variable ID fields to download the file.")
