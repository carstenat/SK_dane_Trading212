import streamlit as st
import pandas as pd
import numpy as np
import re
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta

# ==========================================
# KONŠTANTY A KONFIGURÁCIA (SR LEGISLATÍVA)
# ==========================================
TAX_RATE_SK = 0.19
HEALTH_INSURANCE_RATE_SK = 0.15
TAX_EXEMPTION_LIMIT_SK = 500.0

st.set_page_config(
    page_title="PRO Optimalizátor Trading 212",
    page_icon="📈",
    layout="wide"
)

# Inicializácia Session State proti resetom komponentov
if 'df_raw' not in st.session_state:
    st.session_state.df_raw = None
if 'selected_year' not in st.session_state:
    st.session_state.selected_year = "Všetky"

# ==========================================
# POMOCNÉ ČISTIACE A PARSOVACIE MODULY
# ==========================================
@st.cache_data(ttl=86400)
def fetch_ecb_daily_rates_for_year(year):
    """Sťahuje historické denné kurzy USD a GBP voči EUR z ECB pre daný rok."""
    rates = {'USD': {}, 'GBP': {}}
    try:
        url = "https://europa.eu"
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            root = ET.fromstring(response.content)
            namespaces = {'ns': 'http://ecb.int'}
            for cube_time in root.findall('.//ns:Cube[@time]', namespaces):
                date_str = cube_time.get('time')
                try:
                    date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
                    if date_obj.year == int(year):
                        for cube_curr in cube_time.findall('ns:Cube', namespaces):
                            currency = cube_curr.get('currency')
                            rate_val = float(cube_curr.get('rate'))
                            if currency in rates:
                                rates[currency][date_str] = rate_val
                except Exception:
                    continue
    except Exception:
        pass
    return rates

def get_ecb_rate(date_obj, currency, year_rates):
    """Vráti výmenný kurz. Pri víkende hľadá najbližší predošlý pracovný deň."""
    if currency == 'EUR' or not currency:
        return 1.0
    curr_dict = year_rates.get(currency, {})
    if not curr_dict:
        return 1.10
    for i in range(6):
        check_date = (date_obj - timedelta(days=i)).strftime("%Y-%m-%d")
        if check_date in curr_dict:
            return curr_dict[check_date]
    return 1.10

def clean_numeric_string(val):
    if pd.isna(val):
        return 0.0
    if isinstance(val, (int, float)):
        return float(val)
    val_str = str(val).strip()
    val_str = re.sub(r'[^\d.,\-]', '', val_str)
    if ',' in val_str and '.' in val_str:
        if val_str.find(',') > val_str.find('.'):
            val_str = val_str.replace('.', '').replace(',', '.')
        else:
            val_str = val_str.replace(',', '')
    elif ',' in val_str:
        val_str = val_str.replace(',', '.')
    try:
        return float(val_str)
    except ValueError:
        return 0.0

def normalize_columns(df):
    mapping = {
        'time': 'Time', 'čas': 'Time', 'cas': 'Time',
        'action': 'Action', 'operácia': 'Action', 'operacia': 'Action', 'typ': 'Action',
        'ticker': 'Ticker', 'symbol': 'Ticker',
        'name': 'Name', 'názov': 'Name', 'nazov': 'Name',
        'no. of shares': 'Shares', 'kusy': 'Shares', 'množstvo': 'Shares', 'mnozstvo': 'Shares',
        'price per share': 'PricePerShare', 'cena za kus': 'PricePerShare',
        'total': 'Total', 'celkom': 'Total', 'suma': 'Total',
        'currency': 'Currency', 'mena': 'Currency'
    }
    renamed_cols = {}
    for col in df.columns:
        col_lower = str(col).lower().strip()
        if col_lower in mapping:
            renamed_cols[col] = mapping[col_lower]
        else:
            for key, target in mapping.items():
                if key in col_lower:
                    renamed_cols[col] = target
                    break
    df = df.rename(columns=renamed_cols)
    required_keys = ['Time', 'Action', 'Ticker', 'Name', 'Shares', 'PricePerShare', 'Total', 'Currency']
    for req in required_keys:
        if req not in df.columns:
            df[req] = 'EUR' if req == 'Currency' else np.nan
    return df

