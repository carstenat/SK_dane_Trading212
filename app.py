import streamlit as st
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Trading 212 PRO Daňový Optimalizátor", page_icon="📈", layout="wide")

# =========================================================================
# 🎨 ULTRA-KOMPAKTNÝ FINTECH LUXUSNÝ DIZAJN (PRE MOBIL, TABLET AJ DESKTOP)
# =========================================================================
st.sidebar.header("⚙️ Vzhľad a Vychytávky")
dark_mode = st.sidebar.checkbox("Zapnúť Tmavý režim (Dark Mode)", value=True)

if dark_mode:
    st.markdown("""
        <style>
        /* Celkové zmenšenie medzier a kompaktnejší text */
        .stApp { background-color: #0F172A !important; color: #E2E8F0 !important; font-size: 14px !important; }
        h1 { font-size: 22px !important; font-weight: 700 !important; color: #F8FAFC !important; margin-bottom: 5px !important; }
        h2 { font-size: 18px !important; font-weight: 600 !important; color: #F1F5F9 !important; margin-top: 15px !important; }
        h3 { font-size: 15px !important; font-weight: 600 !important; color: #E2E8F0 !important; }
        div.block-container { padding-top: 1.5rem !important; padding-bottom: 1rem !important; }
        
        /* Moderné zaoblené karty pre metriky */
        div[data-testid="stMetric"] {
            background-color: #1E293B !important;
            border: 1px solid #334155 !important;
            border-radius: 12px !important;
            padding: 12px 16px !important;
            box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1) !important;
        }
        div[data-testid="stMetricValue"] { color: #38BDF8 !important; font-size: 20px !important; font-weight: 700 !important; }
        div[data-testid="stMetricLabel"] { color: #94A3B8 !important; font-size: 12px !important; }
        
        /* Responzívne a čisté záložky (Tabs) */
        .stTabs [data-baseweb="tab-list"] { background-color: #1E293B !important; border-radius: 10px; padding: 4px; gap: 4px; }
        .stTabs [data-baseweb="tab"] { color: #94A3B8 !important; padding: 6px 12px !important; font-size: 13px !important; border-radius: 6px; }
        .stTabs [aria-selected="true"] { background-color: #0EA5E9 !important; color: #FFFFFF !important; font-weight: 600 !important; }
        
        /* Poistenie tabuliek pre perfektné zobrazenie na mobile */
        .stDataFrame div { background-color: #1E293B !important; color: #E2E8F0 !important; border-radius: 8px; }
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
    
    # Príprava unifikovaných dát
    df['Ticker_Clean'] = df['Ticker'].fillna('').astype(str).str.replace("US ", "").str.replace("_US", "").str.replace("_US_EQ", "").str.replace("_EQ", "").str.replace(".US", "").str.strip().str.replace("_", "").str.replace(".", "").str.replace(" ", "").str.upper()
    
    databaza_mien = {}
    for _, riadok in df.iterrows():
        tick_c = str(riadok['Ticker_Clean'])
        full_name = str(riadok.get('Name', '')).strip()
        if tick_c and tick_c != 'nan' and full_name and full_name != 'nan':
            if tick_c not in databaza_mien or len(full_name) > len(databaza_mien[tick_c]):
                databaza_mien[tick_c] = full_name

    # =========================================================================
    # 🔥 1. ČASŤ: PROFESIONÁLNY DAŇOVÝ OPTIMALIZÁTOR PRED PREDAJOM
    # =========================================================================
    st.header("🔍 Daňový Optimalizátor pre dnešný predaj")
    
    df_akcie = df[df['Action'].str.lower().str.contains('buy|investment|deposit|sell|divestment|withdrawal|rebalancing', na=False)].copy()
    zoznam_tickerov_all = sorted(list(df_akcie['Ticker_Clean'].unique()))
    
    if zoznam_tickerov_all:
        ponuka_pre_menu = []
        mapovanie_tickerov = {}
        for t in zoznam_tickerov_all:
            full_company_name = databaza_mien.get(t, "Spoločnosť z platformy")
            ponuka_pre_menu.append(f"{t} - {full_company_name}")
            mapmapping_check = t
            mapovanie_tickerov[f"{t} - {full_company_name}"] = t
            
        ponuka_pre_menu = sorted(list(set(ponuka_pre_menu)))
        vybrany_text = st.selectbox("Vyberte akciu zo svojho portfólia:", ponuka_pre_menu)
        vybrany_ticker_pure = mapovanie_tickerov[vybrany_text]
        
        # Rozdelenie vstupu do dvoch stĺpcov pre maximálnu kompaktnosť na mobiloch
        col_input1, col_input2 = st.columns(2)
        with col_input1:
            skutocny_stav = st.number_input("Počet kusov vlastnených na T212:", min_value=0.0, value=0.0, step=0.00001, format="%.5f", key="vstup_pro_v15")
        with col_input2:
            aktualna_cena = st.number_input("Aktuálna trhová cena akcie (EUR) - voliteľné:", min_value=0.0, value=0.0, step=0.01, format="%.2f", help="Zadajte dnešnú cenu z T212 pre výpočet očakávaného zisku a daňových dopadov.")
        
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
            odhadovany_vydavok_mlade = 0.0
            
            list_dat_nakupu = []
            list_mnozstiev = []
            list_stavov = []
            list_dat_oslobodenia = []
            list_cakania = []
            
            for n in sklad_aktualny:
                if potrebne_ks <= 1e-6:
                    break
                vziat_ks = min(n['shares'], potrebne_ks)
                potrebne_ks -= vziat_ks
                
                nakup_pure = pd.to_datetime(n['date']).to_pydatetime()
                vek_dni = (dnes.date() - nakup_pure.date()).days
                
                list_dat_nakupu.append(nakup_pure.strftime('%d.%m.%Y'))
                list_mnozstiev.append(f"{vziat_ks:.5f}")
                
                if vek_dni >= 365:
                    ks_bez_dane += vziat_ks
                    list_stavov.append("🟢 Bez dane (Nad 1 rok)")
                    list_dat_oslobodenia.append("Už oslobodené")
                    list_cakania.append("0 dní")
                else:
                    ks_mlade += vziat_ks
                    odhadovany_vydavok_mlade += (vziat_ks * n['cena_za_kus'])
                    list_stavov.append("🔴 Zdaňuje sa (Mladá akcia)")
                    list_dat_oslobodenia.append((nakup_pure + pd.Timedelta(days=365)).strftime('%d.%m.%Y'))
                    list_cakania.append(f"⏳ {365 - vek_dni} dní")
            
            # Grafický prehľad (Progress Bar) namiesto zložitého koláča - šetrí miesto na smartfónoch
            pomer_safe = ks_bez_dane / skutocny_stav
            st.markdown(f"**Vizuálny pomer safe pozície:** {ks_bez_dane:.5f} ks z {skutocny_stav:.5f} ks")
            st.progress(float(pomer_safe))
            
            c1, c2 = st.columns(2)
            c1.metric("Môžete predať IHNEĎ BEZ DANE", f"{ks_bez_dane:.5f} ks", help="Tieto akcie držíte viac ako rok. Sú kompletne oslobodené.")
            
            # Ak používateľ zadal cenu, prepočítame reálnu hrozbu dane v EUR
            if aktualna_cena > 0 and ks_mlade > 0:
                prijem_mlade = ks_mlade * aktualna_cena
                cistorocny_zisk = max(0.0, prijem_mlade - odhadovany_vydavok_mlade)
                hrozba_dane = round(cistorocny_zisk * 0.19, 2)
                hrozba_odvodov = round(cistorocny_zisk * 0.14, 2)
                c2.metric("MLADÉ FRAKCIE (Hrozba daní)", f"{ks_mlade:.5f} ks", f"Hrozí daň + odvody: {hrozba_dane + hrozba_odvodov:.2f} EUR", delta_color="inverse", help="Akcie držíte kratšie ako rok. Pri predaji dnes zaplatíte štátu 19% daň + 14% zdravotné odvody zo zisku.")
            else:
