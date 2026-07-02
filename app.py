import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timezone

st.set_page_config(page_title="Trading 212 PRO Daňový Assistant", page_icon="📈", layout="wide")

# =========================================================================
# 💾 TRVALÁ PAMÄŤ CLOUDU (OCHRANA PRED RESETOM SÚBOROV)
# =========================================================================
if "databaza_transakcii" not in st.session_state:
    st.session_state.databaza_transakcii = None

if "vybrany_rok" not in st.session_state:
    st.session_state.vybrany_rok = "Všetky"

# =========================================================================
# 🎨 PRÉMIOVÝ FINTECH VZHĽAD A SIDEBAR
# =========================================================================
st.sidebar.header("⚙️ Nastavenia vzhľadu")
dark_mode = st.sidebar.checkbox("Zapnúť Tmavý režim (Dark Mode)", value=False)

st.sidebar.header("🔀 Nastavenia zoznamu akcií")
metoda_zoradenia = st.sidebar.radio(
    "Zoradiť zoznam spoločností podľa:",
    options=["Tickeru abecedne", "Názvu spoločnosti abecedne"]
)

if dark_mode:
    st.markdown("<style>.stApp { background-color: #0B0F19 !important; color: #F8FAFC !important; } h1, h2, h3, label, p, span { color: #FFFFFF !important; } div[data-testid='stMetric'] { background-color: #1E293B !important; border: 2px solid #475569 !important; border-radius: 12px !important; padding: 14px 18px !important; }</style>", unsafe_allow_html=True)
else:
    st.markdown("<style>.stApp { background-color: #FFFFFF !important; color: #1E293B !important; } h1, h2 { color: #0F172A !important; } div[data-testid='stMetric'] { background-color: #F8FAFC !important; border: 2px solid #CBD5E1 !important; border-radius: 12px !important; padding: 14px 18px !important; }</style>", unsafe_allow_html=True)

st.title("📈 Súkromný PRO Optimalizátor pre Trading 212 (SR)")
st.write("Profesionálny nástroj na kontrolu časového testu pred predajom akcií podľa legislatívy SR (2024+).")

uploaded_files = st.file_uploader("Sem presuňte vaše CSV exporty z Trading 212 (môžete aj viac naraz)", type=["csv"], accept_multiple_files=True, key="uploader_main_final")

if uploaded_files:
    zoznam_df = []
    for file in uploaded_files:
        try:
            zoznam_df.append(pd.read_csv(file))
        except Exception as e:
            st.error(f"Chyba pri načítaní súboru {file.name}: {e}")
    if zoznam_df:
        st.session_state.databaza_transakcii = pd.concat(zoznam_df, ignore_index=True)

