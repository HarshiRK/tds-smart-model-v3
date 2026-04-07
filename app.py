import streamlit as st
import pandas as pd

st.set_page_config(page_title="TDS Smart Model V3", layout="wide")

@st.cache_data
def load_data():
    try:
        # Loading your Excel file
        df = pd.read_excel("TDS_Master_Data.xlsx", engine='openpyxl')
        df.columns = [c.strip() for c in df.columns]
        
        # Clean text columns for matching
        for col in ['Section', 'Nature of Payment', 'Payee Type']:
            df[col] = df[col].astype(str).str.strip()
            
        return df
    except Exception as e:
        st.error(f"Error loading Excel: {e}")
        return None

df = load_data()

if df is not None:
    st.title("🏛️ TDS Smart Model V3")
    st.subheader("Dynamic Nature-of-Payment Logic")
    st.write("---")

    col1, col2 = st.columns(2)

    with col1:
        st.info("📊 **Step 1: Selection**")
        sections = sorted([s for s in df['Section'].unique() if s not in ['nan', 'None']])
        section = st.selectbox("Select Income Tax Section", options=sections)
        
        # Filter data early to get the "Nature of Payment" options
        filtered_df = df[df['Section'] == section]
        
        # Dynamic selection based on 'Nature of Payment' column
        nature_options = sorted(filtered_df['Nature of Payment'].unique().tolist())
        nature_selection = st.selectbox("Nature of Payment / Asset Type", options=nature_options)

    with col2:
        st.info("👤 **Step 2: Details**")
        calc_mode = st.radio("Calculation Basis:", ["Single Transaction", "Aggregate (Full Year)"])
        amount = st.number_input("Enter Amount (INR)", min_value=0.0, step=1000.0)
        pan_status = st.radio("Is PAN available?", ["Yes", "No"])
        pay_date = st.date_input("Transaction Date")

    # --- CALCULATION ---
    st.markdown("---")
    if st.button("🚀 Calculate TDS"):
        target = pd.to_datetime(pay_date)
        
        # Find the row that matches both the Section and the Nature of Payment
        match = filtered_df[filtered_df['Nature of Payment'] == nature_selection]
        
        # Date filtering
        rule = match[(match['Effective From'] <= target) & (match['Effective To'] >= target)]
        if rule.empty and not match.empty:
            rule = match.sort_values(by='Effective From', ascending=False).head(1)

        if not rule.empty:
            sel = rule.iloc[0]
            rate_raw = str(sel['Rate of TDS (%)']).strip().lower()
            
            if rate_raw == 'avg':
                st.info(f"💡 **Note:** {sel['Notes']}")
            else:
                try:
                    base_rate = float(sel['Rate of TDS (%)'])
                    final_rate = 20.0 if pan_status == "No" else base_rate
                    threshold = float(sel['Threshold Amount (Rs)'])
                    
                    # 194C Aggregate Logic
                    if section == "194C" and calc_mode == "Aggregate (Full Year)":
                        threshold = 100000.0
                    
                    if amount > threshold:
                        tax = (amount * final_rate) / 100
                        st.success(f"### Result: Deduct ₹{tax:,.2f}")
                        st.write(f"**Rate Applied:** {final_rate}%")
                        st.write(f"**Threshold:** ₹{threshold:,.0f} (Exceeded)")
                    else:
                        st.warning(f"### Result: No TDS Required")
                        st.write(f"Amount is within the limit of ₹{threshold:,.0f}.")
                except:
                    st.error("Check Excel: Ensure 'Rate' and 'Threshold' are numbers.")
