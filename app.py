import streamlit as st
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Trading 212 PRO Daňový Assistant", page_icon="📈", layout="wide")

# =========================================================================
# 🎨 FINTECH VZHĽAD (DEFAULT SVETLÝ, VYSOKÝ KONTRAST)
# =========================================================================
st.sidebar.header("⚙️ Nastavenia vzhľadu")
dark_mode = st.sidebar.checkbox("Zapnúť Tmavý režim (Dark Mode)", value=False)

if dark_mode:
    st.markdown("""
        <style>
        .stApp { background-color: #0B0F19 !important; color: #F8FAFC !important; }
        h1, h2, h3, label, p, span { color: #FFFFFF !important; }
        div[data-testid="stMetric"] { background-color: #1E293B !important; border: 2px solid #475569 !important; border-radius: 12px !important; padding: 14px 18px !important; }
        </style>
    """, unsafe_allow_html=True)
else:
    st.markdown("""
        <style>
        .stApp { background-color: #FFFFFF !important; color: #1E293B !important; }
        h1, h2 { color: #0F172A !important; }
        div[data-testid="stMetric"] { background-color: #F8FAFC !important; border: 2px solid #CBD5E1 !important; border-radius: 12px !important; padding: 14px 18px !important; }
        </style>
    """, unsafe_allow_html=True)

st.title("📈 Súkromný PRO Optimalizátor pre Trading 212 (SR)")
st.write("Profesionálny nástroj na kontrolu časového testu pred predajom akcií.")

