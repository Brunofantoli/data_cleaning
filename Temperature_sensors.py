# -*- coding: utf-8 -*-
"""
Created on Tue Jun  3 14:46:13 2025

@author: BrunoFantoli
"""
import streamlit as st
import pandas as pd

# Load the CSV
uploaded_file = st.file_uploader("Choose a file")

source_id = st.text_input("Enter the source ID")
variable_id = st.text_input("Enter the variable ID")
file_name = st.text_input("Enter the name of the data")

if uploaded_file is not None:
    # Can be used wherever a "file-like" object is accepted:
    dataframe = pd.read_csv(uploaded_file)

    df = dataframe
    
    # Keep only rows with full timestamps (format: 'YYYY-MM-DD HH:MM:SS')
    df_cleaned = df[df["Time"].str.match(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}")]
    
    df_cleaned["source_id"] = source_id
    df_cleaned["variable_id"] = variable_id
    
    df_cleaned.columns = ["date", "value","source_id", "variable_id"]
    
    # Save the cleaned file (optional)
    output = df_cleaned.to_csv(index=False)
    
    st.download_button(
        label="Download cleaned CSV",
        data=output,  # Convert DataFrame to CSV string
        file_name="OpisenseStandardDataFile_"+file_name+".csv",
        mime="text/csv",
    )
