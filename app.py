import streamlit as st
import pandas as pd
import numpy as np
import re
from datetime import datetime

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

if 'df_raw' not in st.session_state:
    st.session_state.df_raw = None
if 'selected_year' not in st.session_state:
    st.session_state.selected_year = "Všetky"

# ==========================================
# POMOCNÉ ČISTIACE A PARSOVACIE MODULY
# ==========================================
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

def extract_clean_records(file):
    """Načíta CSV, nájde správne stĺpce nezávisle od indexov a vráti čistý zoznam riadkov."""
    try:
        df = pd.read_csv(file)
    except Exception:
        return []
        
    df = df.reset_index(drop=True)
    
    col_mapping = {}
    keywords = {
        'Time': ['time', 'čas', 'cas', 'typ', 'dátum', 'datum'],
        'Action': ['action', 'operácia', 'operacia', 'typ obchodu', 'akcia'],
        'Ticker': ['ticker', 'symbol'],
        'Name': ['name', 'názov', 'nazov', 'spoločnosť', 'nazov nastroja', 'názov nástroja'],
        'Shares': ['no. of shares', 'kusy', 'množstvo', 'mnozstvo', 'počet', 'pocet'],
        'PricePerShare': ['price per share', 'cena za kus', 'cena', 'cena za akciu'],
        'Total': ['total', 'celkom', 'suma', 'celková suma', 'celkova suma']
    }
    
    for target_key, phrases in keywords.items():
        for col in df.columns:
            if str(col).lower().strip() in phrases:
                col_mapping[target_key] = col
                break
        if target_key not in col_mapping:
            for col in df.columns:
                if any(p in str(col).lower() for p in phrases):
                    col_mapping[target_key] = col
                    break

    records = []
    for _, row in df.iterrows():
        r_time = row[col_mapping['Time']] if 'Time' in col_mapping else np.nan
        r_action = row[col_mapping['Action']] if 'Action' in col_mapping else 'UNKNOWN'
        r_ticker = row[col_mapping['Ticker']] if 'Ticker' in col_mapping else 'UNKNOWN'
        r_name = row[col_mapping['Name']] if 'Name' in col_mapping else 'UNKNOWN'
        
        r_shares = clean_numeric_string(row[col_mapping['Shares']]) if 'Shares' in col_mapping else 0.0
        r_price = clean_numeric_string(row[col_mapping['PricePerShare']]) if 'PricePerShare' in col_mapping else 0.0
        r_total = clean_numeric_string(row[col_mapping['Total']]) if 'Total' in col_mapping else 0.0
        
        records.append({
            'Time': r_time,
            'Action': str(r_action),
            'Ticker': str(r_ticker),
            'Name': str(r_name),
            'Shares': r_shares,
            'PricePerShare': r_price,
            'Total': r_total
        })
    return records

def process_uploaded_files(uploaded_files):
    all_records = []
    for file in uploaded_files:
        file_records = extract_clean_records(file)
        all_records.extend(file_records)
        
    if not all_records:
        return None
        
    combined_df = pd.DataFrame(all_records)
    combined_df['Time'] = pd.to_datetime(combined_df['Time'], format='mixed', errors='coerce')
    combined_df = combined_df.dropna(subset=['Time']).sort_values(by='Time').reset_index(drop=True)
    return combined_df

# ==========================================
# STABILNÉ LINEÁRNE FIFO JADRO
# ==========================================
def run_fifo_engine(df):
    action_pattern = r'(buy|sell|nákup|nakup|predaj)'
    
    valid_df = df[
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
        if ticker in ['UNKNOWN', 'NAN', '', 'NONE']:
            continue
            
        action = str(row['Action']).lower()
        row_date = row['Time']
        shares = abs(row['Shares'])
        price_eur = row['PricePerShare']
        name = row['Name'] if row['Name'] != 'UNKNOWN' else ticker
        
        if ticker not in fifo_pools:
            fifo_pools[ticker] = []
            lot_counters[ticker] = 0
            
        # NÁKUP
        if 'buy' in action or 'nákup' in action or 'nakup' in action:
            lot_counters[ticker] += 1
            fifo_pools[ticker].append({
                'date': row_date,
                'shares': shares,
                'price_eur': price_eur,
                'orig_shares': shares,
                'lot_id': lot_counters[ticker]
            })
            
        # PREDAJ
        elif 'sell' in action or 'predaj' in action:
            shares_to_sell = shares
            loop_limit = len(fifo_pools[ticker])
            
            for _ in range(loop_limit):
                if shares_to_sell <= 1e-7 or len(fifo_pools[ticker]) == 0:
                    break
                    
                # DEFINITÍVNA KOREKCIA: Ťaháme prvú nákupnú šaržu cez index [0]
                oldest_lot = fifo_pools[ticker][0]
                
                if oldest_lot['shares'] <= (shares_to_sell + 1e-7):
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
                
            if shares_to_sell > 1e-7:
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
                
    if len(t_tickers) == 0:
        return pd.DataFrame(), fifo_pools
        
    trades_df = pd.DataFrame({
        'Ticker': t_tickers, 'Spoločnosť': t_names, 'Kusy': t_shares,
        'Dátum nákupu': t_buydates, 'Dátum predaja': t_selldates, 'Dni držania': t_days,
        'Príjmy (EUR)': t_revenue, 'Výdavky (EUR)': t_costs, 'Zisk/Strata (EUR)': t_profit,
        'Oslobodené': t_exempt, 'Zdaniteľný zisk': t_taxable, 'Rok_Predaja': t_years
    })
    return trades_df, fifo_pools

# ==========================================
# HLAVNÝ RENDER STRÁNKY (UI)
# ==========================================
st.title("📈 Súkromný PRO Optimalizátor pre Trading 212")
st.caption("Verzia 5.0: Plne stabilizované spracovanie nákupných šarží. Kompletný audit.")

st.header("1. Vstup dát (Hromadný import CSV)")
uploaded_files = st.file_uploader(
    "Nahrajte jeden alebo viac CSV exportov z Trading 212:", 
    type=["csv"], 
    accept_multiple_files=True
)

if uploaded_files:
    parsed_df = process_uploaded_files(uploaded_files)
    if parsed_df is not None:
        st.session_state.df_raw = parsed_df
        st.success("Dáta úspešne spracované.")

if st.session_state.df_raw is None:
    st.info("Na aktiváciu aplikácie nahrajte aspoň jeden CSV súbor exportu z Trading 212 vyššie.")
    st.stop()

df_main = st.session_state.df_raw

try:
    df_trades, open_lots_pool = run_fifo_engine(df_main)
except Exception as fatal_err:
    st.error(f"Chyba pri spracovaní FIFO: {fatal_err}")
    st.stop()

st.header("2. Výber daňového obdobia")
available_years = ["Všetky"]

if not df_main.empty:
    years_found = sorted(list(df_main['Time'].dt.year.unique()))
    available_years.extend([str(y) for y in years_found])

cols_years = st.columns(len(available_years))
for idx, yr in enumerate(available_years):
