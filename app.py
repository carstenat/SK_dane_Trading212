import streamlit as st
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Trading 212 Daňový Asistent & Optimalizátor", page_icon="📈", layout="wide")

# =========================================================================
# 🎨 PREPÍNAČ PRE DARK MODE (ČISTÉ CSS)
# =========================================================================
st.sidebar.header("⚙️ Nastavenia vzhľadu")
dark_mode = st.sidebar.checkbox("Zapnúť Tmavý režim (Dark Mode)", value=True)

if dark_mode:
    st.markdown("""
        <style>
        .stApp { background-color: #121214 !important; color: #E1E1E6 !important; }
        h1, h2, h3, h4, h5, h6, label, p, span { color: #F4F4F5 !important; }
        .stTabs [data-baseweb="tab-list"] { background-color: #1A1A1E !important; border-radius: 8px; padding: 5px; }
        .stTabs [data-baseweb="tab"] { color: #A1A1AA !important; }
        .stTabs [aria-selected="true"] { color: #38BDF8 !important; font-weight: bold; }
        div[data-testid="stMetricValue"] { color: #38BDF8 !important; }
        .stDataFrame div { background-color: #1A1A1E !important; color: #E1E1E6 !important; }
        </style>
    """, unsafe_allow_html=True)

st.title("📈 Súkromný Daňový Asistent a Optimalizátor pre Trading 212 (SR)")
st.write("Nahrajte svoje CSV exporty z Trading 212 a získajte ročný daňový manuál + checker pre bezpečný predaj akcií.")

uploaded_files = st.file_uploader("Sem presuňte vaše CSV súbory (môžete aj viac naraz)", type=["csv"], accept_multiple_files=True)

