import streamlit as st
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Trading 212 PRO Daňový Assistant", page_icon="📈", layout="wide")

# =========================================================================
# 🧮 IZOLOVANÝ LINEÁRNY FIFO ENGINE (Úplná eliminácia IndentationError)
# =========================================================================
def vykonaj_fifo_vypocet(df_akcie, vybrany_rok, databaza_mien):
    realizovane = []
    otvorene = {}
    zoznam_tickerov = sorted([t for t in df_akcie['Ticker_Clean'].unique() if t != ''])
    
    for t in zoznam_tickerov:
        df_t = df_akcie[df_akcie['Ticker_Clean'] == t].copy()
        nakupne_loty = []
        
        for idx, row in df_t.iterrows():
            akcia = str(row['Action_Clean'])
            množstvo = float(row['No. of shares'])
            total_val = float(row['Total'])
            cena_ks = (total_val / množstvo) if množstvo > 0 else 0.0
            
            is_buy = ('buy' in akcia or 'nákup' in akcia or 'nakup' in akcia or 'prijat' in akcia or 'deposit' in akcia)
            is_sell = ('sell' in akcia or 'predaj' in akcia or 'vydaj' in akcia)
            
            if is_buy:
                nakupne_loty.append({'množstvo': množstvo, 'cena_nakup': cena_ks, 'datum_nakup': row['Time']})
                
            if is_sell and len(nakupne_loty) > 0:
                množstvo_na_predaj = množstvo
                for lot in list(nakupne_loty):
                    if lot['množstvo'] <= 0 or množstvo_na_predaj <= 0:
                        continue
                    odpredane_množstvo = min(lot['množstvo'], množstvo_na_predaj)
                    lot['množstvo'] -= odpredane_množstvo
                    množstvo_na_predaj -= odpredane_množstvo
                    
                    zisk_z_predaja = (odpredane_množstvo * cena_ks) - (odpredane_množstvo * lot['cena_nakup'])
                    dni_drzania = (row['Time'] - lot['datum_nakup']).days
                    oslobodene = (dni_drzania >= 365)
                    
                    if vybrany_rok == "Všetky" or row['Rok'] == int(vybrany_rok):
                        realizovane.append({
                            'Ticker': t,
                            'Spoločnosť': databaza_mien.get(t, "Neznáma"),
                            'Kusy': odpredane_množstvo,
                            'Zisk/Strata': zisk_z_predaja,
                            'Oslobodené': "Áno (Časový test)" if oslobodene else "Nie (Podlieha dani)",
                            'Zdaniteľný Zisk': 0.0 if oslobodene else zisk_z_predaja
                        })
        otvorene[t] = [lot for lot in nakupne_loty if lot['množstvo'] > 0.000001]
    return realizovane, otvorene

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
st.write("Profesionálny nástroj na kontrolu časového testu pred predajom akcií.")

uploaded_files = st.file_uploader("Sem presuňte vaše CSV exporty z Trading 212 (môžete aj viac naraz)", type=["csv"], accept_multiple_files=True, key="uploader_main_final")

if uploaded_files:
    zoznam_df = []
    for file in uploaded_files:
        zoznam_df.append(pd.read_csv(file))
    st.session_state.databaza_transakcii = pd.concat(zoznam_df, ignore_index=True)

if st.session_state.databaza_transakcii is not None:
    df = st.session_state.databaza_transakcii.copy()
    
    # 🔍 INTA DIAGNOSTIKA - Hneď uvidíme reálnu štruktúru po nahratí
    with st.expander("🔍 Interná diagnostika CSV (Kliknite pre kontrolu stĺpcov)"):
        st.write("Nájdené stĺpce v súbore:", list(df.columns))
        st.write("Ukážka riadkov:", df.head(2))

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
    
    if 'Time' not in df.columns: df['Time'] = pd.NaT
    if 'Action' not in df.columns: df['Action'] = 'unknown'
    if 'Ticker' not in df.columns: df['Ticker'] = 'UNKNOWN'
    if 'Name' not in df.columns: df['Name'] = 'Neznáma spoločnosť'
    if 'No. of shares' not in df.columns: df['No. of shares'] = 0.0
    if 'Total' not in df.columns: df['Total'] = 0.0
    if 'Withholding tax' not in df.columns: df['Withholding tax'] = 0.0
    
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
            total_div_gross = pd.to_numeric(df_dividendy['Total'], errors='coerce').fillna(0.0).sum()
            total_div_wht = pd.to_numeric(df_dividendy['Withholding tax'], errors='coerce').fillna(0.0).sum()
            total_div_net = total_div_gross - total_div_wht
            st.metric("Celkové pripísané dividendy (Brutto)", f"{total_div_gross:.2f} EUR")
            st.metric("Zahraničná zrazená daň (WHT)", f"{total_div_wht:.2f} EUR")
            st.write(f"**Čisté vyplatené dividendy (Netto):** {total_div_net:.2f} EUR")
