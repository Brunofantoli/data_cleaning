import streamlit as st
import pandas as pd
import numpy as np
import io
import logging
from datetime import datetime, timedelta

# Set up logging
logging.basicConfig(level=logging.WARNING)

st.title("Consumption Data")
st.write("This page is designed to help you manage and analyze consumption data received from clients.")
st.write("You can upload a the file received from the client and it will be processed and cleaned for excel use.")
st.write("THIS PAGE IS STILL BEING DEVELOPED.")


def load_file(uploaded_file):
    """
    Load a CSV or XLSX file into a DataFrame.
    Auto-detects file type and tries to guess delimiter for CSV.
    """
    file_name = uploaded_file.name
    if file_name.lower().endswith('.csv'):
        # Try to detect delimiter
        import csv
        first_bytes = uploaded_file.read(2048).decode('utf-8')
        uploaded_file.seek(0)
        sniffer = csv.Sniffer()
        try:
            dialect = sniffer.sniff(first_bytes)
            delimiter = dialect.delimiter
        except Exception:
            delimiter = ';'  # fallback for European CSVs
        df = pd.read_csv(uploaded_file, delimiter=delimiter)
    elif file_name.lower().endswith(('.xls', '.xlsx')):
        df = pd.read_excel(uploaded_file)
    else:
        st.warning(f"Unsupported file type: {file_name}")
        return None
    df['source_file'] = file_name
    return df

def detect_datetime_column(df):
    """
    Try to find the column containing date/time information.
    """
    for col in df.columns:
        if any(x in col.lower() for x in ['date', 'time', 'timestamp']):
            return col
    # Fallback: try first column
    return df.columns[0]

def standardize_dates(df, datetime_col):
    """
    Standardize date/time column to pandas datetime.
    Handles common formats, Excel serial dates, UNIX timestamps.
    Tries dayfirst=True for European-style dates.
    """
    # Try direct conversion (default: monthfirst)
    df['timestamp'] = pd.to_datetime(df[datetime_col], errors='coerce')
    
    # If many NaT, try dayfirst=True
    if df['timestamp'].isna().sum() > len(df) // 2:
        df['timestamp'] = pd.to_datetime(df[datetime_col], errors='coerce', dayfirst=True)

    # Try Excel serial dates if still mostly NaT
    if df['timestamp'].isna().sum() > len(df) // 2:
        try:
            df['timestamp'] = pd.to_datetime(df[datetime_col], unit='D', origin='1899-12-30', errors='coerce')
        except Exception:
            pass

    # Try UNIX timestamps if still mostly NaT
    if df['timestamp'].isna().sum() > len(df) // 2:
        try:
            df['timestamp'] = pd.to_datetime(df[datetime_col], unit='s', errors='coerce')
        except Exception:
            pass

    return df

def detect_consumption_column(df):
    """
    Try to find the column containing consumption values.
    Only select columns with numeric-like data.
    """
    for col in df.columns:
        if any(x in col.lower() for x in ['consumption', 'kwh', 'energy', 'value', 'usage']):
            # Check if column is numeric-like
            sample = df[col].astype(str).str.replace(',', '.', regex=False)
            numeric_sample = pd.to_numeric(sample, errors='coerce')
            if numeric_sample.notna().sum() > 0:
                return col
    # Fallback: try second column if it's numeric
    if len(df.columns) > 1:
        sample = df[df.columns[1]].astype(str).str.replace(',', '.', regex=False)
        numeric_sample = pd.to_numeric(sample, errors='coerce')
        if numeric_sample.notna().sum() > 0:
            return df.columns[1]
    return None

def infer_frequency(timestamps):
    """
    Infer the most common frequency in the timestamp series.
    """
    diffs = timestamps.sort_values().diff().dropna()
    if diffs.empty:
        return None
    freq = diffs.mode()[0]
    # Map timedelta to pandas offset string
    if freq <= timedelta(minutes=1):
        return 'T'
    elif freq <= timedelta(minutes=15):
        return '15T'
    elif freq <= timedelta(hours=1):
        return 'H'
    elif freq <= timedelta(days=1):
        return 'D'
    else:
        return None

def handle_missing_data(df, freq, consumption_col, impute_strategy='auto'):
    """
    Handle missing data:
    - If cumulative, distribute the difference over missing intervals.
    - If interval, set missing to NaN or zero.
    - impute_strategy: 'auto', 'distribute', 'zero', 'nan'
    """
    df = df.sort_values('timestamp')
    df = df.groupby('timestamp', as_index=False).first()
    idx = pd.date_range(df['timestamp'].min(), df['timestamp'].max(), freq=freq)
    df = df.set_index('timestamp').reindex(idx)
    df['timestamp'] = df.index

    # Standardize decimal separator and convert to float safely
    df[consumption_col] = (
        df[consumption_col]
        .astype(str)
        .str.strip()  # Remove leading/trailing whitespace
        .replace({'': np.nan, ' ': np.nan})  # Treat empty and space as NaN
        .str.replace(',', '.', regex=False)
    )
    df[consumption_col] = pd.to_numeric(df[consumption_col], errors='coerce')

    consumption = df[consumption_col]

    # Detect cumulative: monotonic increasing, large jumps
    is_cumulative = consumption.dropna().is_monotonic_increasing

    # Choose imputation strategy
    if impute_strategy == 'auto':
        strategy = 'distribute' if is_cumulative else 'nan'
    else:
        strategy = impute_strategy

    if strategy == 'distribute' and is_cumulative:
        df['consumption_kWh'] = distribute_cumulative(df, consumption_col)
    elif strategy == 'zero':
        df['consumption_kWh'] = consumption.fillna(0)
    else:  # 'nan'
        df['consumption_kWh'] = consumption

    # Flag missing/irregular data
    df['missing_flag'] = df['consumption_kWh'].isna() | df['consumption_kWh'].le(0)
    return df

