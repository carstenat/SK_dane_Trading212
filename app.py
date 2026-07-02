import streamlit as st
import pandas as pd
from datetime import datetime
import re

st.set_page_config(page_title="Trading 212 PRO Daňový Assistant", page_icon="📈", layout="wide")

if "databaza_transakcii" not in st.session_state:
    st.session_state.databaza_transakcii = None

if "vybrany_rok" not in st.session_state:
    st.session_state.vybrany_rok = "Všetky"

def bezpecne_cislo(hodnota):
    if pd.isna(hodnota):
        return 0.0
    text = str(hodnota).strip()
    text = re.sub(r'[^\d,\.-]', '', text)
    if ',' in text and '.' in text:
        text = text.replace(',', '')
    elif ',' in text:
        text = text.replace(',', '.')
    try:
        return float(text)
    except:
        return 0.0

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
    
    mapovanie_stlpcov = {}
    flags = {"time": False, "action": False, "ticker": False, "name": False, "shares": False, "price": False, "total": False, "wht": False}
    
    for c in df.columns:
        c_low = c.lower()
        if ('time' in c_low or 'čas' in c_low or 'datum' in c_low) and not flags["time"]:
            mapovanie_stlpcov[c] = 'Time'
            flags["time"] = True
        elif ('action' in c_low or 'operácia' in c_low or 'typ' in c_low) and not flags["action"]:
            mapovanie_stlpcov[c] = 'Action'
            flags["action"] = True
        elif ('ticker' in c_low or 'symbol' in c_low) and not flags["ticker"]:
            mapovanie_stlpcov[c] = 'Ticker'
            flags["ticker"] = True
        elif ('name' in c_low or 'názov' in c_low or 'spoločnosť' in c_low) and not flags["name"]:
            mapovanie_stlpcov[c] = 'Name'
            flags["name"] = True
        elif ('shares' in c_low or 'kus' in c_low or 'množstvo' in c_low) and not flags["shares"]:
            mapovanie_stlpcov[c] = 'No. of shares'
            flags["shares"] = True
        elif ('price' in c_low or 'cena' in c_low) and not flags["price"]:
            mapovanie_stlpcov[c] = 'Price per share'
            flags["price"] = True
        elif ('total' in c_low or 'celkom' in c_low or 'suma' in c_low) and not flags["total"]:
            mapovanie_stlpcov[c] = 'Total'
            flags["total"] = True
        elif ('withholding' in c_low or 'zrazen' in c_low or 'daň' in c_low) and not flags["wht"]:
            mapovanie_stlpcov[c] = 'Withholding tax'
            flags["wht"] = True
            
    df = df.rename(columns=mapovanie_stlpcov)
    
    if 'Time' not in df.columns: df['Time'] = pd.NaT
    if 'Action' not in df.columns: df['Action'] = 'unknown'
    if 'Ticker' not in df.columns: df['Ticker'] = 'UNKNOWN'
    if 'Name' not in df.columns: df['Name'] = 'Neznáma spoločnosť'
    
    df['No. of shares'] = df['No. of shares'].apply(bezpecne_cislo)
    df['Total'] = df['Total'].apply(bezpecne_cislo)
    df['Withholding tax'] = df['Withholding tax'].apply(bezpecne_cislo) if 'Withholding tax' in df.columns else 0.0

    df['Time'] = pd.to_datetime(df['Time'], errors='coerce', format='mixed')
    df['Time'] = df['Time'].fillna(datetime.now())
    df['Time'] = df['Time'].dt.tz_localize(None)
    df['Rok'] = df['Time'].dt.year
    df['Action_Clean'] = df['Action'].fillna('').astype(str).str.strip().str.lower()

    st.markdown("---")
    st.sidebar.header("🔀 Nastavenia zoznamu akcií")
    metoda_zoradenia = st.sidebar.radio("Zoradiť zoznam spoločností podľa:", options=["Tickeru abecedne", "Názvu spoločnosti abecedne"])

    st.subheader("📅 Výber daňového obdobia na kontrolu")
    roky_v_datach = sorted([int(r) for r in df['Rok'].dropna().unique()])
    moznosti_rokov = ["Všetky"] + [str(r) for r in roky_v_datach]
    
    cols_roky = st.columns(len(moznosti_rokov))
    for idx, r_opt in enumerate(moznosti_rokov):
        with cols_roky[idx]:
            b_type = "primary" if st.session_state.vybrany_rok == r_opt else "secondary"
            if st.button(f"Rok {r_opt}" if r_opt != "Všetky" else "Všetky", key=f"btn_rok_{r_opt}", type=b_type):
                st.session_state.vybrany_rok = r_opt
                st.rerun()

    df_filtrovane = df.copy() if st.session_state.vybrany_rok == "Všetky" else df[df['Rok'] == int(st.session_state.vybrany_rok)].copy()

    df_dividendy = df_filtrovane[df_filtrovane['Action_Clean'].str.contains('dividend|dividenda|zrazená', na=False)].copy()
    df_uroky = df_filtrovane[df_filtrovane['Action_Clean'].str.contains('interest|úrok|urok', na=False)].copy()
    
    col_div, col_int = st.columns(2)
    with col_div:
        st.header(f"💰 Modul Dividend ({st.session_state.vybrany_rok})")
        if not df_dividendy.empty:
            total_div_gross = df_dividendy['Total'].sum()
            total_div_wht = df_dividendy['Withholding tax'].sum()
            st.metric("Celkové pripísané dividendy (Brutto)", f"{total_div_gross:.2f} EUR")
            st.metric("Zahraničná zrazená daň (WHT)", f"{total_div_wht:.2f} EUR")
            st.write(f"**Čisté dividendy:** {total_div_gross - total_div_wht:.2f} EUR")
        else:
            st.info("Žiadne dividendy.")
            
    with col_int:
        st.header(f"💶 Modul Úrokov ({st.session_state.vybrany_rok})")
        if not df_uroky.empty:
            total_interest_brutto = df_uroky['Total'].sum()
            st.metric("Pripísané denné úroky (Brutto)", f"{total_interest_brutto:.2f} EUR")
            st.metric("Daňová povinnosť v SR (19%)", f"{total_interest_brutto * 0.19:.2f} EUR")
        else:
            st.info("Žiadne úroky z hotovosti.")

    st.markdown("---")
    st.header(f"📊 Globálny daňový report portfólia pre obdobie: {st.session_state.vybrany_rok}")
    
    df_akcie_len = df.copy()
    df_akcie_len = df_akcie_len[df_akcie_len['Ticker'].notna()]
    df_akcie_len['Ticker_Clean'] = df_akcie_len['Ticker'].astype(str).str.strip().str.upper()
    df_akcie_len = df_akcie_len[(df_akcie_len['Ticker_Clean'] != '') & (df_akcie_len['Ticker_Clean'] != 'NONE') & (df_akcie_len['Ticker_Clean'] != 'NAN') & (df_akcie_len['Ticker_Clean'] != 'UNKNOWN')]
    df_akcie_len = df_akcie_len[~df_akcie_len['Action_Clean'].str.contains('dividend|dividenda|interest|úrok|urok|deposit|vklad|withdrawal', na=False)].sort_values(by='Time').reset_index(drop=True)
    
    databaza_mien = {}
    for _, riadok in df_akcie_len.iterrows():
        tick = str(riadok['Ticker_Clean'])
        if tick and tick != 'UNKNOWN':
            databaza_mien[tick] = str(riadok.get('Name', 'Zjednodušená akcia')).strip()

    realizovane_obchody_rok = []
    otvorene_loty_portfolio = {}
    zoznam_tickerov_vsetky = sorted([t for t in df_akcie_len['Ticker_Clean'].unique() if t and t != 'UNKNOWN'])

    for t in zoznam_tickerov_vsetky:
        df_t = df_akcie_len[df_akcie_len['Ticker_Clean'] == t].copy()
        nakupne_loty = []
        
        for idx, row in df_t.iterrows():
            množstvo = abs(float(row['No. of shares']))
            total_val = float(row['Total'])
            akcia = str(row['Action_Clean'])
            cena_ks = (total_val / množstvo) if množstvo > 0 else 0.0
            
            is_sell_action = ('sell' in akcia or 'predaj' in akcia)
            is_buy_action = ('buy' in akcia or 'nákup' in akcia or 'nakup' in akcia)
            
            if is_buy_action and not is_sell_action:
                nakupne_loty.append({'množstvo': množstvo, 'cena_nakup': cena_ks, 'datum_nakup': row['Time'], 'pôvodné': množstvo})
                continue
                
            if is_sell_action:
                množstvo_na_predaj = množstvo
                for i in range(len(nakupne_loty)):
                    if nakupne_loty[i]['množstvo'] <= 0 or množstvo_na_predaj <= 0:
                        continue
                    odpredane = min(nakupne_loty[i]['množstvo'], množstvo_na_predaj)
                    nakupne_loty[i]['množstvo'] -= odpredane
                    množstvo_na_predaj -= odpredane
                    
                    zisk = (odpredane * cena_ks) - (odpredane * nakupne_loty[i]['cena_nakup'])
                    dni = (row['Time'] - nakupne_loty[i]['datum_nakup']).days
                    oslobodene = (dni >= 365)
                    
                    if st.session_state.vybrany_rok == "Všetky" or row['Rok'] == int(st.session_state.vybrany_rok):
                        realizovane_obchody_rok.append({
                            'Ticker': t, 'Spoločnosť': databaza_mien.get(t, "Neznáma"), 'Kusy': odpredane,
                            'Zisk/Strata': zisk, 'Oslobodené': "Áno" if oslobodene else "Nie",
                            'Zdaniteľný Zisk': 0.0 if oslobodene else (zisk if zisk > 0 else 0.0)
                        })
        otvorene_loty_portfolio[t] = nakupne_loty

    if len(realizovane_obchody_rok) == 0:
        st.info(f"ℹ️ V daňovom období '{st.session_state.vybrany_rok}' ste nerealizovali žiadne predaje akcií.")
        zdanitelny_zisk_celkom = 0.0
    else:
        df_realizovane = pd.DataFrame(realizovane_obchody_rok)
        st.dataframe(df_realizovane, use_container_width=True)
        zdanitelny_zisk_celkom = max(0.0, df_realizovane['Zdaniteľný Zisk'].sum())

    # 🌟 ROBUSTNÉ UKOTVENIE METRÍK: Už nikdy nezmiznú, sú generované pred optimalizátorom
    col_m1, col_m2, col_m3 = st.columns(3)
    with col_m1: st.metric("Krátkodobý zdaniteľný zisk", f"{zdanitelny_zisk_celkom:,.2f} EUR")
    with col_m2: st.metric("Daň z príjmu (19%)", f"{zdanitelny_zisk_celkom * 0.19:,.2f} EUR")
