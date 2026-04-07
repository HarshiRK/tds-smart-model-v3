import streamlit as st
import pandas as pd

st.set_page_config(page_title="TDS Smart Model V3", layout="wide")

@st.cache_data
def load_data():
    try:
        # Load the Excel file
        df = pd.read_excel("TDS_Master_Data.xlsx", engine='openpyxl')
        
        # CLEANING HEADERS
        df.columns = [c.strip() for c in df.columns]
        
        # CLEANING DATA: Removing hidden spaces from every single cell
        df = df.applymap(lambda x: x.strip() if isinstance(x, str) else x)
        
        # Ensure dates are working
        df['Effective From'] = pd.to_datetime(df['Effective From'], errors='coerce')
        df['Effective To'] = pd.to_datetime(df['Effective To'], errors='coerce').fillna(pd.Timestamp('2099-12-31'))
        
        return df
    except Exception as e:
        st.error(f"Excel Load Error: {e}")
        return None

df = load_data()

if df is not None:
    st.title("🏛️ TDS Smart Model V3")
    st.write("---")

    col1, col2 = st.columns(2)

    with col1:
        sections = sorted([s for s in df['Section'].unique() if str(s) != 'nan'])
        section = st.selectbox("1. Select Section", options=sections)
        
        # Filter for the selected section
        filtered_df = df[df['Section'] == section]
        
        # NATURE OF PAYMENT - This is the key for 194I
        nature_options = sorted([n for n in filtered_df['Nature of Payment'].unique() if str(n) != 'nan'])
        nature_selection = st.selectbox("2. Nature of Payment", options=nature_options)

    with col2:
        amount = st.number_input("3. Amount (INR)", min_value=0.0)
        pan_status = st.radio("4. PAN Available?", ["Yes", "No"])
        pay_date = st.date_input("5. Transaction Date")
        calc_mode = st.radio("Basis:", ["Single Transaction", "Aggregate (Full Year)"])

    if st.button("🚀 Calculate"):
        target = pd.to_datetime(pay_date)
        
        # STEP 1: Find the exact row matching Section AND Nature
        match = filtered_df[filtered_df['Nature of Payment'] == nature_selection]
        
        # STEP 2: Filter by Date
        rule = match[(match['Effective From'] <= target) & (match['Effective To'] >= target)]
        
        # If no date match, take the latest one
        if rule.empty and not match.empty:
            rule = match.sort_values(by='Effective From', ascending=False).head(1)

        if not rule.empty:
            sel = rule.iloc[0]
            rate_raw = str(sel['Rate of TDS (%)']).strip().lower()
            
            if rate_raw == 'avg':
                st.info(f"💡 {sel['Notes']}")
            else:
                try:
                    base = float(sel['Rate of TDS (%)'])
                    final_rate = 20.0 if pan_status == "No" else base
                    thresh = float(sel['Threshold Amount (Rs)'])
                    
                    # 194C Aggregate Logic
                    if section == "194C" and calc_mode == "Aggregate (Full Year)":
                        thresh = 100000.0
                    
                    if amount > thresh:
                        tax = (amount * final_rate) / 100
                        st.success(f"### Deduct: ₹{tax:,.2f}")
                        st.write(f"**Section:** {section} | **Rate:** {final_rate}%")
                    else:
                        st.warning(f"Below Threshold (Limit: ₹{thresh:,.0f})")
                except Exception as e:
                    st.error(f"Calculation Error: Check if Rate/Threshold are numbers in Excel. Error: {e}")
        else:
            # THIS PREVENTS THE BLANK SCREEN
            st.error("❌ No matching rule found in the Excel for this combination.")
            st.info("Check if the 'Nature of Payment' matches exactly between your selection and the Excel row.")
