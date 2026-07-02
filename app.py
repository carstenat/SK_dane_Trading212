import streamlit as st
import pandas as pd
from datetime import datetime
import re

st.set_page_config(page_title="Trading 212 PRO Daňový Assistant", page_icon="📈", layout="wide")

# =========================================================================
# 💾 TRVALÁ PAMÄŤ CLOUDU
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
st.write("Profesionálny nástroj na kontrolu časového testu pred predajom akcií.")

uploaded_files = st.file_uploader("Sem presuňte vaše CSV exporty z Trading 212 (môžete aj viac naraz)", type=["csv"], accept_multiple_files=True, key="uploader_main_final")

if uploaded_files:
    zoznam_df = []
    for file in uploaded_files:
        zoznam_df.append(pd.read_csv(file))
    st.session_state.databaza_transakcii = pd.concat(zoznam_df, ignore_index=True)

# Funkcia na bezpečné očistenie textu na čisté float číslo
def bezpecne_cislo(hodnota):
    if pd.isna(hodnota):
        return 0.0
    text = str(hodnota).strip()
    # Odstránenie všetkého okrem čísel, pomlčky, bodky a čiarky (odmaže EUR, USD, atď.)
    text = re.sub(r'[^\d,\.-]', '', text)
    if ',' in text and '.' in text:
        text = text.replace(',', '') # tisícné separátory
    elif ',' in text:
        text = text.replace(',', '.') # európska desatinná čiarka
    try:
        return float(text)
    except:
        return 0.0