def process_uploaded_files(uploaded_files):
    df_list = []
    for file in uploaded_files:
        try:
            current_df = pd.read_csv(file)
            for col in current_df.columns:
                if 'total' in col.lower() and ('usd' in col.lower() or '$' in col.lower()):
                    current_df['Currency_Detected'] = 'USD'
                elif 'total' in col.lower() and ('gbp' in col.lower() or '£' in col.lower()):
                    current_df['Currency_Detected'] = 'GBP'
            df_list.append(current_df)
        except Exception:
            continue
            
    if not df_list:
        return None
        
    combined_df = pd.concat(df_list, ignore_index=True)
    combined_df = normalize_columns(combined_df)
    
    if 'Currency_Detected' in combined_df.columns:
        combined_df['Currency'] = combined_df['Currency'].fillna(combined_df['Currency_Detected'])
    combined_df['Currency'] = combined_df['Currency'].fillna('EUR').astype(str).str.upper().str.strip()
    
    combined_df['Shares'] = combined_df['Shares'].apply(clean_numeric_string)
    combined_df['PricePerShare'] = combined_df['PricePerShare'].apply(clean_numeric_string)
    combined_df['Total'] = combined_df['Total'].apply(clean_numeric_string)
    
    combined_df['Time'] = pd.to_datetime(combined_df['Time'], format='mixed', errors='coerce')
    combined_df = combined_df.dropna(subset=['Time']).sort_values(by='Time').reset_index(drop=True)
    return combined_df

# ==========================================
# REFORMOVANÉ FIFO JADRO (BEZ ZACYKLENIA)
# ==========================================
def run_fifo_engine(df, cached_rates):
    action_pattern = r'(buy|sell|nákup|nakup|predaj)'
    valid_df = df[
        df['Ticker'].notna() & 
        (df['Ticker'].str.strip() != '') & 
        df['Action'].astype(str).str.lower().str.contains(action_pattern, regex=True)
    ].copy()
    
    fifo_pools = {}
    lot_counters = {}
    
    t_tickers, t_names, t_shares = [], [], []
    t_buydates, t_selldates, t_days = [], [], []
    t_revenue, t_costs, t_profit = [], [], []
    t_exempt, t_taxable, t_years = [], [], []
    
    for idx, row in valid_df.iterrows():
        ticker = str(row['Ticker']).strip().upper()
        action = str(row['Action']).lower()
        row_date = row['Time']
        shares = abs(row['Shares'])
        price_raw = row['PricePerShare']
        currency = row['Currency']
        name = row['Name'] if pd.notna(row['Name']) else ticker
        
        rate = get_ecb_rate(row_date.date(), currency, cached_rates)
        price_eur = price_raw / rate if currency != 'EUR' else price_raw
        
        if ticker not in fifo_pools:
            fifo_pools[ticker] = []
            lot_counters[ticker] = 0
            
        # SPRACUJE NÁKUP
        if 'buy' in action or 'nákup' in action or 'nakup' in action:
            lot_counters[ticker] += 1
            fifo_pools[ticker].append({
                'date': row_date,
                'shares': shares,
                'price_eur': price_eur,
                'orig_shares': shares,
                'lot_id': lot_counters[ticker],
                'currency_orig': currency
            })
            
        # SPRACUJE PREDAJ
        elif 'sell' in action or 'predaj' in action:
            shares_to_sell = shares
            
            while shares_to_sell > 0 and len(fifo_pools[ticker]) > 0:
                # KĽÚČOVÁ OPRAVA: [0] explicitne vyberie najstarší prvok z listu šarží
                oldest_lot = fifo_pools[ticker][0]
                
                if oldest_lot['shares'] <= shares_to_sell:
                    matched_shares = oldest_lot['shares']
                    shares_to_sell -= matched_shares
                    fifo_pools[ticker].pop(0)
                else:
                    matched_shares = shares_to_sell
                    oldest_lot['shares'] -= matched_shares
                    shares_to_sell = 0
                    
                buy_date = oldest_lot['date']
                days_held = (row_date - buy_date).days
                
                cost_basis_eur = matched_shares * oldest_lot['price_eur']
                revenue_basis_eur = matched_shares * price_eur
                profit_loss_eur = revenue_basis_eur - cost_basis_eur
                
                is_exempt = days_held >= 365
                taxable_profit = profit_loss_eur if not is_exempt else 0.0
                
                t_tickers.append(ticker)
                t_names.append(name)
                t_shares.append(matched_shares)
                t_buydates.append(buy_date.strftime('%Y-%m-%d'))
                t_selldates.append(row_date.strftime('%Y-%m-%d'))
                t_days.append(days_held)
                t_revenue.append(revenue_basis_eur)
                t_costs.append(cost_basis_eur)
                t_profit.append(profit_loss_eur)
                t_exempt.append('Áno' if is_exempt else 'Nie')
                t_taxable.append(taxable_profit)
                t_years.append(row_date.year)
                
            if shares_to_sell > 0:
                t_tickers.append(ticker)
                t_names.append(name)
                t_shares.append(shares_to_sell)
                t_buydates.append('Neznámy')
                t_selldates.append(row_date.strftime('%Y-%m-%d'))
                t_days.append(0)
                t_revenue.append(shares_to_sell * price_eur)
                t_costs.append(0.0)
                t_profit.append(0.0)
                t_exempt.append('Nie')
                t_taxable.append(0.0)
                t_years.append(row_date.year)
                