# =========================================================================
# 📦 KRABICA Č. 1: HLAVNÝ OPTIMALIZÁTOR SKLADU (Náš zamknutý checkpoint)
# =========================================================================
def vypocitaj_a_zobraz_optimalizator(df):
    df_akcie = df[df['Action'].str.lower().str.contains('buy|investment|deposit|sell|divestment|withdrawal|rebalancing', na=False)].copy()
    
    df_akcie['Ticker_Clean'] = df_akcie['Ticker'].fillna('').astype(str).str.strip().str.upper()
    zoznam_tickerov_all = sorted([x for x in df_akcie['Ticker_Clean'].unique() if x and x != 'nan' and x != ''])
    
    databaza_mien = {}
    for _, riadok in df_akcie.iterrows():
        tick_c = str(riadok['Ticker_Clean'])
        full_name = str(riadok.get('Name', 'Zjednodušená akcia')).strip()
        if tick_c and tick_c != 'nan' and full_name and full_name != 'nan':
            if tick_c not in databaza_mien or len(full_name) > len(databaza_mien[tick_c]):
                databaza_mien[tick_c] = full_name
                
    if zoznam_tickerov_all:
        ponuka_pre_menu = []
        mapovanie_tickerov = {}
        for t in zoznam_tickerov_all:
            full_company_name = databaza_mien.get(t, "Spoločnosť z platformy")
            text_riadku = f"{t} - {full_company_name}"
            ponuka_pre_menu.append(text_riadku)
            mapovanie_tickerov[text_riadku] = t
            
        st.markdown("##")
        st.header("🔍 Daňový Optimalizátor pre dnešný predaj")
        ponuka_pre_menu = sorted(list(set(ponuka_pre_menu)))
        vybrany_text = st.selectbox("Vyberte akciu zo svojho portfólia, ktorú plánujete predať:", ponuka_pre_menu, key="sel_linearna_checkpoint")
        vybrany_ticker_pure = mapovanie_tickerov[vybrany_text]
        
        col1, col2 = st.columns(2)
        with col1:
            vstup_vlastnene = st.number_input("Počet kusov vlastnených na platforme Trading 212:", min_value=0.0, value=0.0, step=0.00001, format="%.5f", key="vstup_stav_checkpoint")
        with col2:
            aktualna_cena = st.number_input("Aktuálna trhová cena akcie v EUR (voliteľné):", min_value=0.0, value=0.0, step=0.01, format="%.2f", key="vstup_cena_checkpoint")
            
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
                for b in sklad_aktualny:
                    if predat_este > 1e-6 and b['shares'] > 0:
                        vziat = min(b['shares'], predat_este)
                        b['shares'] -= vziat
                        predat_este -= vziat
                sklad_aktualny = [x for x in sklad_aktualny if x['shares'] > 1e-6]
                
        max_sklad_dostupny = sum([x['shares'] for x in sklad_aktualny])
        
        if vstup_vlastnene > 0:
            if vstup_vlastnene > max_sklad_dostupny:
                st.error(f"⚠️ Pozor: Zadáli ste {vstup_vlastnene:.5f} ks, ale vo vašom reálnom sklade Trading 212 zostáva len {max_sklad_dostupny:.5f} ks {vybrany_ticker_pure}. Výpočet orezávame na vaše reálne maximum.")
                skutocny_stav = max_sklad_dostupny
            else:
                skutocny_stav = vstup_vlastnene
                
            if skutocny_stav > 0:
                potrebne_ks = skutocny_stav
                dnes = datetime.now()
                ks_bez_dane = 0.0
                ks_mlade = 0.0
                vydavok_safe_balika = 0.0
                vydavok_mladeho_balika = 0.0
                
                rozpis_textov = []
                
                for n in sklad_aktualny:
                    if potrebne_ks < 1e-5:
                        break
                    vziat_ks = min(n['shares'], potrebne_ks)
                    potrebne_ks -= vziat_ks
                    
                    nakup_pure = pd.to_datetime(n['date']).to_pydatetime()
                    vek_dni = (dnes.date() - nakup_pure.date()).days
                    cena_balika = vziat_ks * n['cena_za_kus']
                    
                    d_nakupu = nakup_pure.strftime('%d.%m.%Y')
                    text_mnozstva = f"{vziat_ks:.5f} ks"
                    text_ceny = f"{n['cena_za_kus']:.2f} EUR/ks"
                    text_celkovo = f"Spolu: {cena_balika:.2f} EUR"
                    
                    if vek_dni >= 365:
                        ks_bez_dane += vziat_ks
                        vydavok_safe_balika += cena_balika
                        riadok_prehladu = f"🟢 **BEZ DANE** | Nákup: {d_nakupu} | Množstvo: {text_mnozstva} pri cene {text_ceny} ({text_celkovo}) | ⏳ Netreba čakať (Oslobodené)"
                        rozpis_textov.append(riadok_prehladu)
                    else:
                        ks_mlade += vziat_ks
                        vydavok_mladeho_balika += cena_balika
                        d_oslobodenia = (nakup_pure + pd.Timedelta(days=365)).strftime('%d.%m.%Y')
                        zostava_dni = 365 - vek_dni
                        riadok_prehladu = f"🔴 **ZDAŇUJE SA** | Nákup: {d_nakupu} | Množstvo: {text_mnozstva} pri cene {text_ceny} ({text_celkovo}) | ⏳ Zostáva čakať: **{zostava_dni} dní** (Oslobodenie: {d_oslobodenia})"
                        rozpis_textov.append(riadok_prehladu)
                        
                ks_bez_dane = round(ks_bez_dane, 5)
                ks_mlade = round(ks_mlade, 5)
                
                st.markdown(f"**Vizuálny pomer safe pozície:** {ks_bez_dane:.5f} ks z {skutocny_stav:.5f} ks")
                st.progress(float(ks_bez_dane / skutocny_stav))
                
                trhova_hodnota_safe = ks_bez_dane * aktualna_cena
                cisty_zisk_safe = max(0.0, trhova_hodnota_safe - vydavok_safe_balika)
                st.success(f"🔓 Môžete predať IHNEĎ BEZ DANE: **{ks_bez_dane:.5f} ks** | Súčasná hodnota: {trhova_hodnota_safe:.2f} € (Čistý oslobodený zisk: +{cisty_zisk_safe:.2f} €)")
                
                trhova_hodnota_mlade = ks_mlade * aktualna_cena
                zisk_mlade = max(0.0, trhova_hodnota_mlade - vydavok_mladeho_balika)
                dan_19 = round(zisk_mlade * 0.19, 2)
                odvody_14 = round(zisk_mlade * 0.14, 2)
                celkovy_vypal_statu = dan_19 + odvody_14
                
                st.warning(f"🔒 POZOR, MLADÉ FRAKCIE (Zdaňujú sa pri predaji dnes): {ks_mlade:.5f} ks")
                st.error(f"⚠️ **Daňový rozpis pre mladé akcie:** Krátkodobý zisk: {zisk_mlade:.2f} EUR | Daň z príjmu (19%): {dan_19:.2f} EUR | Zdravotné odvody (14%): {odvody_14:.2f} EUR | Celkovo odovzdáte štátu: -{celkovy_vypal_statu:.2f} EUR")
                
                with st.expander("📋 Zobraziť detailný rozpis nákupných balíčkov (Frakcií)"):
                    st.write("Tu nájdete kompletný chronologický zoznam vašich nákupov, z ktorých je poskladaná dnešná otvorená pozícia:")
                    for r_text in rozpis_textov:
                        st.write(r_text)
        return vybrany_ticker_pure
    return None

# =========================================================================
# 🔒 KRABICA Č. 2: IDENTICKÝ PREHĽAD DIVIDEND (S 100% OPRAVENOU SYNTAXIU)
# =========================================================================
def vypocitaj_a_zobraz_dividendy(df, vybrany_ticker):
    if not vybrany_ticker:
        return
    try:
        df['Action_Lower'] = df['Action'].fillna('').astype(str).str.lower()
        df['Ticker_Clean'] = df['Ticker'].fillna('').astype(str).str.strip().str.upper()
        df_div = df[df['Action_Lower'].str.contains('dividend|dividenda', na=False)].copy()
        df_div_ticker = df_div[df_div['Ticker_Clean'] == vybrany_ticker].copy()
        
        with st.expander("💰 Zobraziť prehľad a zdanenie Dividend pre vybranú akciu"):
            if len(df_div_ticker) > 0:
                total_brutto = 0.0
