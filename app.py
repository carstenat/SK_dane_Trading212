import streamlit as st
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Trading 212 Daňový Asistent & Optimalizátor", page_icon="📈", layout="wide")

# =========================================================================
# 🎨 FUNKČNÝ PREPÍNAČ PRE DARK MODE (ČISTÉ CSS)
# =========================================================================
st.sidebar.header("⚙️ Nastavenia vzhľadu")
dark_mode = st.sidebar.checkbox("Zapnúť Tmavý režim (Dark Mode)", value=True)

if dark_mode:
    st.markdown("""
        <style>
        .stApp {
            background-color: #121214 !important;
            color: #E1E1E6 !important;
        }
        h1, h2, h3, h4, h5, h6, label, p, span {
            color: #F4F4F5 !important;
        }
        .stTabs [data-baseweb="tab-list"] {
            background-color: #1A1A1E !important;
            border-radius: 8px;
            padding: 5px;
        }
        .stTabs [data-baseweb="tab"] {
            color: #A1A1AA !important;
        }
        .stTabs [aria-selected="true"] {
            color: #38BDF8 !important;
            font-weight: bold;
        }
        div[data-testid="stMetricValue"] {
            color: #38BDF8 !important;
        }
        .stDataFrame div {
            background-color: #1A1A1E !important;
            color: #E1E1E6 !important;
        }
        </style>
    """, unsafe_allow_html=True)

