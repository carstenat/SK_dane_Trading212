import streamlit as st
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Trading 212 PRO Daňový Asistent & Optimalizátor", page_icon="📈", layout="wide")

# =========================================================================
# 🎨 PREPÍNAČ PRE DARK / LIGHT MODE (DEFAULT SVETLÝ)
# =========================================================================
st.sidebar.header("⚙️ Nastavenia vzhľadu")
dark_mode = st.sidebar.checkbox("Zapnúť Tmavý režim (Dark Mode)", value=False)

if dark_mode:
    st.markdown("""
        <style>
        .stApp { background-color: #121214 !important; color: #E1E1E6 !important; }
        h1, h2, h3, h4, h5, h6, label, p, span { color: #F4F4F5 !important; }
        .stTabs [data-baseweb="tab-list"] { background-color: #1A1A1E !important; border-radius: 8px; padding: 5px; }
        .stTabs [data-baseweb="tab"] { color: #A1A1AA !important; }
        .stTabs [aria-selected="true"] { color: #38BDF8 !important; font-weight: bold; }
        div[data-testid="stMetricValue"] { color: #38BDF8 !important; font-weight: bold; }
        .stDataFrame div { background-color: #1A1A1E !important; color: #E1E1E6 !important; }
        </style>
    """, unsafe_allow_html=True)
else:
    st.markdown("""
        <style>
        div[data-testid="stMetric"] { background-color: #F8FAFC !important; border: 1px solid #CBD5E1 !important; border-radius: 12px !important; padding: 14px 18px !important; }
        div[data-testid="stMetricValue"] { color: #0284C7 !important; font-weight: 800 !important; }
        </style>
    """, unsafe_allow_html=True)

st.title("📈 Súkromný PRO Optimalizátor pre Trading 212 (SR)")
st.write("Profesionálny Nástroj na kontrolu časového testu pred predajom a automatickú ročnú daňovú uzávierku.")

uploaded_files = st.file_uploader("Sem presuňte vaše CSV súbory (môžete aj viac naraz)", type=["csv"], accept_multiple_files=True)

