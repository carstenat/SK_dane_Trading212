import streamlit as st
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Trading 212 PRO Daňový Asistent & Optimalizátor", page_icon="📈", layout="wide")

# =========================================================================
# 🎨 PREPÍNAČ PRE DARK / LIGHT MODE (DEFAULT SVETLÝ, PREPÍNATEĽNÝ)
# =========================================================================
st.sidebar.header("⚙️ Vzhľad a Vychytávky")
dark_mode = st.sidebar.checkbox("Zapnúť Tmavý režim (Dark Mode)", value=False)

if dark_mode:
    st.markdown("""
        <style>
        .stApp { background-color: #0B0F19 !important; color: #F8FAFC !important; font-size: 14px !important; }
        h1 { font-size: 24px !important; font-weight: 700 !important; color: #FFFFFF !important; margin-bottom: 5px !important; }
        h2 { font-size: 19px !important; font-weight: 600 !important; color: #F8FAFC !important; margin-top: 15px !important; }
        h3 { font-size: 16px !important; font-weight: 600 !important; color: #FFFFFF !important; }
        p, label, span { color: #E2E8F0 !important; }
        
        div[data-testid="stMetric"] {
            background-color: #1E293B !important;
            border: 2px solid #475569 !important;
            border-radius: 12px !important;
            padding: 14px 18px !important;
            box-shadow: 0 4px 12px rgba(0,0,0,0.3) !important;
        }
        div[data-testid="stMetricValue"] { color: #38BDF8 !important; font-size: 22px !important; font-weight: 800 !important; }
        div[data-testid="stMetricLabel"] { color: #CBD5E1 !important; font-size: 13px !important; font-weight: 600 !important; }
        
        .stTabs [data-baseweb="tab-list"] { background-color: #1E293B !important; border: 1px solid #475569 !important; border-radius: 10px; padding: 4px; }
        .stTabs [data-baseweb="tab"] { color: #94A3B8 !important; font-weight: 600 !important; }
        .stTabs [aria-selected="true"] { background-color: #0EA5E9 !important; color: #FFFFFF !important; font-weight: 700 !important; }
        
        .stDataFrame div { background-color: #111827 !important; color: #F8FAFC !important; border-radius: 8px; }
        </style>
    """, unsafe_allow_html=True)
else:
    st.markdown("""
        <style>
        /* Moderný čistý svetlý dizajn */
        div[data-testid="stMetric"] {
            background-color: #F8FAFC !important;
            border: 1px solid #CBD5E1 !important;
            border-radius: 12px !important;
            padding: 14px 18px !important;
        }
        div[data-testid="stMetricValue"] { color: #0284C7 !important; font-weight: 800 !important; }
        </style>
    """, unsafe_allow_html=True)

st.title("📈 Súkromný PRO Optimalizátor pre Trading 212 (SR)")
st.write("Profesionálny nástroj na kontrolu časového testu pred predajom a automatickú ročnú daňovú uzávierku.")

uploaded_files = st.file_uploader("Sem presuňte vaše CSV exporty z Trading 212 (môžete aj viac naraz)", type=["csv"], accept_multiple_files=True)