if st.session_state.databaza_transakcii is not None:
    df = st.session_state.databaza_transakcii.copy()
    
    # 🔍 UNIVERZÁLNE PREMENOVANIE STŮPCOV
    mapovanie_stlpcov = {}
    najdeny_shares = False
    najdeny_total = False
    najdeny_wht = False
    
    for c in df.columns:
        if ('shares' in c.lower() or 'kus' in c.lower() or 'počet' in c.lower()) and not najdeny_shares:
            mapovanie_stlpcov[c] = 'No. of shares'
            najdeny_shares = True
        elif ('total' in c.lower() or 'celkom' in c.lower() or 'suma' in c.lower()) and not najdeny_total:
            mapovanie_stlpcov[c] = 'Total'
            najdeny_total = True
        elif ('withholding' in c.lower() or 'zrazen' in c.lower()) and not najdeny_wht:
            mapovanie_stlpcov[c] = 'Withholding tax'
            najdeny_wht = True
            
    df = df.rename(columns=mapovanie_stlpcov)
    
    if 'No. of shares' not in df.columns: df['No. of shares'] = 0.0
    if 'Total' not in df.columns: df['Total'] = 0.0
    if 'Withholding tax' not in df.columns: df['Withholding tax'] = 0.0
    
    df['Time'] = pd.to_datetime(df['Time'], errors='coerce').dt.tz_localize(None)
    df['Rok'] = df['Time'].dt.year
    df['Action_Clean'] = df['Action'].fillna('').astype(str).str.strip().str.lower()
    df['No. of shares'] = pd.to_numeric(df['No. of shares'], errors='coerce').fillna(0.0)
    df['Total'] = pd.to_numeric(df['Total'], errors='coerce').fillna(0.0)

    # Prečistenie dát pre akcie
    df_akcie_len = df.dropna(subset=['Time', 'Ticker']).copy()
    df_akcie_len['Ticker_Clean'] = df_akcie_len['Ticker'].astype(str).str.strip().str.upper()
    df_akcie_len = df_akcie_len[(df_akcie_len['Ticker_Clean'] != '') & (df_akcie_len['Ticker_Clean'] != 'NAN')]
    df_akcie_len = df_akcie_len.sort_values(by='Time').reset_index(drop=True)
    
    # Príprava čistej databázy mien (vždy String)
    databaza_mien = {}
    for _, riadok in df_akcie_len.iterrows():
        tick_c = riadok['Ticker_Clean']
        name_val = riadok.get('Name', tick_c)
        if pd.isna(name_val) or str(name_val).strip() == '':
            name_val = tick_c
        databaza_mien[tick_c] = str(name_val).strip()

    # =========================================================================
    # 📅 MODUL SELEKCIE DAŇOVÉHO OBDOBIA (UI Tlačidlá)
    # =========================================================================
    st.markdown("---")
    st.subheader("📅 Výber daňového obdobia na kontrolu")
    
    roky_v_datach = sorted([int(r) for r in df['Rok'].dropna().unique()])
    moznosti_rokov = ["Všetky"] + [str(r) for r in roky_v_datach]
    
    cols_roky = st.columns(len(moznosti_rokov))
    for idx, r_opt in enumerate(moznosti_rokov):
        with cols_roky[idx]:
            b_type = "primary" if st.session_state.vybrany_rok == r_opt else "secondary"
            if st.button(f"Rok {r_opt}" if r_opt != "Všetky" else "Všetky obdobia", type=b_type, key=f"btn_rok_{r_opt}"):
                st.session_state.vybrany_rok = r_opt
                st.rerun()

    if st.session_state.vybrany_rok == "Všetky":
        df_filtrovane = df.copy()
    else:
        df_filtrovane = df[df['Rok'] == int(st.session_state.vybrany_rok)].copy()

    # =========================================================================
    # 💰 GLOBÁLNE MODULY: DIVIDENDY A ÚROKY
    # =========================================================================
    df_dividendy = df_filtrovane[df_filtrovane['Action_Clean'].str.contains('dividend', na=False)].copy()
    df_uroky = df_filtrovane[df_filtrovane['Action_Clean'].str.contains('interest', na=False)].copy()
    
    col_div, col_int = st.columns(2)
    
    with col_div:
        st.header(f"💰 Modul Dividend ({st.session_state.vybrany_rok})")
        if not df_dividendy.empty:
            total_div_gross = pd.to_numeric(df_dividendy['Total'], errors='coerce').fillna(0.0).sum()
            total_div_wht = pd.to_numeric(df_dividendy['Withholding tax'], errors='coerce').fillna(0.0).sum()
            total_div_net = total_div_gross - total_div_wht
            
            st.metric("Celkové pripísané dividendy (Brutto)", f"{total_div_gross:.2f} EUR")
            st.metric("Zahraničná zrazená daň (WHT)", f"{total_div_wht:.2f} EUR")
            st.write(f"**Čisté vyplatené dividendy (Netto):** {total_div_net:.2f} EUR")
            
            with st.expander("Zobraziť históriu dividend pre toto obdobie"):
                st.dataframe(df_dividendy[['Time', 'Ticker', 'Total', 'Withholding tax']].head(100))
        else:
            st.info("Pre zvolené obdobie sa nenašli žiadne dividendy.")
            
    with col_int:
        st.header(f"💶 Modul Úrokov ({st.session_state.vybrany_rok})")
        if not df_uroky.empty:
            total_interest_brutto = pd.to_numeric(df_uroky['Total'], errors='coerce').fillna(0.0).sum()
            dan_z_urokov = total_interest_brutto * 0.19
            total_interest_netto = total_interest_brutto - dan_z_urokov
            
            st.metric("Pripísané denné úroky (Brutto)", f"{total_interest_brutto:.2f} EUR")
            st.metric("Daňová povinnosť v SR (19%)", f"{dan_z_urokov:.2f} EUR")
            st.write(f"**Čistý výnos z úrokov po zdanení:** {total_interest_netto:.2f} EUR")
            
            with st.expander("Zobraziť históriu pripísaných úrokov pre toto obdobie"):
                st.dataframe(df_uroky[['Time', 'Total']].head(100))
        else:
            st.info("Pre zvolené obdobie sa nenašli žiadne úroky z hotovosti.")

    # =========================================================================
    # ⚙️ JADRO CORE: PLOCHÝ FIFO ENGINE PRE CELÚ HISTÓRIU
    # =========================================================================
    priebezne_sarze = {}  # Ticker -> list of dicts (nákupy)
    realizovane_predaje_vsetky = [] # Všetky zatvorené obchody v histórii
    
    for _, riadok in df_akcie_len.iterrows():
        ticker = riadok['Ticker_Clean']
        akcia = riadok['Action_Clean']
        cas = riadok['Time']
        kusy = float(riadok['No. of shares'])
        celkom = float(riadok['Total'])
        
        if ticker not in priebezne_sarze:
            priebezne_sarze[ticker] = []
            
        if 'buy' in akcia or 'market buy' in akcia or 'limit buy' in akcia:
            if kusy > 0:
                cena_za_kus = celkom / kusy
                priebezne_sarze[ticker].append({
                    'Time': cas,
                    'Kusy_Povodny': kusy,
                    'Kusy_Ostava': kusy,
                    'Total_Povodny': celkom,
                    'Cena_Za_Kus': cena_za_kus
                })
                
        elif 'sell' in akcia or 'market sell' in akcia or 'limit sell' in akcia:
            if kusy > 0:
                ostava_na_predaj = kusy
                predajna_cena_za_kus = celkom / kusy
                pouzite_sarze_v_predaji = []
                
                while ostava_na_predaj > 0 and len(priebezne_sarze[ticker]) > 0:
                    najstarsi_nakup = priebezne_sarze[ticker][0]
                    
                    if najstarsi_nakup['Kusy_Ostava'] <= ostava_na_predaj:
                        vzaté_kusy = najstarsi_nakup['Kusy_Ostava']
                        ostava_na_predaj -= vzaté_kusy
                        pouzite_sarze_v_predaji.append({