# Main obsah
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
    
    df['Ticker_Clean'] = df['Ticker'].fillna('').astype(str).str.replace("US ", "").str.replace("_US", "").str.replace("_US_EQ", "").str.replace("_EQ", "").str.replace(".US", "").str.strip().str.replace("_", "").str.replace(".", "").str.replace(" ", "").str.upper()
    
    sklad_historicky = {}
    databaza_mien = {}
    vysledky_po_rokoch = {}
    
    # =========================================================================
    # KROK 1: HISTORICKÁ FIFO MATEMATIKA PRE ROČNÉ PREHĽADY
    # =========================================================================
    for _, riadok in df.iterrows():
        typ = str(riadok['Action']).lower()
        tick_c = str(riadok['Ticker_Clean'])
        full_name = str(riadok.get('Name', 'Neznáma spoločnosť')).strip()
        
        if not tick_c or tick_c == 'nan':
            continue
            
        if pd.notna(riadok.get('Name')) and full_name and full_name != 'nan':
            if tick_c not in databaza_mien or len(full_name) > len(databaza_mien[tick_c]):
                databaza_mien[tick_c] = full_name
        
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
            
        if ('sell' in typ or 'divestment' in typ or 'withdrawal' in typ) and abs(result) < 2.0 and total < 10.0:
            continue
            
        if 'buy' in typ or 'investment' in typ or 'deposit' in typ:
            if tick_c not in sklad_historicky: 
                sklad_historicky[tick_c] = []
            if shares > 0:
                sklad_historicky[tick_c].append({'shares': shares, 'date': datum, 'cena_za_kus': total/shares if shares > 0 else 0.0})
            
        elif 'sell' in typ or 'divestment' in typ or 'withdrawal' in typ or 'rebalancing' in typ or shares < 0:
            predat_este = abs(shares)
            riadok_po_roku = 0.0
            riadok_do_roka = 0.0
            riadok_vydavok = 0.0
            
            if tick_c in sklad_historicky and sklad_historicky[tick_c]:
                temp_sklad = list(sklad_historicky[tick_c])
                sklad_historicky[tick_c] = []
                
                for balicek in temp_sklad:
                    if predat_este <= 1e-6:
                        sklad_historicky[tick_c].append(balicek)
                        continue
                        
                    vek = datum - balicek['date']
                    splnil_rok = vek.days >= 365
                    
                    if balicek['shares'] <= predat_este:
                        pomer = balicek['shares'] / abs(shares)
                        if splnil_rok: riadok_po_roku += (result * pomer)
                        else:
                            riadok_do_roka += (result * pomer)
                            riadok_vydavok += (balicek['shares'] * balicek['cena_za_kus'])
                        predat_este -= balicek['shares']
                    else:
                        pomer = predat_este / abs(shares)
                        if splnil_rok: riadok_po_roku += (result * pomer)
                        else:
                            riadok_do_roka += (result * pomer)
                            riadok_vydavok += (predat_este * balicek['cena_za_kus'])
                        
                        zostatok_shares = balicek['shares'] - predat_este
                        sklad_historicky[tick_c].append({'shares': zostatok_shares, 'date': balicek['date'], 'cena_za_kus': balicek['cena_za_kus']})
                        predat_este = 0.0
                        
            vysledky_po_rokoch[rok]['zisk_do_roka'] += riadok_do_roka
            vysledky_po_rokoch[rok]['zisk_po_roku'] += riadok_po_roku
            if riadok_do_roka != 0:
                vysledky_po_rokoch[rok]['prijmy_kratkodobe'] += total
                vysledky_po_rokoch[rok]['vydavky_kratkodobe'] += riadok_vydavok

    st.success("🚀 Analýza exportov úspešne dokončená!")
    
    # -------------------------------------------------------------------------
    # ZOBRAZENIE ROČNÝCH PREHĽADOV PRE DAŇOVÉ PRIZNANIE (SEKCIA 1)
    # -------------------------------------------------------------------------
    st.header("📑 Ročné podklady pre Daňové priznanie SR")
    roky_zoznam = sorted(list(vysledky_po_rokoch.keys()), reverse=True)
    moje_tabs = st.tabs([f"📅 Rok {r}" for r in roky_zoznam])
    
    for index, r in enumerate(roky_zoznam):
        v = vysledky_po_rokoch[r]
        oslobodeny_zisk = max(0.0, v['zisk_do_roka'])
        priznany_zisk_po_oslobodeni = max(0.0, oslobodeny_zisk - 500.0) if oslobodeny_zisk > 0 else 0.0
        
        realna_dan_uroky = round(v['uroky'] * 0.19, 2)
        realna_dan_akcie = round(priznany_zisk_po_oslobodeni * 0.19, 2)
        realne_odvody_akcie = round(priznany_zisk_po_oslobodeni * 0.14, 2)
        celkovo = realna_dan_uroky + realna_dan_akcie + realne_odvody_akcie
        
        with moje_tabs[index]:
            col1, col2 = st.columns(2)
            col1.metric("Celková daňová povinnosť", f"{celkovo:.2f} EUR", help="Suma dane z úrokov a krátkodobých ziskov nad limit 500€ + 14% zdravotné odvody.")
            col2.metric("Dlhodobý zisk (OSLOBODENÝ OD DANE)", f"{v['zisk_po_roku']:.2f} EUR", help="Zisk z pozícií držaných nad 1 rok. Tento zisk je kompletne oslobodený podľa § 9 zákona o dani z príjmov.")
            st.markdown("---")
            st.subheader("📑 VIII. ODDIEL - Kapitálový majetok")
            st.write(f"**Riadok 2 (Úroky z hotovosti):** Príjmy: `{v['uroky']:.2f} EUR` | Predbežná daň (19%): `{realna_dan_uroky:.2f} EUR`")
            st.subheader("📑 PRÍLOHA č. 2 - Dividendy")
            st.write(f"**Riadok 1:** Príjem Brutto: `{v['div_brutto']:.2f} EUR` | Daň zaplatená v zahraničí: `{v['div_dan']:.2f} EUR` *(V SR doplácate 0.00 €)*")
            st.subheader("📑 X. ODDIEL - Ostatné príjmy (§ 8)")
            if v['zisk_do_roka'] <= 0:
                st.info(f"V roku {r} ste utrpeli stratu ({v['zisk_do_roka']:.2f} EUR). Netreba nič vypĺňať.")
            else:
                if (priznany_zisk_po_oslobodeni == 0):
                    st.info(f"Zisk {v['zisk_do_roka']:.2f} EUR nepresiahol oslobodený limit 500 EUR. Netreba zdaňovať.")
                else:
                    pomer = priznany_zisk_po_oslobodeni / v['zisk_do_roka']
                    st.write(f"**Riadok 5 (Stĺpec 1 - Príjmy):** `{v['prijmy_kratkodobe']*pomer:.2f} EUR`")
                    st.write(f"**Riadok 5 (Stĺpec 2 - Výdavky):** `{v['vydavky_kratkodobe']*pomer:.2f} EUR`")
                    st.write(f"**Zdravotné odvody (14%):** `{realne_odvody_akcie:.2f} EUR`")

    # =========================================================================
    # KROK 2: DAŇOVÝ OPTIMALIZÁTOR S CELÝMI NÁZVAMI A VYSVETLIVKAMI (SEKCIA 2)
    # =========================================================================
    st.markdown("##")
    st.markdown("---")
    st.header("🔍 Daňový Optimalizátor pre dnešný predaj")
