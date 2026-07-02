import streamlit as st
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Trading 212 PRO Daňový Assistant", page_icon="📈", layout="wide")

# =========================================================================
# 💾 TRVALÁ PAMÄŤ CLOUDU (OCHRANA PRED RESETOM SÚBOROV)
# =========================================================================
if "databaza_transakcii" not in st.session_state:
    st.session_state.databaza_transakcii = None

# =========================================================================
# 🎨 PRÉMIOVÝ FINTECH VZHĽAD
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
    st.session_state.databaza_transakcii = pd.concat(zoznam_df, ignore_index=True)

if st.session_state.databaza_transakcii is not None:
    df = st.session_state.databaza_transakcii.copy()
    
    # 🔍 UNIVERZÁLNE PREMENOVANIE STĹPCOV - Ochrana pred duplicitnými stĺpcami (napr. Total a Total (EUR))
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
    
    # Doplnenie chýbajúcich stĺpcov pre istotu
    if 'No. of shares' not in df.columns: df['No. of shares'] = 0.0
    if 'Total' not in df.columns: df['Total'] = 0.0
    if 'Withholding tax' not in df.columns: df['Withholding tax'] = 0.0
    
    df['Time'] = pd.to_datetime(df['Time'], errors='coerce').dt.tz_localize(None)
    
    # =========================================================================
    # 💰 GLOBÁLNE MODULY: DIVIDENDY A ÚROKY
    # =========================================================================
    df_dividendy = df[df['Action'].str.lower().str.contains('dividend', na=False)].copy()
    df_uroky = df[df['Action'].str.lower().str.contains('interest', na=False)].copy()
    
    st.markdown("---")
    col_div, col_int = st.columns(2)
    
    with col_div:
        st.header("💰 Modul Dividend")
        if not df_dividendy.empty:
            total_div_gross = pd.to_numeric(df_dividendy['Total'], errors='coerce').fillna(0.0).sum()
            total_div_wht = pd.to_numeric(df_dividendy['Withholding tax'], errors='coerce').fillna(0.0).sum()
            total_div_net = total_div_gross - total_div_wht
            
            st.metric("Celkové pripísané dividendy (Brutto)", f"{total_div_gross:.2f} EUR")
            st.metric("Zahraničná zrazená daň (WHT)", f"{total_div_wht:.2f} EUR")
            st.write(f"**Čisté vyplatené dividendy (Netto):** {total_div_net:.2f} EUR")
            
            with st.expander("Zobraziť históriu dividend"):
                st.dataframe(df_dividendy[['Time', 'Ticker', 'Action', 'Total']].head(100))
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
                st.dataframe(df_uroky[['Time', 'Action', 'Total']].head(100))
        else:
            st.info("V importovaných súboroch sa nenachádzajú žiadne záznamy o úrokoch z hotovosti.")

    # Spracovanie dát pre akcie
    df = df.dropna(subset=['Time', 'Ticker']).sort_values(by='Time').reset_index(drop=True)
    df['No. of shares'] = pd.to_numeric(df['No. of shares'], errors='coerce').fillna(0.0)
    df['Total'] = pd.to_numeric(df['Total'], errors='coerce').fillna(0.0)
    df['Ticker_Clean'] = df['Ticker'].fillna('').astype(str).str.strip().str.upper()
        
    databaza_mien = {}
    for _, riadok in df.iterrows():
        tick_c = str(riadok['Ticker_Clean'])
        full_name = str(riadok.get('Name', 'Zjednodušená akcia')).strip()
        if tick_c and tick_c != 'nan' and full_name and full_name != 'nan':
            if tick_c not in databaza_mien or len(full_name) > len(databaza_mien[tick_c]):
                databaza_mien[tick_c] = full_name

    # =========================================================================
    # 🔍 HLAVNÝ OPTIMALIZÁTOR POZÍCIE
    # =========================================================================
    st.markdown("---")
    st.header("🔍 Hlavný optimalizátor pozície")

    zoznam_tickerov = sorted([t for t in df['Ticker_Clean'].unique() if t != ''])
    
    if zoznam_tickerov:
        vybrany_ticker = st.selectbox("Vyberte akciový ticker pre detailnú analýzu časového testu:", zoznam_tickerov)
        
        df_ticker = df[df['Ticker_Clean'] == vybrany_ticker].copy()
        meno_akcie = databaza_mien.get(vybrany_ticker, "Neznámy titul")
        st.subheader(f"Analýza pre: {vybrany_ticker} - {meno_akcie}")
        
        df_nakupy = df_ticker[df_ticker['Action'].str.lower().str.contains('buy', na=False)].copy()
        
        if not df_nakupy.empty:
            aktualny_cas = datetime.now()
            kumulativne_kusy = 0.0
            kumulativne_naklady = 0.0
            
            riadky_analyzy = []
            
            for _, r in df_nakupy.iterrows():
                kusy = float(r['No. of shares'])
                total_cena = float(r['Total'])
                cas_nakupu = r['Time']
                
                if kusy > 0.00001:
                    priemerna_cena_za_kus = total_cena / kusy
                else:
                    priemerna_cena_za_kus = 0.0
                    
                dni_drzania = (aktualny_cas - cas_nakupu).days
                presiel_testom = dni_drzania >= 365
                status_testu = "✅ Oslobodené (DRŽANÉ NAD 1 ROK)" if presiel_testom else "❌ Podlieha dani (Menej ako 1 rok)"
                
                kumulativne_kusy += kusy
                kumulativne_naklady += total_cena
                
                riadky_analyzy.append({
                    "Dátum nákupu": cas_nakupu.strftime('%Y-%m-%d %H:%M'),
                    "Počet kusov": kusy,
                    "Nákupná cena za kus": f"{priemerna_cena_za_kus:.4f} EUR",
                    "Celkom zaplatené": f"{total_cena:.2f} EUR",
                    "Dni držania": dni_drzania,
                    "Časový test SR": status_testu
                })
            
            df_vysledok = pd.DataFrame(riadky_analyzy)
            
            col_m1, col_m2 = st.columns(2)
            with col_m1:
                st.metric("Celkový akumulovaný objem (Kusy)", f"{kumulativne_kusy:.4f}")
            with col_m2:
                st.metric("Celkové investované náklady", f"{kumulativne_naklady:.2f} EUR")
                
            st.write("### Detailný rozpad nákupných šarží (Lotov):")
            st.dataframe(df_vysledok, use_container_width=True)
            
            txt_info = "💡 **Tip pre daňovú optimalizáciu v SR:**\n"
            txt_info += "Slovenská legislatíva uplatňuje ročný časový test na predaj cenných papierov obchodovaných na regulovanej burze.\n"
            txt_info += "Ak plánujete pozíciu čiastočne redukovať, uistite sa, že uplatňujete metódu FIFO (First-In, First-Out)\n"
            txt_info += "a predávate prioritne tie šarže, ktoré majú v stĺpci Časový test status '✅ Oslobodené'.\n"
            st.info(txt_info)
        else:
            st.warning("Pre tento ticker neboli nájdené žiadne priame nákupné transakcie (BUY).")
    else:
        st.info("Databáza neobsahuje žiadne platné tickery pre akciové pozície.")
