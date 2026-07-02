import streamlit as st
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Trading 212 PRO Daňový Assistant", page_icon="📈", layout="wide")

# Inicializácia trvalej pamäte pre výpočty (zamedzí resetovaniu tlačidla)
if 'vypocet_aktivny' not in st.session_state:
    st.session_state.vypocet_aktivny = False
if 'posledny_ticker' not in st.session_state:
    st.session_state.posledny_ticker = ""

# =========================================================================
# 🎨 PRÉMIOVÝ FINTECH VZHĽAD (DEFAULT SVETLÝ, VYSOKÝ KONTRAST)
# =========================================================================
st.sidebar.header("⚙️ Nastavenia vzhľadu")
dark_mode = st.sidebar.checkbox("Zapnúť Tmavý režim (Dark Mode)", value=False)

if dark_mode:
    st.markdown("<style>.stApp { background-color: #0B0F19 !important; color: #F8FAFC !important; } h1, h2, h3, label, p, span { color: #FFFFFF !important; } div[data-testid='stMetric'] { background-color: #1E293B !important; border: 2px solid #475569 !important; border-radius: 12px !important; padding: 14px 18px !important; }</style>", unsafe_allow_html=True)
else:
    st.markdown("<style>.stApp { background-color: #FFFFFF !important; color: #1E293B !important; } h1, h2 { color: #0F172A !important; } div[data-testid='stMetric'] { background-color: #F8FAFC !important; border: 2px solid #CBD5E1 !important; border-radius: 12px !important; padding: 14px 18px !important; }</style>", unsafe_allow_html=True)

st.title("📈 Súkromný PRO Optimalizátor pre Trading 212 (SR)")
st.write("Profesionálny nástroj na kontrolu časového testu pred predajom akcií.")

uploaded_files = st.file_uploader("Sem presuňte vaše CSV exporty z Trading 212 (môžete aj viac naraz)", type=["csv"], accept_multiple_files=True, key="uploader_main_final")

