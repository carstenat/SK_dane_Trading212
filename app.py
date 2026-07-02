import streamlit as st
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Trading 212 PRO Daňový Assistant", page_icon="📈", layout="wide")

# =========================================================================
# 💾 TRVALÁ PAMÄŤ CLOUDU (OCHRANA PRED RESETOM SÚBOROV)
# =========================================================================
if "databaza_transakcii" not in st.session_state:
    st.session_state.databaza_transakcii = None

if "vybrany_rok" not in st.session_state:
    st.session_state.vybrany_rok = "Všetky"

# =========================================================================
# 🎨 PRÉMIOVÝ FINTECH VZHĽAD A NASTAVENIA ZORADENIA
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

if st.session_state.databaza_transakcii is not None:
    df = st.session_state.databaza_transakcii.copy()
    
    # 🔍 UNIVERZÁLNE PREMENOVANIE STĹPCOV - Ochrana pred duplicitnými stĺpcami
    mapovanie_stlpcov = {}
    najdeny_shares = False
    najdeny_total = False
    najdeny_wht = False
    
    for c in df.columns:
        if ('shares' in c.lower() or 'kus' in c.lower()) and not najdeny_shares:
            mapovanie_stlpcov[c] = 'No. of shares'
            najdeny_shares = True
        elif ('total' in c.lower() or 'celkom' in c.lower()) and not najdeny_total:
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
    
    # Pre-processing pre korektné názvy akcií
    df['Ticker_Clean'] = df['Ticker'].fillna('').astype(str).str.strip().str.upper()
    databaza_mien = {}
    for _, riadok in df.iterrows():
        tick_c = str(riadok['Ticker_Clean'])
        full_name = str(riadok.get('Name', 'Zjednodušená akcia')).strip()
        if tick_c and tick_c != 'nan' and full_name and full_name != 'nan':
            if tick_c not in databaza_mien or len(full_name) > len(databaza_mien[tick_c]):
                databaza_mien[tick_c] = full_name

    # =========================================================================
    # 📅 MODUL SELEKCIE DAŇOVÉHO OBDOBIA (Tlačidlá)
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
    df_dividendy = df_filtrovane[df_filtrovane['Action'].str.lower().str.contains('dividend', na=False)].copy()
    df_uroky = df_filtrovane[df_filtrovane['Action'].str.lower().str.contains('interest', na=False)].copy()
    
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
                st.dataframe(df_dividendy[['Time', 'Ticker', 'Action', 'Total']].head(100))
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
                st.dataframe(df_uroky[['Time', 'Action', 'Total']].head(100))
        else:
            st.info("Pre zvolené obdobie sa nenašli žiadne úroky z hotovosti.")

    df = df.dropna(subset=['Time', 'Ticker']).sort_values(by='Time').reset_index(drop=True)
    df['No. of shares'] = pd.to_numeric(df['No. of shares'], errors='coerce').fillna(0.0)
    df['Total'] = pd.to_numeric(df['Total'], errors='coerce').fillna(0.0)

    # =========================================================================
    # 🔍 HLAVNÝ OPTIMALIZÁTOR A FIFO ENGINE
    # =========================================================================
    st.markdown("---")
    st.header("🔍 Pokročilý FIFO Optimalizátor realizovaných a otvorených frakcií")

    zoznam_tickerov = sorted([t for t in df['Ticker_Clean'].unique() if t != ''])
    
    if zoznam_tickerov:
        mapovanie_zobrazenia = {}
        list_prvkov = []
        
        for t in zoznam_tickerov:
            meno_firmy = databaza_mien.get(t, "Neznámy titul")
            retazec = f"{t} - {meno_firmy}"
            mapovanie_zobrazenia[retazec] = (t, meno_firmy)
            list_prvkov.append(retazec)
            
        # 🔀 Dynamické zoradenie podľa vybranej preferencie v sidebare
        if metoda_zoradenia == "Názvu spoločnosti abecedne":
            list_na_zobrazenie = sorted(list_prvkov, key=lambda x: mapovanie_zobrazenia[x][1].lower())
        else:
            list_na_zobrazenie = sorted(list_prvkov, key=lambda x: mapovanie_zobrazenia[x][0].lower())
            
        vybrany_text = st.selectbox("Vyberte akciu alebo ETF (môžete do okna priamo písať a hľadať):", list_na_zobrazenie)
        skutocny_ticker = mapovanie_zobrazenia[vybrany_text][0]
        
        df_ticker = df[df['Ticker_Clean'] == skutocny_ticker].copy()
        st.subheader(f"FIFO analýza lotov pre: {vybrany_text}")
        
        vsetky_transakcie = df_ticker[df_ticker['Action'].str.lower().str.contains('buy|sell', na=False)].copy()
        
        nakupne_loty = []
        realizovane_obchody = []
        
        for _, r in vsetky_transakcie.iterrows():
            akcia = r['Action'].lower()
            kusy = float(r['No. of shares'])
            celkovy_objem = float(r['Total'])
            cas_tx = r['Time']
            rok_tx = r['Rok']
            
            if 'buy' in akcia:
                if kusy > 0.00001:
                    nakupne_loty.append({
                        "Time": cas_tx,
                        "Kusy_Povodny": kusy,
                        "Kusy_Zostatok": kusy,
                        "Total_Cena": celkovy_objem,
                        "Cena_Za_Kus": celkovy_objem / kusy,
                        "Rok": rok_tx
