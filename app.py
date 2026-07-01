import streamlit as st
import pandas as pd
import io
from datetime import datetime

st.set_page_config(page_title="Trading 212 Daňová Kalkulačka", page_icon="📈", layout="wide")

st.title("📈 Súkromný Daňový Asistent a Optimalizátor pre Trading 212 (SR)")
st.write("Nahrajte svoje CSV exporty z Trading 212 a získajte ročný daňový manuál + checker pre safe predaj akcií.")

uploaded_files = st.file_uploader("Sem presuňte vaše CSV súbory (môžete aj viac naraz)", type=["csv"], accept_multiple_files=True)

if uploaded_files:
    zoznam_df = []
    for file in uploaded_files:
        zoznam_df.append(pd.read_csv(file))
        
    df = pd.concat(zoznam_df, ignore_index=True)
    df['Time'] = pd.to_datetime(df['Time'], errors='coerce').dt.tz_localize(None)
    df = df.dropna(subset=['Time']).sort_values(by='Time').reset_index(drop=True)
    
    sklad = {}
    vysledky_po_rokoch = {}
    databaza_mien = {}
    
    # 1. KROK: BEZPEČNÁ HISTORICKÁ FIFO MATEMATIKA (BEZ RIZIKA ZACYKLENIA)
    for _, riadok in df.iterrows():
        typ = str(riadok['Action']).lower()
        ticker_surovy = str(riadok['Ticker'])
        full_name = str(riadok.get('Name', 'Neznáma spoločnosť')).strip()
        
        ticker = ticker_surovy.replace("US ", "").replace("_US", "").strip()
        
        if pd.notna(riadok.get('Name')) and ticker != 'nan' and ticker:
            if ticker not in databaza_mien or len(full_name) > len(databaza_mien[ticker]):
                databaza_mien[ticker] = full_name
        
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
            if ticker not in sklad: sklad[ticker] = []
            sklad[ticker].append({'shares': shares, 'date': datum, 'cena_za_kus': total/shares if shares > 0 else 0.0})
            
        elif 'sell' in typ or 'divestment' in typ or 'withdrawal' in typ or 'rebalancing' in typ or shares < 0:
            predat_este = abs(shares)
            riadok_po_roku = 0.0
            riadok_do_roka = 0.0
            riadok_vydavok = 0.0
            
            if ticker in sklad and sklad[ticker]:
                temp_sklad = list(sklad[ticker])
                sklad[ticker] = []
                
                for najstarsie in temp_sklad:
                    if predat_este <= 0:
                        sklad[ticker].append(najstarsie)
                        continue
                        
                    vek = datum - najstarsie['date']
                    splnil_rok = vek.days >= 365
                    
                    if najstarsie['shares'] <= predat_este:
                        pomer = najstarsie['shares'] / abs(shares)
                        if splnil_rok: riadok_po_roku += (result * pomer)
                        else:
                            riadok_do_roka += (result * pomer)
                            riadok_vydavok += (najstarsie['shares'] * najstarsie['cena_za_kus'])
                        predat_este -= najstarsie['shares']
                    else:
                        pomer = predat_este / abs(shares)
                        if splnil_rok: riadok_po_roku += (result * pomer)
                        else:
                            riadok_do_roka += (result * pomer)
                            riadok_vydavok += (predat_este * najstarsie['cena_za_kus'])
                        
                        zostatok_shares = najstarsie['shares'] - predat_este
                        sklad[ticker].append({'shares': zostatok_shares, 'date': najstarsie['date'], 'cena_za_kus': najstarsie['cena_za_kus']})
                        predat_este = 0.0
                        
            vysledky_po_rokoch[rok]['zisk_do_roka'] += riadok_do_roka
            vysledky_po_rokoch[rok]['zisk_po_roku'] += riadok_po_roku
            if riadok_do_roka != 0:
                vysledky_po_rokoch[rok]['prijmy_kratkodobe'] += total
                vysledky_po_rokoch[rok]['vydavky_kratkodobe'] += riadok_vydavok

    st.success("🚀 Analýza úspešne dokončená!")
    
    # ROČNÉ PREHĽADY
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
            col1.metric("Celková daňová povinnosť", f"{celkovo:.2f} EUR", 
                        help="Celková suma dane z úrokov a krátkodobých ziskov nad limit 500€ + zdravotné odvody. Toto musíte zaplatiť štátu.")
            col2.metric("Dlhodobý zisk (BEZ DANE)", f"{v['zisk_po_roku']:.2f} EUR", 
                        help="Zisk z akcií, ktoré ste držali dlhšie ako 1 rok. Tieto peniaze sú kompletne oslobodené od dane.")
            st.markdown("---")
            st.subheader("📑 VIII. ODDIEL - Kapitálový majetok")
            st.write(f"**Riadok 2 (Úroky z vkladov):** Príjmy: `{v['uroky']:.2f} EUR` | Daň: `{realna_dan_uroky:.2f} EUR`")
            st.subheader("📑 PRÍLOHA č. 2 - Dividendy")
            st.write(f"**Riadok 1:** Príjem Brutto: `{v['div_brutto']:.2f} EUR` | Daň zaplatená v zahraničí: `{v['div_dan']:.2f} EUR` *(V SR doplácate 0.00 €)*")
            st.subheader("📑 X. ODDIEL - Ostatné príjmy (§ 8)")
            if v['zisk_do_roka'] <= 0:
                st.info(f"Utrpeli ste stratu ({v['zisk_do_roka']:.2f} EUR). Netreba nič vypĺňať.")
            else:
                if prepocet_ok := (priznany_zisk_po_oslobodeni == 0):
                    st.info(f"Zisk {v['zisk_do_roka']:.2f} EUR nepresiahol 500 EUR. Je oslobodený.")
                else:
                    pomer = priznany_zisk_po_oslobodeni / v['zisk_do_roka']
                    st.write(f"**Riadok 5 (Stĺpec 1 - Príjmy):** `{v['prijmy_kratkodobe']*pomer:.2f} EUR`")
                    st.write(f"**Riadok 5 (Stĺpec 2 - Výdavky):** `{v['vydavky_kratkodobe']*pomer:.2f} EUR`")
                    st.write(f"**Zdravotné odvody (14%):** `{realne_odvody_akcie:.2f} EUR`")

    # =========================================================================
    # 🔥 2. KROK: PLOCHÝ OPTIMALIZÁTOR - BEZ NEBEZPEČNÝCH MEDZIER A SLUČIEK
    # =========================================================================
    st.markdown("##")
    st.header("🔍 Daňový Optimalizátor pre dnešný predaj")
    st.write("Aplikácia analyzovala históriu nákupov. Pre zaručenie 100% presnosti zadajte váš aktuálny otvorený stav z platformy Trading 212.")
    
    vsetky_tickery = sorted(list(sklad.keys()))
    
    if vsetky_tickery:
        ponuka_pre_menu = []
        mapovanie = {}
        for t in vsetky_tickery:
            text_polozky = f"{t} - {databaza_mien.get(t, 'Spoločnosť z CSV')}"
            ponuka_pre_menu.append(text_polozky)
            mapovanie[text_polozky] = t
            
        vybrany_text = st.selectbox("Vyberte akciu zo svojho portfólia, ktorú plánujete predať:", ponuka_pre_menu)
        vybrany_ticker = mapovanie[vybrany_text]
        
        skutocny_stav_mobil = st.number_input(f"Zadajte presný počet kusov {vybrany_ticker}, ktorý momentálne SKUTOČNE vidíte v platforme Trading 212:", min_value=0.0, value=0.0, step=0.00001, format="%.5f", key="definitivny_vstup_t212_vFINAL_DVE")
        
        if skutocny_stav_mobil > 0:
            nákupy_vsetky = sklad.get(vybrany_ticker, [])
            
            if not nákupy_vsetky:
                st.info("V histórii nákupov pre tento ticker neboli nájdené žiadne otvorené balíčky.")
            else:
                nákupy_vsetky = sorted(nákupy_vsetky, key=lambda x: x['date'])
                nákupy_skutocne = []
                potrebne_ks = skutocny_stav_mobil
                
                for n in nákupy_vsetky:
                    if potrebne_ks <= 0:
                        break
                    vziat_ks = min(n['shares'], potrebne_ks)
                    nákupy_skutocne.append({'shares': vziat_ks, 'date': n['date']})
                    potrebne_ks -= vziat_ks
                
                dnes = datetime.now()
                ks_bez_dane = 0.0
                ks_mlade = 0.0
                list_dat_nakupu = []
                list_mnozstiev = []
                list_stavov = []
                list_dat_oslobodenia = []
                list_cakania = []
                
                for n in nákupy_skutocne:
                    nakup_pure = pd.to_datetime(n['date']).to_pydatetime() if hasattr(n['date'], 'to_pydatetime') else n['date']
