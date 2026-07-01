import streamlit as st
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Trading 212 PRO Daňový Asistent & Optimalizátor", page_icon="📈", layout="wide")

# =========================================================================
# 🎨 NATVRDO PREVOLENÝ VYSOKO-KONTRASTNÝ FINTECH DESIGN (NEZÁVISLÝ OD TICKBOXU)
# =========================================================================
st.markdown("""
    <style>
    /* Sýte tmavé bridlicové pozadie */
    .stApp { background-color: #0B0F19 !important; color: #F8FAFC !important; font-size: 14px !important; }
    
    /* Kontrastné nadpisy - dokonale viditeľné */
    h1 { font-size: 24px !important; font-weight: 700 !important; color: #FFFFFF !important; margin-bottom: 5px !important; }
    h2 { font-size: 19px !important; font-weight: 600 !important; color: #F8FAFC !important; margin-top: 15px !important; }
    h3 { font-size: 16px !important; font-weight: 600 !important; color: #FFFFFF !important; }
    p, label, span { color: #E2E8F0 !important; }
    
    /* Prémiové, vysoko čitateľné fintech widgety */
    div[data-testid="stMetric"] {
        background-color: #1E293B !important;
        border: 2px solid #475569 !important;
        border-radius: 12px !important;
        padding: 14px 18px !important;
        box-shadow: 0 4px 12px rgba(0,0,0,0.3) !important;
    }
    /* Jasná neónovo-tyrkysová farba namiesto nečitateľnej modrej */
    div[data-testid="stMetricValue"] { color: #38BDF8 !important; font-size: 22px !important; font-weight: 800 !important; }
    div[data-testid="stMetricLabel"] { color: #CBD5E1 !important; font-size: 13px !important; font-weight: 600 !important; }
    
    /* Kontrastné responzívne záložky (Tabs) */
    .stTabs [data-baseweb="tab-list"] { background-color: #1E293B !important; border: 1px solid #475569 !important; border-radius: 10px; padding: 4px; }
    .stTabs [data-baseweb="tab"] { color: #94A3B8 !important; font-weight: 600 !important; }
    .stTabs [aria-selected="true"] { background-color: #0EA5E9 !important; color: #FFFFFF !important; font-weight: 700 !important; }
    
    /* Kompaktné a vysoko kontrastné tabuľky */
    .stDataFrame div { background-color: #111827 !important; color: #F8FAFC !important; border-radius: 8px; }
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
    
    df['Ticker_Clean'] = df['Ticker'].fillna('').astype(str).str.replace("US ", "").str.replace("_US", "").str.replace("_US_EQ", "").str.replace("_EQ", "").str.replace(".US", "").str.strip().str.replace("_", "").str.replace(".", "").str.replace(" ", "").str.upper()
    
    databaza_mien = {}
    for _, riadok in df.iterrows():
        tick_c = str(riadok['Ticker_Clean'])
        full_name = str(riadok.get('Name', 'Zjednodušená akcia')).strip()
        if tick_c and tick_c != 'nan' and full_name and full_name != 'nan':
            if tick_c not in databaza_mien or len(full_name) > len(databaza_mien[tick_c]):
                databaza_mien[tick_c] = full_name

    # =========================================================================
    # 🔥 1. ČASŤ: PROFESIONÁLNY DAŇOVÝ OPTIMALIZÁTOR PRED PREDAJOM
    # =========================================================================
    st.header("🔍 Daňový Optimalizátor pre dnešný predaj")
    st.write("Vyberte firmu zo zoznamu a zadajte aktuálny otvorený stav, ktorý vidíte v platforme Trading 212.")
    
    df_akcie = df[df['Action'].str.lower().str.contains('buy|investment|deposit|sell|divestment|withdrawal|rebalancing', na=False)].copy()
    zoznam_tickerov_all = sorted(list(df_akcie['Ticker_Clean'].unique()))
    
    if zoznam_tickerov_all:
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
            skutocny_stav = st.number_input("Počet kusov vlastnených na T212:", min_value=0.0, value=0.0, step=0.00001, format="%.5f", key="vstup_pro_v30")
        with col_input2:
            aktualna_cena = st.number_input("Aktuálna trhová cena akcie (EUR):", min_value=0.0, value=0.0, step=0.01, format="%.2f", key="vstup_cena_v30")
        
        # Rekonštrukcia aktuálneho skladu cez FIFO
        df_ticker = df_akcie[df_akcie['Ticker_Clean'] == vybrany_ticker_pure].copy()
        df_ticker = df_ticker.sort_values(by='Time').reset_index(drop=True)
        
        sklad_aktualny = []
        for _, riadok in df_ticker.iterrows():
            typ = str(riadok['Action']).lower()
            shares = float(riadok['No. of shares']) if pd.notna(riadok['No. of shares']) else 0.0
            total = float(riadok['Total']) if pd.notna(riadok['Total']) else 0.0
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
                if predat_break_check := (potrebne_ks <= 1e-6):
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
            st.progress(float(pomer_safe))
            
            c1, c2 = st.columns(2)
            
            if aktualna_cena > 0:
                teoreticka_hodnota_safe = ks_bez_dane * aktualna_cena
                odhadovany_zisk_safe = teoreticka_hodnota_safe - vydavok_safe_balika
                c1.success(f"🔓 Môžete predať IHNEĎ BEZ DANE:\n**{ks_bez_dane:.5f} ks**\nHodnota: {teoreticka_hodnota_safe:.2f} EUR (Čistý zisk: +{odhadovany_zisk_safe:.2f} EUR)")
            else:
                c1.success(f"🔓 Môžete predať IHNEĎ BEZ DANE:\n**{ks_bez_dane:.5f} ks**")
            
            if aktualna_cena > 0 and ks_mlade > 0:
                prijem_mlade = ks_mlade * aktualna_cena
                zisk_mlade = max(0.0, prijem_mlade - vydavok_mladeho_balika)
                dan_mlade = round(zisk_mlade * 0.19, 2)
                odvody_mlade = round(zisk_mlade * 0.14, 2)
                celkova_hrozba = dan_mlade + odvody_mlade