if uploaded_files:
    zoznam_df = []
    for file in uploaded_files:
        zoznam_df.append(pd.read_csv(file))
        
    df = pd.concat(zoznam_df, ignore_index=True)
    df['Time'] = pd.to_datetime(df['Time'], errors='coerce').dt.tz_localize(None)
    df = df.dropna(subset=['Time']).sort_values(by='Time').reset_index(drop=True)
    
    # 🛡️ UNIVERZÁLNE OŠETRENIE ČÍSELNÝCH TYPOV (Zabráni pádu na TypeError)
    df['No. of shares'] = pd.to_numeric(df['No. of shares'], errors='coerce').fillna(0.0)
    df['Total'] = pd.to_numeric(df['Total'], errors='coerce').fillna(0.0)
    df['Result'] = pd.to_numeric(df['Result'], errors='coerce').fillna(0.0)
    df['Withholding tax'] = pd.to_numeric(df['Withholding tax'], errors='coerce').fillna(0.0)
    
    # Odfiltrujeme vklady/úroky bez tickeru hneď na úvode pre stabilitu optimalizátora
    df_filtrat = df[df['Ticker'].notna()].copy()
    df_filtrat['Ticker'] = df_filtrat['Ticker'].astype(str).str.strip()
    df_filtrat = df_filtrat[(df_filtrat['Ticker'] != '') & (df_filtrat['Ticker'] != 'nan')].copy()
    
    df_filtrat['Ticker_Clean'] = df_filtrat['Ticker'].str.replace("US ", "").str.replace("_US", "").str.replace("_US_EQ", "").str.replace("_EQ", "").str.replace(".US", "").str.strip().str.replace("_", "").str.replace(".", "").str.replace(" ", "").str.upper()
    
    databaza_mien = {}
    for _, riadok in df_filtrat.iterrows():
        tick_c = str(riadok['Ticker_Clean'])
        full_name = str(riadok.get('Name', 'Zjednodušená akcia')).strip()
        if tick_c and full_name and full_name != 'nan':
            if tick_c not in databaza_mien or len(full_name) > len(databaza_mien[tick_c]):
                databaza_mien[tick_c] = full_name

    # =========================================================================
    # 🔥 1. ČASŤ: PROFESIONÁLNY DAŇOVÝ OPTIMALIZÁTOR PRED PREDAJOM
    # =========================================================================
    st.header("🔍 Daňový Optimalizátor pre dnešný predaj")
    st.write("Vyberte firmu zo zoznamu a zadajte aktuálny otvorený stav, ktorý vidíte v platforme Trading 212.")
    
    df_akcie = df_filtrat[df_filtrat['Action'].str.lower().str.contains('buy|investment|deposit|sell|divestment|withdrawal|rebalancing', na=False)].copy()
    zoznam_tickerov_all = sorted(list(df_akcie['Ticker_Clean'].unique()))
    
    if not zoznam_tickerov_all:
        st.info("V nahratých súboroch sa nenachádzajú žiadne nákupné transakcie akcií.")
    else:
        ponuka_pre_menu = []
        mapovanie_tickerov = {}
        for t in zoznam_tickerov_all:
            full_company_name = databaza_mien.get(t, "Spoločnosť z platformy")
            text_riadku = f"{t} - {full_company_name}"
            ponuka_pre_menu.append(text_riadku)
            mapovanie_tickerov[text_riadku] = t
            
        ponuka_pre_menu = sorted(list(set(ponuka_pre_menu)))
        vybrany_text = st.selectbox("Vyberte akciu zo svojho portfólia:", ponuka_pre_menu)
        vybrany_ticker_pure = mapovanie_tickerov[vybrany_text]
        
        col_input1, col_input2 = st.columns(2)
        with col_input1:
            skutocny_stav = st.number_input("Počet kusov vlastnených na T212:", min_value=0.0, value=0.0, step=0.00001, format="%.5f", key="vstup_pro_v39")
        with col_input2:
            aktualna_cena = st.number_input("Aktuálna trhová cena akcie (EUR):", min_value=0.0, value=0.0, step=0.01, format="%.2f", key="vstup_cena_v39")
        
        df_ticker = df_akcie[df_akcie['Ticker_Clean'] == vybrany_ticker_pure].copy()
        df_ticker = df_ticker.sort_values(by='Time').reset_index(drop=True)
        
        sklad_aktualny = []
        for _, riadok in df_ticker.iterrows():
            typ = str(riadok['Action']).lower()
            shares = float(riadok['No. of shares'])
            total = float(riadok['Total'])
            datum = riadok['Time']
            
            if 'buy' in typ or 'investment' in typ or 'deposit' in typ:
                if shares > 0:
                    sklad_aktualny.append({'shares': shares, 'date': datum, 'cena_za_kus': total/shares if shares > 0 else 0.0})
            elif 'sell' in typ or 'divestment' in typ or 'withdrawal' in typ or 'rebalancing' in typ or shares < 0:
                predat_este = abs(shares)
                temp_sklad = []
                for balicek in sklad_aktualny:
                    if predat_este <= 1e-6:
                        temp_sklad.append(balicek)
                    else:
                        if balicek['shares'] <= predat_este:
                            predat_este -= balicek['shares']
                        else:
                            balicek['shares'] -= predat_este
                            predat_este = 0.0
                            temp_sklad.append(balicek)
                sklad_aktualny = temp_sklad
        
        if skutocny_stav > 0:
            potrebne_ks = skutocny_stav
            dnes = datetime.now()
            ks_bez_dane = 0.0
            ks_mlade = 0.0
            vydavok_safe_balika = 0.0
            vydavok_mladeho_balika = 0.0
            
            list_dat_nakupu = []
            list_mnozstiev = []
            list_stavov = []
            list_povodna_cena = []
            list_celkovy_nakup = []
            list_dat_oslobodenia = []
            list_cakania = []
            
            for n in sklad_aktualny:
                if potrebne_ks <= 1e-6:
                    break
                vziat_ks = min(n['shares'], potrebne_ks)
                potrebne_ks -= vziat_ks
                
                nakup_pure = pd.to_datetime(n['date']).to_pydatetime()
                vek_dni = (dnes.date() - nakup_pure.date()).days
                cena_balika = vziat_ks * n['cena_za_kus']
                
                list_dat_nakupu.append(nakup_pure.strftime('%d.%m.%Y'))
                list_mnozstiev.append(f"{vziat_ks:.5f}")
                list_povodna_cena.append(f"{n['cena_za_kus']:.2f} EUR")
                list_celkovy_nakup.append(f"{cena_balika:.2f} EUR")
                
                if vek_dni >= 365:
                    ks_bez_dane += vziat_ks
                    vydavok_safe_balika += cena_balika
                    list_stavov.append("🟢 Bez dane (Nad 1 rok)")
                    list_dat_oslobodenia.append("Už oslobodené")
                    list_cakania.append("0 dní")
                else:
                    ks_mlade += vziat_ks
                    vydavok_mladeho_balika += cena_balika
                    list_stavov.append("🔴 Zdaňuje sa (Mladá akcia)")
                    list_dat_oslobodenia.append((nakup_pure + pd.Timedelta(days=365)).strftime('%d.%m.%Y'))
                    list_cakania.append(f"⏳ {365 - vek_dni} dní")
            
            pomer_safe = ks_bez_dane / skutocny_stav
            st.markdown(f"**Vizuálny pomer safe pozície:** {ks_bez_dane:.5f} ks z {skutocny_stav:.5f} ks")