if uploaded_files:
    zoznam_df = []
    for file in uploaded_files:
        zoznam_df.append(pd.read_csv(file))
        
    df = pd.concat(zoznam_df, ignore_index=True)
    df['Time'] = pd.to_datetime(df['Time'], errors='coerce').dt.tz_localize(None)
    df = df.dropna(subset=['Time']).sort_values(by='Time').reset_index(drop=True)
    
    # Vyčistíme názvy tickerov do jednotného formátu
    df['Ticker_Clean'] = df['Ticker'].fillna('').astype(str).str.replace("US ", "").str.replace("_US", "").str.replace("_US_EQ", "").str.replace("_EQ", "").str.replace(".US", "").str.strip().str.replace("_", "").str.replace(".", "").str.replace(" ", "").str.upper()
    
    # Vybudujeme databázu celých názvov spoločností
    databaza_mien = {}
    for _, riadok in df.iterrows():
        tick_c = str(riadok['Ticker_Clean'])
        full_name = str(riadok.get('Name', '')).strip()
        if tick_c and tick_c != 'nan' and full_name and full_name != 'nan':
            if tick_c not in databaza_mien or len(full_name) > len(databaza_mien[tick_c]):
                databaza_mien[tick_c] = full_name

    # =========================================================================
    # 🔥 1. ČASŤ: DAŇOVÝ OPTIMALIZÁTOR (NAVRCHU STRÁNKY)
    # =========================================================================
    st.markdown("##")
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
        vybrany_text = st.selectbox("Vyberte akciu zo svojho portfólia, ktorú plánujete predať:", ponuka_pre_menu)
        vybrany_ticker_pure = mapovanie_tickerov[vybrany_text]
        
        # POLÍČKO PRE KUSY S JEDINEČNÝM KĽÚČOM
        skutocny_stav = st.number_input(f"Zadajte presný počet kusov pre {vybrany_ticker_pure}, ktorý momentálne vidíte v platforme:", min_value=0.0, value=0.0, step=0.00001, format="%.5f", key="definitivny_vstup_optimalizator_v15")
        
        # Rekonštrukcia skladu pomocou FIFO
        df_ticker = df_akcie[df_akcie['Ticker_Clean'] == vybrany_ticker_pure].copy()
        df_ticker = df_ticker.sort_values(by='Time').reset_index(drop=True)
        
        sklad_aktualny = []
        for _, riadok in df_ticker.iterrows():
            typ = str(riadok['Action']).lower()
            shares = float(riadok['No. of shares']) if pd.notna(riadok['No. of shares']) else 0.0
            datum = riadok['Time']
            
            if 'buy' in typ or 'investment' in typ or 'deposit' in typ:
                if shares > 0:
                    sklad_aktualny.append({'shares': shares, 'date': datum})
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
            
            list_dat_nakupu = []
            list_mnozstiev = []
            list_stavov = []
            list_dat_oslobodenia = []
            list_cakania = []
            
            for n in sklad_aktualny:
                if potrebne_ks <= 1e-6:
                    break
                vziat_ks = min(n['shares'], potrebné_kopirovanie :=  potrebne_ks)
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
                    list_stavov.append("🔴 Zdaňuje sa (Mladá akcia)")
                    list_dat_oslobodenia.append((nakup_pure + pd.Timedelta(days=365)).strftime('%d.%m.%Y'))
                    list_cakania.append(f"⏳ {365 - vek_dni} dní")
            
            c1, c2 = st.columns(2)
            c1.success(f"🔓 Môžete predať IHNEĎ BEZ DANE:\n**{ks_bez_dane:.5f} ks**")
            c2.warning(f"🔒 MLADÉ FRAKCIE (Zdaňujú sa pri predaji dnes):\n**{ks_mlade:.5f} ks**")
            
            st.markdown("### 📋 Detailný rozpis balíčkov na vašom sklade:")
            tovarna_tabulky = pd.DataFrame({
                "Dátum nákupu": list_dat_nakupu,
                "Množstvo (ks)": list_mnozstiev,
                "Daňový stav": list_stavov,
                "Dátum oslobodenia": list_dat_oslobodenia,
                "Zostáva čakať": list_cakania
            })
            st.dataframe(tovarna_tabulky, use_container_width=True, hide_index=True)
            st.info("💡 **Ako čítať tabuľku:** Platforma Trading 212 predáva akcie chronologicky od najstarších (pravidlo FIFO). Sledujte zelené riadky – tie predáte bezpečne.")
        else:
            st.info("Pre zobrazenie daňového breakdownu zadajte do políčka vyššie množstvo väčšie ako 0.")

    # =========================================================================
    # 📑 2. ČASŤ: HISTORICKÉ ROČNÉ PREHĽADY PRE DAŇOVÉ PRIZNANIE (ÚPLNE PLOCHÁ STRUKTÚRA)
    # =========================================================================
    st.markdown("##")
    st.markdown("---")
    st.header("📑 Ročné podklady pre Daňové priznanie SR")
    
    sklad_historicky = {}
    vysledky_po_rokoch = {}
    
    for _, riadok in df.iterrows():
        typ = str(riadok['Action']).lower()
        tick_c = str(riadok['Ticker_Clean'])
        
        if not tick_c or tick_c == 'nan':
            continue
            
        shares = float(riadok['No. of shares']) if pd.notna(riadok['No. of shares']) else 0.0
        total = float(riadok['Total']) if pd.notna(riadok['Total']) else 0.0
        result = float(riadok['Result']) if pd.notna(riadok['Result']) else 0.0
        tax = float(riadok['Withholding tax']) if pd.notna(riadok['Withholding tax']) else 0.0
        datum = riadok['Time']
        rok = datum.year
        
        if rok not in vysledky_po_rokoch:
            vysledky_po_rokoch[rok] = {'uroky': 0.0, 'div_brutto': 0.0, 'div_dan': 0.0, 'zisk_do_roka': 0.0, 'zisk_po_roku': 0.0, 'prijmy_kratkodobe': 0.0, 'vydavky_kratkodobe': 0.0}
            
        if 'interest on cash' in typ:
            vysledky_po_rokoch[rok]['uroky'] += total
            continue
            
        if 'dividend' in typ:
            vysledky_po_rokoch[rok]['div_brutto'] += (total + tax)
            vysledky_po_rokoch[rok]['div_dan'] += tax
            continue
            
        if 'buy' in typ or 'investment' in typ or 'deposit' in typ:
            if tick_c not in sklad_historicky: 
                sklad_historicky[tick_c] = []
            if shares > 0:
                sklad_historicky[tick_c].append({'shares': shares, 'date': datum, 'cena_za_kus': total/shares})
            