def distribute_cumulative(df, consumption_col):
    """
    For cumulative data, fill missing values by distributing the difference
    between previous and next valid readings equally across all missing intervals.
    """
    consumption = df[consumption_col].copy()
    result = np.zeros(len(consumption))
    i = 0
    while i < len(consumption):
        if pd.isna(consumption.iloc[i]):
            # Find previous valid value
            prev_idx = i - 1
            while prev_idx >= 0 and pd.isna(consumption.iloc[prev_idx]):
                prev_idx -= 1
            prev_val = consumption.iloc[prev_idx] if prev_idx >= 0 else 0

            # Find next valid value
            next_idx = i
            while next_idx < len(consumption) and pd.isna(consumption.iloc[next_idx]):
                next_idx += 1
            if next_idx < len(consumption):
                next_val = consumption.iloc[next_idx]
                n_missing = next_idx - prev_idx
                if n_missing > 0:
                    interval = (next_val - prev_val) / n_missing
                    for j in range(prev_idx + 1, next_idx + 1):
                        result[j] = interval
                i = next_idx + 1
            else:
                # No next valid value, fill remaining with NaN
                for j in range(prev_idx + 1, len(consumption)):
                    result[j] = np.nan
                break
        else:
            if i > 0:
                result[i] = consumption.iloc[i] - consumption.iloc[i - 1]
            else:
                result[i] = consumption.iloc[i]
            i += 1
    return result

def clean_and_merge(files, freq):
    """
    Load, clean, and merge multiple files into a standardized DataFrame.
    """
    dfs = []
    for uploaded_file in files:
        df = load_file(uploaded_file)
        if df is None:
            continue
        datetime_col = detect_datetime_column(df)
        df = standardize_dates(df, datetime_col)
        consumption_col = detect_consumption_column(df)
        if consumption_col is None:
            st.warning(f"Could not detect consumption column in {uploaded_file.name}")
            continue
        # Infer frequency if not provided
        inferred_freq = infer_frequency(df['timestamp'].dropna())
        use_freq = freq if freq else inferred_freq if inferred_freq else 'H'
        df = handle_missing_data(df, use_freq, consumption_col)
        dfs.append(df[['timestamp', 'consumption_kWh', 'source_file', 'missing_flag']])
    if dfs:
        merged = pd.concat(dfs, ignore_index=True)
        merged = merged.sort_values('timestamp').reset_index(drop=True)
        return merged
    else:
        return pd.DataFrame(columns=['timestamp', 'consumption_kWh', 'source_file', 'missing_flag'])

# --- Streamlit UI ---
uploaded_files = st.file_uploader("Upload CSV/XLSX files", accept_multiple_files=True)
freq_options = {'15 min': '15T', 'Hourly': 'H', 'Daily': 'D'}
freq_label = st.selectbox("Aggregation frequency", list(freq_options.keys()), index=1)
freq = freq_options[freq_label]

impute_strategy = st.selectbox(
    "Missing data handling strategy",
    ["auto", "distribute (for cumulative)", "zero (set missing to 0)", "nan (leave missing as NaN)"],
    index=0
)
impute_map = {
    "auto": "auto",
    "distribute (for cumulative)": "distribute",
    "zero (set missing to 0)": "zero",
    "nan (leave missing as NaN)": "nan"
}

if uploaded_files:
    # Load first file to get columns for selection
    df_preview = load_file(uploaded_files[0])
    if df_preview is not None:
        st.write("Preview of uploaded file:", df_preview.head())
        detected_col = detect_consumption_column(df_preview)
        if detected_col is not None:
            consumption_cols = st.multiselect(
                "Select consumption column(s) to process",
                options=df_preview.columns,
                default=[detected_col]
            )
        else:
            consumption_cols = st.multiselect(
                "Select consumption column(s) to process",
                options=df_preview.columns
            )
    else:
        consumption_cols = []

    cleaned_dfs = []
    for uploaded_file in uploaded_files:
        df = load_file(uploaded_file)
        if df is None:
            continue
        datetime_col = detect_datetime_column(df)
        df = standardize_dates(df, datetime_col)
        # Use user-selected columns if available, else auto-detect
        for consumption_col in consumption_cols if consumption_cols else [detect_consumption_column(df)]:
            if consumption_col is None:
                st.warning(f"Could not detect consumption column in {uploaded_file.name}")
                continue
            inferred_freq = infer_frequency(df['timestamp'].dropna())
            use_freq = freq if freq else inferred_freq if inferred_freq else 'H'
            df_clean = handle_missing_data(df, use_freq, consumption_col, impute_map[impute_strategy])
            cleaned_dfs.append(df_clean[['timestamp', 'consumption_kWh', 'source_file', 'missing_flag']])

    if cleaned_dfs:
        merged = pd.concat(cleaned_dfs, ignore_index=True)
        merged = merged.sort_values('timestamp').reset_index(drop=True)
        st.write("Preview of standardized dataset:", merged.head())
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            merged.to_excel(writer, index=False, sheet_name='Standardized')
        output.seek(0)
        st.download_button(
            label="Download standardized dataset (Excel)",
            data=output,
            file_name="Standardized_Energy_Data.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )