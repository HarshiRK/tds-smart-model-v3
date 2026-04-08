import streamlit as st
import pandas as pd

st.set_page_config(page_title="TDS Smart Model V3", layout="wide")

@st.cache_data
def load_data():
    try:
        df = pd.read_excel("TDS_Master_Data.xlsx", engine='openpyxl')
        df.columns = [c.strip() for c in df.columns]
        # Robust cleaning for all text columns
        for col in df.select_dtypes(include=['object']).columns:
            df[col] = df[col].astype(str).str.strip()
        
        df['Effective From'] = pd.to_datetime(df['Effective From'], errors='coerce')
        df['Effective To'] = pd.to_datetime(df['Effective To'], errors='coerce').fillna(pd.Timestamp('2099-12-31'))
        return df
    except Exception as e:
        st.error(f"Excel Error: {e}")
        return None

df = load_data()

if df is not None:
    st.title("🏛️ TDS Calculation Portal - V3")
    
    col1, col2 = st.columns(2)
    with col1:
        sections = sorted([s for s in df['Section'].unique() if s != 'nan'])
        section = st.selectbox("1. Section", options=sections)
        filtered_df = df[df['Section'] == section]
        
        natures = sorted([n for n in filtered_df['Nature of Payment'].unique() if n != 'nan'])
        nature_selection = st.selectbox("2. Nature of Payment", options=natures)
        
        amount = st.number_input("3. Amount (INR)", min_value=0.0, value=250000.0)

    with col2:
        pan_status = st.radio("4. PAN Available?", ["Yes", "No"])
        pay_date = st.date_input("5. Date")
        calc_mode = st.radio("6. Basis", ["Single Transaction", "Aggregate (Full Year)"])

    if st.button("🚀 Calculate"):
        target = pd.to_datetime(pay_date)
        match = filtered_df[filtered_df['Nature of Payment'] == nature_selection]
        rule = match[(match['Effective From'] <= target) & (match['Effective To'] >= target)]
        
        if rule.empty and not match.empty:
            rule = match.sort_values(by='Effective From', ascending=False).head(1)

        if not rule.empty:
            sel = rule.iloc[0]
            try:
                base_rate = float(sel['Rate of TDS (%)'])
                final_rate = 20.0 if pan_status == "No" else base_rate
                thresh = float(sel['Threshold Amount (Rs)'])
                
                # 194C Aggregate Override
                if section == "194C" and calc_mode == "Aggregate (Full Year)":
                    thresh = 100000.0
                
                if amount > thresh:
                    tax = (amount * final_rate) / 100
                    st.success(f"### ✅ Deduct: ₹{tax:,.2f}")
                    st.metric("Rate", f"{final_rate}%")
                else:
                    st.warning(f"### ⚠️ No TDS Required")
                    st.write(f"Amount ₹{amount:,.0f} is not above ₹{thresh:,.0f}")
                
                # DEBUG BOX (Show this to your manager to prove it's working)
                with st.expander("View Calculation Logic"):
                    st.write(f"**Section Matched:** {sel['Section']}")
                    st.write(f"**Threshold in Excel:** ₹{thresh:,.0f}")
                    st.write(f"**Rate in Excel:** {base_rate}%")
                    st.write(f"**Date Range:** {sel['Effective From'].date()} to {sel['Effective To'].date()}")
            except:
                st.error("Check Excel: Rates/Thresholds must be plain numbers (no % signs).")
        else:
            st.error("No matching rule found for this date/nature.")
