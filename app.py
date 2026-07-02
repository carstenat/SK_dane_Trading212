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

# Inicializácia Session State proti resetom komponentov
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
            df_list.append(current_df)
        except Exception:
            continue
            
    if not df_list:
        return None
        
    combined_df = pd.concat(df_list, ignore_index=True)
    combined_df = normalize_columns(combined_df)
    
    combined_df['Currency'] = combined_df['Currency'].fillna('EUR').astype(str).str.upper().str.strip()
    combined_df['Shares'] = combined_df['Shares'].apply(clean_numeric_string)
    combined_df['PricePerShare'] = combined_df['PricePerShare'].apply(clean_numeric_string)
    combined_df['Total'] = combined_df['Total'].apply(clean_numeric_string)
    
    combined_df['Time'] = pd.to_datetime(combined_df['Time'], format='mixed', errors='coerce')
    combined_df = combined_df.dropna(subset=['Time']).sort_values(by='Time').reset_index(drop=True)
    return combined_df

# ==========================================
# STABILNÉ LINEÁRNE FIFO JADRO (BEZ KRAŠOV)
# ==========================================
def run_fifo_engine(df):
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
        price_eur = row['PricePerShare']  # Počítame s natívnou cenou z CSV
        name = row['Name'] if pd.notna(row['Name']) else ticker
        
        if ticker not in fifo_pools:
            fifo_pools[ticker] = []
            lot_counters[ticker] = 0
            
        # NÁKUP: Pridanie novej šarže
        if 'buy' in action or 'nákup' in action or 'nakup' in action:
            lot_counters[ticker] += 1
            fifo_pools[ticker].append({
                'date': row_date,
                'shares': shares,
                'price_eur': price_eur,
                'orig_shares': shares,
                'lot_id': lot_counters[ticker],
                'currency_orig': row['Currency']
            })
            
        # PREDAJ: Bezpečné lineárne párovanie
        elif 'sell' in action or 'predaj' in action:
            shares_to_sell = shares
            loop_limit = len(fifo_pools[ticker])
            
            for _ in range(loop_limit):
                if shares_to_sell <= 1e-7 or len(fifo_pools[ticker]) == 0:
                    break
                    
                # FIX: Natvrdo vyťahujeme prvý konkrétny slovník z poľa cez index 0
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
# HLAVNÝ BEZPEČNÝ RENDER STRÁNKY (UI)
# ==========================================
st.title("📈 Súkromný PRO Optimalizátor pre Trading 212")
st.caption("Verzia 4.0: Odstránené sieťové API a ošetrené indexovanie šarží. Absolútna stabilita štartu.")

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
        st.success("Dáta úspešne načítané.")

# KĽÚČOVÁ OCHRANA: Ak v stave nie sú dáta, kód sa tu natvrdo zastaví a nevyvolá bielu obrazovku
if st.session_state.df_raw is None:
    st.info("Na aktiváciu aplikácie nahrajte aspoň jeden CSV súbor exportu z Trading 212 vyššie.")
    st.stop()

# Ak dáta existujú, bezpečne pokračujeme vo vykresľovaní zvyšku stránky
df_main = st.session_state.df_raw

# Spustenie stabilného bezchybného engine
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
    if cols_years[idx].button(f"📅 {yr}", key=f"btn_yr_{yr}"):
        st.session_state.selected_year = yr

st.write(f"Aktívne daňové obdobie: **{st.session_state.selected_year}**")