if uploaded_files:
    zoznam_df = []
    for file in uploaded_files:
        zoznam_df.append(pd.read_csv(file))
            
    df = pd.concat(zoznam_df, ignore_index=True)
    df['Time'] = pd.to_datetime(df['Time'], errors='coerce').dt.tz_localize(None)
    
    # =========================================================================
    # 💰 GLOBÁLNE MODULY: DIVIDENDY A ÚROKY (ZOBRAZENÉ HNEĎ)
    # =========================================================================
    df_dividendy = df[df['Action'].str.lower().str.contains('dividend', na=False)].copy()
    df_uroky = df[df['Action'].str.lower().str.contains('interest', na=False)].copy()
    
    st.markdown("---")
    col_div, col_int = st.columns(2)
    
    with col_div:
        st.header("💰 Modul Dividend")
        if not df_dividendy.empty:
            total_div_gross = pd.to_numeric(df_dividendy['Total'], errors='coerce').fillna(0.0).sum()
            total_div_wht = pd.to_numeric(df_dividendy.get('Withholding tax', 0), errors='coerce').fillna(0.0).sum()
            total_div_net = total_div_gross - total_div_wht
            
            st.metric("Celkové pripísané dividendy (Brutto)", f"{total_div_gross:.2f} EUR")
            st.metric("Zahraničná zrazená daň (WHT)", f"{total_div_wht:.2f} EUR")
            st.write(f"**Čisté vyplatené dividendy (Netto):** {total_div_net:.2f} EUR")
            
            with st.expander("Zobraziť históriu dividend"):
                st.dataframe(df_dividendy[['Time', 'Ticker', 'Action', 'Total', 'Withholding tax']])
        else:
            st.info("V importovaných súboroch sa nenachádzajú žiadne záznamy o dividendách.")
            
    with col_int:
        st.header("💶 Modul Úrokov")
        if not df_uroky.empty:
            total_interest_brutto = pd.to_numeric(df_uroky['Total'], errors='coerce').fillna(0.0).sum()
            dan_z_urokov = total_interest_brutto * 0.19
            total_interest_netto = total_interest_brutto - dan_z_urokov
            
            st.metric("Pripísané denné úroky (Brutto)", f"{total_interest_brutto:.2f} EUR")
            st.metric("Daňová povinnosť v SR (19%)", f"{dan_z_urokov:.2f} EUR")
            st.write(f"**Čistý výnos z úrokov po zdanení:** {total_interest_netto:.2f} EUR")
            
            with st.expander("Zobraziť históriu pripísaných úrokov"):
                st.dataframe(df_uroky[['Time', 'Action', 'Total']])
        else:
            st.info("V importovaných súboroch sa nenachádzajú žiadne záznamy o úrokoch z hotovosti.")

    # Spracovanie dát pre akcie
    df = df.dropna(subset=['Time', 'Ticker']).sort_values(by='Time').reset_index(drop=True)
    df['No. of shares'] = pd.to_numeric(df['No. of shares'], errors='coerce').fillna(0.0)
    df['Total'] = pd.to_numeric(df['Total'], errors='coerce').fillna(0.0)
    df['Withholding tax'] = pd.to_numeric(df['Withholding tax'], errors='coerce').fillna(0.0)
    df['Ticker_Clean'] = df['Ticker'].fillna('').astype(str).str.strip().str.upper()
        
    databaza_mien = {}
    for _, riadok in df.iterrows():
        tick_c = str(riadok['Ticker_Clean'])
        full_name = str(riadok.get('Name', 'Zjednodušená akcia')).strip()
        if tick_c and tick_c != 'nan' and full_name and full_name != 'nan':
            if tick_c not in databaza_mien or len(full_name) > len(databaza_mien[tick_c]):
                databaza_mien[tick_c] = full_name

    st.markdown("---")
    st.header("🔍 Hlavný optimalizátor pozície")
    
    df_akcie = df[df['Action'].str.lower().str.contains('buy|sell|nákup|nakup|predaj|market|limit', na=False)].copy()
    zoznam_tickerov_all = sorted([x for x in df_akcie['Ticker_Clean'].unique() if x and x != 'nan' and x != ''])
    
    if zoznam_tickerov_all:
        ponuka_pre_menu = []
        mapovanie_tickerov = {}
        for t in zoznam_tickerov_all:
            full_company_name = databaza_mien.get(t, "Spoločnosť z platformy")
            text_riadku = f"{t} - {full_company_name}"
            ponuka_pre_menu.append(text_riadku)
            mapovanie_tickerov[text_riadku] = t
            
        ponuka_pre_menu = sorted(list(set(ponuka_pre_menu)))
        vybrany_text = st.selectbox("Vyberte akciu zo svojho portfólia, ktorú plánujete predať:", ponuka_pre_menu, key="sel_linearna_final")
        vybrany_ticker_pure = mapovanie_tickerov[vybrany_text]
        
        # Ak používateľ zmení ticker, resetujeme stav výpočtu
        if st.session_state.posledny_ticker != vybrany_ticker_pure:
            st.session_state.vypocitany_pomer = False
            st.session_state.posledny_ticker = vybrany_ticker_pure
        
        col1, col2 = st.columns(2)
        with col1:
            vstup_vlastnene = st.number_input("Počet kusov plánovaných na predaj:", min_value=0.0, value=0.0, step=0.00001, format="%.5f", key="vstup_stav_final")
        with col2:
            aktualna_cena = st.number_input("Aktuálna trhová cena akcie v EUR:", min_value=0.0, value=0.0, step=0.01, format="%.2f", key="vstup_cena_final")
        
        spustit_vypocet = st.button("🚀 Spustiť daňový prepočet pre vybranú akciu", type="primary", use_container_width=True)
        
        if spustit_vypocet:
            if vstup_vlastnene > 0:
                st.session_state.vypocet_aktivny = True
            else:
                st.warning("⚠️ Zadajte najprv počet kusov väčší ako 0.")
                st.session_state.vypocet_aktivny = False
        
        # Ak je výpočet aktivovaný v Session State, trvalo ho zobrazíme
        if st.session_state.vypocet_aktivny:
            df_ticker = df_akcie[df_akcie['Ticker_Clean'] == vybrany_ticker_pure].sort_values(by='Time').reset_index(drop=True)
            
            # FIFO MOTOR
            sklad_aktualny = []
            for _, riadok in df_ticker.iterrows():
                typ = str(riadok['Action']).lower()
                shares = float(riadok['No. of shares'])
                total = float(riadok['Total'])
                datum = riadok['Time']
                
                if 'buy' in typ or 'nákup' in typ or 'nakup' in typ:
                    if shares > 0.00001:
                        sklad_aktualny.append({'shares': shares, 'date': datum, 'cena_za_kus': total / shares})
                elif 'sell' in typ or 'predaj' in typ or shares < 0:
                    predat_este = abs(shares)
                    for b in sklad_aktualny:
                        if predat_este > 1e-6 and b['shares'] > 0:
                            vziat = min(b['shares'], predat_este)
                            b['shares'] -= vziat
                            predat_este -= vziat
                    sklad_aktualny = [x for x in sklad_aktualny if x['shares'] > 1e-6]
            
            max_sklad_dostupny = sum([x['shares'] for x in sklad_aktualny])
            
            skutocny_stav = vstup_vlastnene
            if vstup_vlastnene > max_sklad_dostupny:
                st.error(f"⚠️ Pozor: Zadáli ste {vstup_vlastnene:.5f} ks, ale vo vašom sklade zostáva len {max_sklad_dostupny:.5f} ks {vybrany_ticker_pure}. Orezávame na reálne maximum.")
                skutocny_stav = max_sklad_dostupny
                
            potrebne_ks = skutocny_stav
            dnes = datetime.now()
            ks_bez_dane = 0.0
            ks_mlade = 0.0
            vydavok_safe_balika = 0.0
            vydavok_mladeho_balika = 0.0
            
            rozpis_textov = []
            zoznam_riadkov_exportu = []
            
            for n in sklad_aktualny:
                if potrebne_ks < 1e-5:
                    break
                vziat_ks = min(n['shares'], potrebne_ks)
                potrebne_ks -= vziat_ks
                
                nakup_pure = pd.to_datetime(n['date']).to_pydatetime()
                vek_dni = (dnes.date() - nakup_pure.date()).days
                cena_balika = vziat_ks * n['cena_za_kus']
                aktualna_hodnota_balika = vziat_ks * aktualna_cena
                zisk_balika = aktualna_hodnota_balika - cena_balika
                
                d_nakupu = nakup_pure.strftime('%d.%m.%Y')
                text_mnozstva = f"{vziat_ks:.5f} ks"
