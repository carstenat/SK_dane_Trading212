import streamlit as st
import pandas as pd
import io
from datetime import datetime

st.set_page_config(page_title="Trading 212 Daňová Kalkulačka", page_icon="📈", layout="wide")

st.title("📈 Súkromný Daňový Asistent a Optimalizátor pre Trading 212 (SR)")
st.write("Nahrajte svoje CSV exporty z Trading 212 a získajte ročný daňový manuál + checker pre bezpečný predaj akcií.")

uploaded_files = st.file_uploader("Sem presuňte vaše CSV súbory (môžete aj viac naraz)", type=["csv"], accept_multiple_files=True)

if uploaded_files:
    zoznam_df = []
    for file in uploaded_files:
        zoznam_df.append(pd.read_csv(file))
        
    df = pd.concat(zoznam_df, ignore_index=True)
    df['Time'] = pd.to_datetime(df['Time'])
    df = df.sort_values(by='Time').reset_index(drop=True)
    
    sklad = {}
    vysledky_po_rokoch = {}
    
    # FIFO logika pre historické ročné reporty
    for _, riadok in df.iterrows():
        typ = str(riadok['Action']).lower()
        ticker = str(riadok['Ticker'])
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
        if 'sell' in typ and abs(result) < 2.0 and total < 10.0:
            continue
            
        if 'buy' in typ:
            if ticker not in sklad: sklad[ticker] = []
            sklad[ticker].append({'shares': shares, 'date': datum, 'cena_za_kus': total/shares if shares > 0 else 0.0})
        elif 'sell' in typ and shares > 0:
            predat_este = shares
            riadok_po_roku = 0.0
            riadok_do_roka = 0.0
            riadok_vydavok = 0.0
            
            if ticker in sklad and sklad[ticker]:
                while predat_este > 0 and sklad[ticker]:
                    najstarsie = sklad[ticker][0]
                    vek = datum - najstarsie['date']
                    splnil_rok = vek.days >= 365
                    
                    if najstarsie['shares'] <= predat_este:
                        pomer = najstarsie['shares'] / shares
                        if splnil_rok: riadok_po_roku += (result * pomer)
                        else:
                            riadok_do_roka += (result * pomer)
                            riadok_vydavok += (najstarsie['shares'] * najstarsie['cena_za_kus'])
                        predat_este -= najstarsie['shares']
                        sklad[ticker].pop(0)
                    else:
                        pomer = predat_este / shares
                        if splnil_rok: riadok_po_roku += (result * pomer)
                        else:
                            riadok_do_roka += (result * pomer)
                            riadok_vydavok += (predat_este * najstarsie['cena_za_kus'])
                        najstarsie['shares'] -= predat_este
                        predat_este = 0.0
                        
            vysledky_po_rokoch[rok]['zisk_do_roka'] += riadok_do_roka
            vysledky_po_rokoch[rok]['zisk_po_roku'] += riadok_po_roku
            if riadok_do_roka != 0:
                vysledky_po_rokoch[rok]['prijmy_kratkodobe'] += total
                vysledky_po_rokoch[rok]['vydavky_kratkodobe'] += riadok_vydavok

    st.success("🚀 Analýza úspešne dokončená!")
    
    # ROČNÉ PREHĽADY
    roky_zoznam = sorted(list(vysledky_po_rokoch.keys()), reverse=True)
    tabs = st.tabs([f"📅 Rok {r}" for r in roky_zoznam])
    
    for index, r in enumerate(roky_zoznam):
        v = vysledky_po_rokoch[r]
        oslobodeny_zisk = max(0.0, v['zisk_do_roka'])
        priznany_zisk_po_oslobodeni = max(0.0, oslobodeny_zisk - 500.0) if oslobodeny_zisk > 0 else 0.0
        
        realna_dan_uroky = round(v['uroky'] * 0.19, 2)
        realna_dan_akcie = round(priznany_zisk_po_oslobodeni * 0.19, 2)
        realne_odvody_akcie = round(priznany_zisk_po_oslobodeni * 0.14, 2)
        celkovo = realna_dan_uroky + realna_dan_akcie + realne_odvody_akcie
        
        with tabs[index]:
            col1, col2 = st.columns(2)
            col1.metric("Celková daňová povinnosť", f"{celkovo:.2f} EUR")
            col2.metric("Dlhodobý zisk (BEZ DANE)", f"{v['zisk_po_roku']:.2f} EUR")
            st.markdown("---")
            st.subheader("📑 VIII. ODDIEL - Kapitálový majetok")
            st.write(f"**Riadok 2 (Úroky z vkladov):** Príjmy: `{v['uroky']:.2f} EUR` | Daň: `{realna_dan_uroky:.2f} EUR`")
            st.subheader("📑 PRÍLOHA č. 2 - Dividendy")
            st.write(f"**Riadok 1:** Príjem Brutto: `{v['div_brutto']:.2f} EUR` | Daň zaplatená v zahraničí: `{v['div_dan']:.2f} EUR` *(V SR doplácate 0.00 €)*")
            st.subheader("📑 X. ODDIEL - Ostatné príjmy (§ 8)")
            if v['zisk_do_roka'] <= 0:
                st.info(f"Utrpeli ste stratu ({v['zisk_do_roka']:.2f} EUR). Netreba nič vypĺňať.")
            else:
                if priznany_zisk_po_oslobodeni == 0:
                    st.info(f"Zisk {v['zisk_do_roka']:.2f} EUR nepresiahol 500 EUR. Je oslobodený.")
                else:
                    pomer = priznany_zisk_po_oslobodeni / v['zisk_do_roka']
                    st.write(f"**Riadok 5 (Stĺpec 1 - Príjmy):** `{v['prijmy_kratkodobe']*pomer:.2f} EUR`")
                    st.write(f"**Riadok 5 (Stĺpec 2 - Výdavky):** `{v['vydavky_kratkodobe']*pomer:.2f} EUR`")
                    st.write(f"**Zdravotné odvody (14%):** `{realne_odvody_akcie:.2f} EUR`")

    # =========================================================================
    # 🔥 OPRAVENÝ OPTIMALIZÁTOR PRE DNEŠNÝ PREDAJ (Zohľadňuje minulé predaje)
    # =========================================================================
    st.markdown("##")
    st.header("🔍 Daňový Optimalizátor pre dnešný predaj")
    st.write(f"Aplikácia analyzovala váš skutočný aktuálny otvorený sklad k dnešnému dňu (**{datetime.now().strftime('%d.%m.%Y')}**).")
    
    # Vyberieme len tie tickery, ktorých reálny konečný zostatok je väčší ako nula
    aktivne_tickery = sorted([t for t in sklad.keys() if len(sklad[t]) > 0 and sum(n['shares'] for n in sklad[t]) > 0.00001])
    
    if aktivne_tickery:
        vybrany_ticker = st.selectbox("Vyberte alebo napíšte skratku akcie (Ticker) na kontrolu:", aktivne_tickery)
        
        if vybrany_ticker:
            st.subheader(f"📊 Analýza pozície pre {vybrany_ticker}")
            nákupy = sklad[vybrany_ticker]
            
            celkovo_vlastnene = sum(n['shares'] for n in nákupy)
            st.write(f"Aktuálne reálne vlastníte: **{celkovo_vlastnene:.5f} ks** tejto akcie.")
            
            dnes = datetime.now()
            ks_bez_dane = 0.0
            ks_mlade = 0.0
            podrobnosti_mlade = []
            
            for n in nákupy:
                vek_dni = (dnes - n['date']).days
                if vek_dni >= 365:
                    ks_bez_dane += n['shares']
                else:
                    ks_mlade += n['shares']
                    dni_do_roka = 365 - vek_dni
                    podrobnosti_mlade.append({
                        'shares': n['shares'],
                        'date': n['date'].strftime('%d.%m.%Y'),
                        'dni_cakat': dni_do_roka
                    })
            
            c1, c2 = st.columns(2)
            c1.success(f"🔓 Môžete predať IHNEĎ BEZ DANE:\n**{ks_bez_dane:.5f} ks**")
            c2.warning(f"🔒 MLADÉ FRAKCIE (Zdaňujú sa pri predaji dnes):\n**{ks_mlade:.5f} ks**")
            
            if ks_mlade > 0:
                st.markdown("### 📅 Kedy predáte zvyšok bez dane?")
                st.write("Tu je prehľad balíčkov, ktoré ešte musíte podržať:")
                for pm in podrobnosti_mlade:
                    st.write(f"• Fragment o veľkosti **{pm['shares']:.5f} ks** (nakúpený {pm['date']}) bude oslobodený o **{pm['dni_cakat']} dní**.")
    else:
        st.info("Vo vašej histórii momentálne nezostali žiadne otvorené pozície akcií (všetko je predané).")