if uploaded_files:
    zoznam_df = []
    for file in uploaded_files:
        zoznam_df.append(pd.read_csv(file))
        
    df = pd.concat(zoznam_df, ignore_index=True)
    df['Time'] = pd.to_datetime(df['Time'], errors='coerce').dt.tz_localize(None)
    df = df.dropna(subset=['Time']).sort_values(by='Time').reset_index(drop=True)
    
    df['No. of shares'] = pd.to_numeric(df['No. of shares'], errors='coerce').fillna(0.0)
    df['Total'] = pd.to_numeric(df['Total'], errors='coerce').fillna(0.0)
    df['Result'] = pd.to_numeric(df['Result'], errors='coerce').fillna(0.0)
    df['Withholding tax'] = pd.to_numeric(df['Withholding tax'], errors='coerce').fillna(0.0)
    
    df['Ticker_Clean'] = df['Ticker'].fillna('').astype(str).str.replace("US ", "").str.replace("_US", "").str.replace("_US_EQ", "").str.replace("_EQ", "").str.replace(".US", "").str.strip().str.replace("_", "").str.replace(".", "").str.replace(" ", "").str.upper()
    
    databaza_mien = {}
    for _, riadok in df.iterrows():
        tick_c = str(riadok['Ticker_Clean'])
        full_name = str(riadok.get('Name', 'Zjednodušená akcia')).strip()
        if tick_c and tick_c != 'nan' and full_name and full_name != 'nan':
            if tick_c not in databaza_mien or len(full_name) > len(databaza_mien[tick_c]):
                databaza_mien[tick_c] = full_name

    # =========================================================================
    # 🔥 1. ČASŤ: DAŇOVÝ OPTIMALIZÁTOR PRE DNEŠNÝ PREDAJ (HORE)
    # =========================================================================
    st.markdown("##")
    st.header("🔍 Daňový Optimalizátor pre dnešný predaj")
    
    df_akcie = df[df['Action'].str.lower().str.contains('buy|investment|deposit|sell|divestment|withdrawal|rebalancing', na=False)].copy()
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
        vybrany_text = st.selectbox("Vyberte akciu zo svojho portfólia, ktorú plánujete predať:", ponuka_pre_menu, key="selectbox_stabilna_v85")
        vybrany_ticker_pure = mapovanie_tickerov[vybrany_text]
        
        col1, col2 = st.columns(2)
        with col1:
            skutocny_stav = st.number_input(f"Zadajte presný počet kusov pre {vybrany_ticker_pure}, ktorý momentálne vidíte v platforme:", min_value=0.0, value=0.0, step=0.00001, format="%.5f", key="vstup_stav_stabilny_v85")
        with col2:
            aktualna_cena = st.number_input("Aktuálna trhová cena akcie v EUR (voliteľné):", min_value=0.0, value=0.0, step=0.01, format="%.2f", key="vstup_cena_pro_v85")
        
        df_ticker = df_akcie[df_akcie['Ticker_Clean'] == vybrany_ticker_pure].sort_values(by='Time').reset_index(drop=True)
        
        sklad_aktualny = []
        for _, riadok in df_ticker.iterrows():
            typ = str(riadok['Action']).lower()
            shares = float(riadok['No. of shares'])
            total = float(riadok['Total'])
            datum = riadok['Time']
            
            if 'buy' in typ or 'investment' in typ or 'deposit' in typ:
                if shares > 0.00001:
                    sklad_aktualny.append({'shares': shares, 'date': datum, 'cena_za_kus': total/shares})
            elif 'sell' in typ or 'divestment' in typ or 'withdrawal' in typ or 'rebalancing' in typ or shares < 0:
                predat_este = abs(shares)
                while predat_este > 1e-6 and len(sklad_aktualny) > 0:
                    prvy_balicek = sklad_aktualny[0]
                    if prvy_balicek['shares'] <= predat_este:
                        predat_este -= prvy_balicek['shares']
                        sklad_aktualny.pop(0)
                    else:
                        prvy_balicek['shares'] -= predat_este
                        predat_este = 0.0
        
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
            
            # Bezpečné lineárne prechádzanie zoznamu (0% šanca na zacyklenie)
            temp_optimalizator_sklad = [dict(x) for x in sklad_aktualny]
            for n in temp_optimalizator_sklad:
                if potrebne_ks < 1e-5:
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
            
            c1, c2 = st.columns(2)
            
            if aktualna_cena > 0:
                trhova_hodnota_safe = ks_bez_dane * aktualna_cena
                cisty_zisk_safe = max(0.0, trhova_hodnota_safe - vydavok_safe_balika)
                c1.metric("Môžete predať IHNEĎ BEZ DANE", f"{ks_bez_dane:.5f} ks", f"Hodnota: {trhova_hodnota_safe:.2f} € (Zisk: +{cisty_zisk_safe:.2f} €)")
                
                prijem_mlade = ks_mlade * aktualna_cena
                zisk_mlade = max(0.0, prijem_mlade - vydavok_mladeho_balika)
                celkova_hrozba = round((zisk_mlade * 0.19) + (zisk_mlade * 0.14), 2)
                c2.metric("MLADÉ FRAKCIE (Zdaňujú sa dnes)", f"{ks_mlade:.5f} ks", f"Hrozba štátu: -{celkova_hrozba:.2f} EUR", delta_color="inverse")
            else:
                c1.metric("Môžete predať IHNEĎ BEZ DANE", f"{ks_bez_dane:.5f} ks")
                c2.metric("MLADÉ FRAKCIE (Zdaňujú sa pri predaji dnes)", f"{ks_mlade:.5f} ks")
            
            st.markdown("### 📋 Detailný rozpis balíčkov na vašom sklade:")
            tovarna_tabulky = pd.DataFrame({
                "Dátum nákupu": list_dat_nakupu,
                "Množstvo (ks)": list_mnozstiev,
                "Nákupná cena/ks": list_povodna_cena,
                "Celkový nákup": list_celkovy_nakup,
                "Daňový stav": list_stavov,
                "Dátum oslobodenia": list_dat_oslobodenia,
                "Zostáva čakať": list_cakania
            })
            st.dataframe(tovarna_tabulky, use_container_width=True, hide_index=True)
            
            csv_data = tovarna_tabulky.to_csv(index=False).encode('utf-8')
