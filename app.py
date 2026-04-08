import streamlit as st
import pandas as pd

# 1. PAGE CONFIGURATION
st.set_page_config(page_title="TDS Smart Model V3", layout="wide")

@st.cache_data
def load_data():
    try:
        # Load the renamed Excel file
        df = pd.read_excel("TDS_Master_Data.xlsx", engine='openpyxl')
        
        # CLEANING HEADERS
        df.columns = [c.strip() for c in df.columns]
        
        # CLEANING DATA: Removes hidden spaces from text columns to ensure matching works
        df = df.apply(lambda x: x.str.strip() if x.dtype == "object" else x)
        
        # DATE HANDLING
        df['Effective From'] = pd.to_datetime(df['Effective From'], errors='coerce')
        df['Effective To'] = pd.to_datetime(df['Effective To'], errors='coerce').fillna(pd.Timestamp('2099-12-31'))
        
        return df
    except Exception as e:
        st.error(f"Excel Load Error: {e}. Please ensure 'TDS_Master_Data.xlsx' is uploaded to GitHub.")
        return None

# Load the data
df = load_data()

if df is not None:
    st.title("🏛️ TDS Calculation Portal - Advanced V3")
    st.markdown("### *Dynamic Asset & Threshold Compliance Model*")
    st.write("---")

    # 2. USER INPUT SECTION
    col1, col2 = st.columns(2)

    with col1:
        st.info("📊 **Transaction Details**")
        # Section selection
        sections = sorted([s for s in df['Section'].unique() if str(s) != 'nan'])
        section = st.selectbox("1. Select Income Tax Section", options=sections)
        
        # Filter data for the selected section to get Nature of Payment options
        filtered_df = df[df['Section'] == section]
        nature_options = sorted([n for n in filtered_df['Nature of Payment'].unique() if str(n) != 'nan'])
        nature_selection = st.selectbox("2. Nature of Payment (Asset Type)", options=nature_options)
        
        # Amount input
        amount = st.number_input("3. Enter Amount (INR)", min_value=0.0, step=1000.0, value=250000.0)

    with col2:
        st.info("👤 **Compliance Parameters**")
        # PAN status
        pan_status = st.radio("4. Does the Payee have a PAN?", ["Yes", "No"])
        
        # Date selection
        pay_date = st.date_input("5. Transaction Date")
        
        # Calculation Mode (Single vs Aggregate)
        calc_mode = st.radio("6. Threshold Calculation Basis:", ["Single Transaction", "Aggregate (Full Year)"])

    st.write("---")
    
    # 3. CALCULATION & RESULT SECTION
    if st.button("🚀 Run Compliance Check"):
        target = pd.to_datetime(pay_date)
        
        # Match the specific row in Excel
        match = filtered_df[filtered_df['Nature of Payment'] == nature_selection]
        
        # Filter by Date Range
        rule = match[(match['Effective From'] <= target) & (match['Effective To'] >= target)]
        
        # Fallback to latest if date range doesn't match perfectly
        if rule.empty and not match.empty:
            rule = match.sort_values(by='Effective From', ascending=False).head(1)

        if not rule.empty:
            sel = rule.iloc[0]
            rate_raw = str(sel['Rate of TDS (%)']).strip().lower()
            
            # Special case for Salaries (Section 192) or Bank Interest (Section 194P)
            if rate_raw == 'avg':
                st.info(f"💡 **Note for {section}:** {sel['Notes']}")
            else:
                try:
                    # Pull values from Excel
                    base_rate = float(sel['Rate of TDS (%)'])
                    # Apply 20% penalty if PAN is missing
                    final_rate = 20.0 if pan_status == "No" else base_rate
                    
                    # Pull threshold from Excel
                    threshold = float(
