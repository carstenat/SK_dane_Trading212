import streamlit as st
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Trading 212 PRO Daňový Assistant", page_icon="📈", layout="wide")

# =========================================================================
# 🎨 PRÉMIOVÝ FINTECH VZHĽAD (DEFAULT SVETLÝ, VYSOKÝ KONTRAST)
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
st.write("Profesionálny nástroj na kontrolu časového testu pred predajom akcií a ročné daňové podklady.")

uploaded_files = st.file_uploader("Sem presuňte vaše CSV exporty z Trading 212 (môžete aj viac naraz)", type=["csv"], accept_multiple_files=True, key="uploader_main_final")

if uploaded_files:
    zoznam_df = []
    for file in uploaded_files:
        zoznam_df.append(pd.read_csv(file))
        
    df_global = pd.concat(zoznam_df, ignore_index=True)
    df_global['Time'] = pd.to_datetime(df_global['Time'], errors='coerce').dt.tz_localize(None)
    df_global = df_global.dropna(subset=['Time']).sort_values(by='Time').reset_index(drop=True)
    
    df_global['No. of shares'] = pd.to_numeric(df_global['No. of shares'], errors='coerce').fillna(0.0)
    df_global['Total'] = pd.to_numeric(df_global['Total'], errors='coerce').fillna(0.0)
    df_global['Withholding tax'] = pd.to_numeric(df_global['Withholding tax'], errors='coerce').fillna(0.0)
    df_global['Ticker_Clean'] = df_global['Ticker'].fillna('').astype(str).str.strip().str.upper()
    df_global['Rok'] = df_global['Time'].dt.year
    
    databaza_mien = {}
    for _, riadok in df_global.iterrows():
        tick_c = str(riadok['Ticker_Clean'])
        full_name = str(riadok.get('Name', 'Zjednodušená akcia')).strip()
        if tick_c and tick_c != 'nan' and full_name and full_name != 'nan':
            if tick_c not in databaza_mien or len(full_name) > len(databaza_mien[tick_c]):
                databaza_mien[tick_c] = full_name

    # 📅 TRI ROČNÉ ZÁLOŽKY
    tab2024, tab2025, tab2026 = st.tabs(["📅 Daňový rok 2024", "📅 Daňový rok 2025", "📅 Daňový rok 2026"])
    
    roky_zoznam = [2024, 2025, 2026]
    tabs_zoznam = [tab2024, tab2025, tab2026]
    
    for i in range(3):
        r_rok = roky_zoznam[i]
        r_tab = tabs_zoznam[i]
        
        with r_tab:
            st.header(f"Optimalizátor a podklady pre rok {r_rok}")
            
            df_akcie = df_global[(df_global['Action'].str.lower().str.contains('buy|sell|nákup|nakup|predaj|market|limit', na=False)) & (df_global['Rok'] <= r_rok)].copy()
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
                vybrany_text = st.selectbox("Vyberte akciu zo svojho portfólia, ktorú plánujete predať:", ponuka_pre_menu, key=f"sel_linearna_{r_rok}")
                vybrany_ticker_pure = mapovanie_tickerov[vybrany_text]
                
                col1, col2 = st.columns(2)
                with col1:
                    vstup_vlastnene = st.number_input("Počet kusov vlastnených na platforme Trading 212:", min_value=0.0, value=0.0, step=0.00001, format="%.5f", key=f"vstup_stav_{r_rok}")
                with col2:
                    aktualna_cena = st.number_input("Aktuálna trhová cena akcie v EUR (voliteľné):", min_value=0.0, value=0.0, step=0.01, format="%.2f", key=f"vstup_cena_{r_rok}")
                
                df_ticker = df_akcie[df_akcie['Ticker_Clean'] == vybrany_ticker_pure].sort_values(by='Time').reset_index(drop=True)
                
                sklad_aktualny = []
                for _, riadok in df_ticker.iterrows():
                    typ = str(riadok['Action']).lower()
                    shares = float(riadok['No. of shares'])
                    total = float(riadok['Total'])
                    datum = riadok['Time']
                    
                    if 'buy' in typ or 'nákup' in typ or 'nakup' in typ:
                        if shares > 0.00001:
                            sklad_aktualny.append({'shares': shares, 'date': datum, 'cena_za_kus': total/shares})
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
                    st.error(f"⚠️ Pozor: Zadáli ste {vstup_vlastnene:.5f} ks, ale vo vašom sklade v roku {r_rok} zostáva len {max_sklad_dostupny:.5f} ks {vybrany_ticker_pure}. Orezávame na reálne maximum.")
                    skutocny_stav = max_sklad_dostupny
                    
                potrebne_ks = skutocny_stav
                dnes = datetime.now()
                ks_bez_dane = 0.0
                ks_mlade = 0.0
                vydavok_safe_balika = 0.0
                vydavok_mladeho_balika = 0.0
                
                rozpis_textov = []
                export_csv_riadky = [["Datum nakupu", "Mnozstvo (ks)", "Nakupna cena/ks", "Celkovy nakup", "Danovy stav", "Datum oslobodenia", "Zostava cakat"]]
                
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
                        export_csv_riadky.append([d_nakupu, f"{vziat_ks:.5f}", f"{n['cena_za_kus']:.2f}", f"{cena_balika:.2f}", "Bez dane", "Uz oslobodene", "0 dni"])
                    else:
                        ks_mlade += vziat_ks
                        vydavok_mladeho_balika += cena_balika
                        d_oslobodenia = (nakup_pure + pd.Timedelta(days=365)).strftime('%d.%m.%Y')
                        zostava_dni = 365 - vek_dni
                        riadok_prehladu = f"🔴 **ZDAŇUJE SA** | Nákup: {d_nakupu} | Množstvo: {text_mnozstva} pri cene {text_ceny} ({text_celkovo}) | ⏳ Zostáva čakať: **{zostava_dni} dní** (Oslobodenie: {d_oslobodenia})"
                        rozpis_textov.append(riadok_prehladu)
                        export_csv_riadky.append([d_nakupu, f"{vziat_ks:.5f}", f"{n['cena_za_kus']:.2f}", f"{cena_balika:.2f}", "Zdanuje sa", d_oslobodenia, f"{zostava_dni} dni"])
                
                ks_bez_dane = round(ks_bez_dane, 5)
                ks_mlade = round(ks_mlade, 5)
                
                st.markdown(f"**Vizuálny pomer safe pozície pre rok {r_rok}:** {ks_bez_dane:.5f} ks z {skutocny_stav:.5f} ks")
                vypocitany_pomer = float(ks_bez_dane / skutocny_stav) if skutocny_stav > 0 else 0.0
                st.progress(max(0.0, min(1.0, vypocitany_pomer)))
                
                # 🔓 BEZPEČNÁ ZELENÁ KARTA - Násobenie beží len ak je cena zadaná
                if aktualna_cena > 0:
                    trhova_hodnota_safe = ks_bez_dane * aktualna_cena
                    cisty_zisk_safe = max(0.0, trhova_hodnota_safe - vydavok_safe_balika)
