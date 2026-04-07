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
        
        # CLEANING DATA: The "New" way that avoids the 'applymap' error
        # This removes hidden spaces from every cell in the spreadsheet
        df = df.apply(lambda x: x.str.strip() if x.dtype == "object" else x)
        
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
        
        filtered_df = df[df['Section'] == section]
        
        nature_options = sorted([n for n in filtered_df['Nature of Payment'].unique() if str(n) != 'nan'])
        nature_selection = st.selectbox("2. Nature of Payment", options=nature_options)

    with col2:
        amount = st.number_input("3. Amount (INR)", min_value=0.0)
        pan_status = st.radio("4. PAN Available?", ["Yes", "No"])
        pay_date = st.date_input("5. Transaction Date")
        calc_mode = st.radio("Basis:", ["Single Transaction", "Aggregate (Full Year)"])

    st.write("---")
    
    # 3. CALCULATION LOGIC
    if st.button("🚀 Calculate"):
        target = pd.to_datetime(pay_date)
        
        # Match Section and Nature of Payment exactly
        match = filtered_df[filtered_df['Nature of Payment'] == nature_selection]
        
        # Filter by Date
        rule = match[(match['Effective From'] <= target) & (match['Effective To'] >= target)]
        
        # Fallback to the most recent entry if date match fails
        if rule.empty and not match.empty:
            rule = match.sort_values(by='Effective From', ascending=False).head(1)

        if not rule.empty:
            sel = rule.iloc[0]
            rate_raw = str(sel['Rate of TDS (%)']).strip().lower()
            
            if rate_raw == 'avg':
                st.info(f"💡 **Salary/Specified Bank Note:** {sel['Notes']}")
            else:
                try:
                    # Convert values to float for math
                    base = float(sel['Rate of TDS (%)'])
                    final_rate = 20.0 if pan_status == "No" else base
                    thresh = float(sel['Threshold Amount (Rs)'])
                    
                    # 194C Aggregate Logic override
                    if section == "194C" and calc_mode == "Aggregate (Full Year)":
                        thresh = 100000.0
                    
                    if amount > thresh:
                        tax = (amount * final_rate) / 100
                        st.success(f"### Result: Deduct ₹{tax:,.2f}")
                        st.write(f"**Applied Rate:** {final_rate}% | **Limit:** ₹{thresh:,.0f}")
                    else:
                        st.warning(f"### Result: No TDS Required")
                        st.write(f"Amount is below the threshold of **₹{thresh:,.0f}**.")
                except Exception as e:
                    st.error(f"Calculation Error: Check your Excel values. {e}")
        else:
            st.error("❌ No matching rule found. Check if 'Nature of Payment' is spelled correctly in Excel.")