if st.session_state.databaza_transakcii is not None:
    df = st.session_state.databaza_transakcii.copy()
    
    # 🔍 UNIVERZÁLNE MAPOVANIE VARIÁCIÍ STĹPCOV (SK / EN)
    mapovanie_stlpcov = {}
    flags = {"time": False, "action": False, "ticker": False, "name": False, "shares": False, "price": False, "total": False, "wht": False}
    
    for c in df.columns:
        c_low = c.lower()
        if ('time' in c_low or 'čas' in c_low or 'datum' in c_low or 'dátum' in c_low) and not flags["time"]:
            mapovanie_stlpcov[c] = 'Time'
            flags["time"] = True
        elif ('action' in c_low or 'operácia' in c_low or 'operacia' in c_low or 'typ' in c_low) and not flags["action"]:
            mapovanie_stlpcov[c] = 'Action'
            flags["action"] = True
        elif ('ticker' in c_low or 'symbol' in c_low) and not flags["ticker"]:
            mapovanie_stlpcov[c] = 'Ticker'
            flags["ticker"] = True
        elif ('name' in c_low or 'názov' in c_low or 'nazov' in c_low or 'spoločnosť' in c_low) and not flags["name"]:
            mapovanie_stlpcov[c] = 'Name'
            flags["name"] = True
        elif ('shares' in c_low or 'kus' in c_low or 'počet' in c_low or 'pocet' in c_low or 'množstvo' in c_low) and not flags["shares"]:
            mapovanie_stlpcov[c] = 'No. of shares'
            flags["shares"] = True
        elif ('price' in c_low or 'cena' in c_low) and not flags["price"]:
            mapovanie_stlpcov[c] = 'Price per share'
            flags["price"] = True
        elif ('total' in c_low or 'celkom' in c_low or 'suma' in c_low or 'celková' in c_low) and not flags["total"]:
            mapovanie_stlpcov[c] = 'Total'
            flags["total"] = True
        elif ('withholding' in c_low or 'zrazen' in c_low or 'daň' in c_low or 'wht' in c_low) and not flags["wht"]:
            mapovanie_stlpcov[c] = 'Withholding tax'
            flags["wht"] = True
            
    df = df.rename(columns=mapovanie_stlpcov)
    
    # Priradenie fallback hodnôt pre stĺpce
    if 'Time' not in df.columns: df['Time'] = pd.NaT
    if 'Action' not in df.columns: df['Action'] = 'unknown'
    if 'Ticker' not in df.columns: df['Ticker'] = 'UNKNOWN'
    if 'Name' not in df.columns: df['Name'] = 'Neznáma spoločnosť'
    
    # 🌟 CRITICAL FIX: Vyčistenie finančných hodnôt od textových mien cez regex funkciu
    df['No. of shares'] = df['No. of shares'].apply(bezpecne_cislo)
    df['Total'] = df['Total'].apply(bezpecne_cislo)
    if 'Withholding tax' in df.columns:
        df['Withholding tax'] = df['Withholding tax'].apply(bezpecne_cislo)
    else:
        df['Withholding tax'] = 0.0

    df['Time'] = pd.to_datetime(df['Time'], errors='coerce').dt.tz_localize(None)
    df['Rok'] = df['Time'].dt.year
    df['Action_Clean'] = df['Action'].fillna('').astype(str).str.strip().str.lower()

    # =========================================================================
    # 📅 MODUL SELEKCIE DAŇOVÉHO OBDOBIA
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
    # 💰 GLOBÁLNE MODULY: DIVIDENDY A ÚROKY (S EXPANDERMI)
    # =========================================================================
    df_dividendy = df_filtrovane[df_filtrovane['Action_Clean'].str.contains('dividend', na=False)].copy()
    df_uroky = df_filtrovane[df_filtrovane['Action_Clean'].str.contains('interest', na=False)].copy()
    
    col_div, col_int = st.columns(2)
    
    with col_div:
        st.header(f"💰 Modul Dividend ({st.session_state.vybrany_rok})")
        if not df_dividendy.empty:
            total_div_gross = df_dividendy['Total'].sum()
            total_div_wht = df_dividendy['Withholding tax'].sum()
            total_div_net = total_div_gross - total_div_wht
            st.metric("Celkové pripísané dividendy (Brutto)", f"{total_div_gross:.2f} EUR")
            st.metric("Zahraničná zrazená daň (WHT)", f"{total_div_wht:.2f} EUR")
            st.write(f"**Čisté vyplatené dividendy (Netto):** {total_div_net:.2f} EUR")
        else:
            st.info("Pre zvolené obdobie sa nenašli žiadne dividendy.")
            
    with col_int:
        st.header(f"💶 Modul Úrokov ({st.session_state.vybrany_rok})")
        if not df_uroky.empty:
            total_interest_brutto = df_uroky['Total'].sum()
            dan_z_urokov = total_interest_brutto * 0.19
            total_interest_netto = total_interest_brutto - dan_z_urokov
            st.metric("Pripísané denné úroky (Brutto)", f"{total_interest_brutto:.2f} EUR")
            st.metric("Daňová povinnosť v SR (19%)", f"{dan_z_urokov:.2f} EUR")
            st.write(f"**Čistý výnos z úrokov po zdanení:** {total_interest_netto:.2f} EUR")
        else:
            st.info("Pre zvolené obdobie sa nenašli žiadne úroky z hotovosti.")

    # =========================================================================
    # 🌍 GLOBÁLNY DAŇOVÝ REPORT PORTFÓLIA (PANDAS ČISTENIE)
    # =========================================================================
    st.markdown("---")
    st.header(f"📊 Globálny daňový report portfólia pre obdobie: {st.session_state.vybrany_rok}")
    
    df_akcie_len = df.dropna(subset=['Time']).copy()
    df_akcie_len = df_akcie_len[~df_akcie_len['Action_Clean'].str.contains('dividend|interest', na=False)]
    df_akcie_len['Ticker_Clean'] = df_akcie_len['Ticker'].fillna('UNKNOWN').astype(str).str.strip().str.upper()
    df_akcie_len = df_akcie_len[(df_akcie_len['Ticker_Clean'] != '') & (df_akcie_len['Ticker_Clean'] != 'UNKNOWN')]
    df_akcie_len = df_akcie_len.sort_values(by='Time').reset_index(drop=True)
    
    databaza_mien = {}
    for _, riadok in df_akcie_len.iterrows():
        tick_c = riadok['Ticker_Clean']
        full_name = str(riadok.get('Name', 'Zjednodušená akcia')).strip()
        if full_name and full_name != 'nan':
            databaza_mien[tick_c] = full_name

    zoznam_tickerov_vsetky = sorted([t for t in df_akcie_len['Ticker_Clean'].unique()])
    
    realizovane_obchody_rok = []
    otvorene_loty_portfolio = {}

    # MATEMATICKÝ FIFO PARSER S DEFANZÍVNOU POISTKOU PROTI TICHÉMU PÁDU
    for t in zoznam_tickerov_vsetky:
        try:
            df_t = df_akcie_len[df_akcie_len['Ticker_Clean'] == t].copy()
