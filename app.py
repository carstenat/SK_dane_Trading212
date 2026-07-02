    # === POKRAČOVANIE VÁŠHO KÓDU (Doplnenie useknutej časti) ===
    zoznam_tickerov_vsetky = sorted([t for t in df['Ticker_Clean'].unique() if t and t != 'NAN'])
    
    realizovane_obchody_rok = []
    otvorene_loty_portfólio = dict()

    # Prechádzame celú históriu kvôli správnemu FIFO párovaniu
    for t in zoznam_tickerov_vsetky:
        df_t = df[df['Ticker_Clean'] == t].copy()
        
        # Fronta nákupných lotov (FIFO)
        nakupne_loty = []
        
        for _, row in df_t.iterrows():
            akcia = str(row['Action']).lower()
            množstvo = float(row['No. of shares'])
            total_val = float(row['Total'])
            
            # Výpočet ceny za kus, ak v CSV chýba explicitný stĺpec
            cena_ks = (total_val / množstvo) if informed_shares := (množstvo > 0) else 0.0
            
            # 1. Spracovanie NÁKUPU (BUY) alebo prichádzajúcich akcií
            if 'buy' in akcia or 'market buy' in akcia:
                lot = dict()
                lot['množstvo'] = množstvo
                lot['cena_nakup'] = cena_ks
                lot['datum_nakup'] = row['Time']
                nakupne_loty.append(lot)
                
            # 2. Spracovanie PREDAJA (SELL) pomocou FIFO
            elif 'sell' in akcia or 'market sell' in akcia:
                množstvo_na_predaj = množstvo
                
                while množstvo_na_predaj > 0 and len(nakupne_loty) > 0:
                    aktualny_lot = nakupne_loty[0]
                    
                    if aktualny_lot['množstvo'] <= množstvo_na_predaj:
                        # Spotrebujeme celú šaržu
                        odpredane_množstvo = aktualny_lot['množstvo']
                        množstvo_na_predaj -= odpredane_množstvo
                        nakupne_loty.pop(0)
                    else:
                        # Spotrebujeme len časť šarže
                        odpredane_množstvo = množstvo_na_predaj
                        aktualny_lot['množstvo'] -= odpredane_množstvo
                        množstvo_na_predaj = 0
                        
                    prijem = odpredane_množstvo * cena_ks
                    vydaj = odpredane_množstvo * aktualny_lot['cena_nakup']
                    zisk_z_predaja = prijem - vydaj
                    
                    # Kontrola 1-ročného časového testu v SR
                    dni_drzania = (row['Time'] - aktualny_lot['datum_nakup']).days
                    oslobodene = dni_drzania >= 365
                    
                    # Ak predaj patrí do vybraného roku, zapíšeme ho do reportu
                    if st.session_state.vybrany_rok == "Všetky" or row['Rok'] == int(st.session_state.vybrany_rok):
                        obchod = dict()
                        obchod['Ticker'] = t
                        obchod['Spoločnosť'] = databaza_mien.get(t, "Neznáma")
                        obchod['Kusy'] = odpredane_množstvo
                        obchod['Zisk/Strata'] = zisk_z_predaja
                        obchod['Oslobodené'] = "Áno (Časový test)" if oslobodene else "Nie (Podlieha dani)"
                        obchod['Zdaniteľný Zisk'] = 0.0 if oslobodene else zisk_z_predaja
                        realizovane_obchody_rok.append(obchod)
                        
        # Zostávajúce loty uložíme ako otvorené pozície k dnešnému dňu
        otvorene_loty_portfólio[t] = [lot for lot in nakupne_loty if lot['množstvo'] > 0.000001]

    # Vykreslenie globálneho FIFO daňového reportu
    if len(realizovane_obchody_rok) == 0:
        st.info(f"ℹ️ V daňovom období '{st.session_state.vybrany_rok}' ste nerealizovali žiadne predaje (SELL). Daňový základ z predaja cenných papierov je nulový.")
        zdanitelny_zisk_celkom = 0.0
    else:
        df_realizovane = pd.DataFrame(realizovane_obchody_rok)
        st.dataframe(df_realizovane, use_container_width=True)
        
        # Sčítame iba obchody, ktoré nesplnili časový test a skončili v zisku
        zdanitelny_zisk_celkom = df_realizovane['Zdaniteľný Zisk'].sum()
        zdanitelny_zisk_celkom = max(0.0, zdanitelny_zisk_celkom)

    # Výpočet daní a odvodov podliehajúcich novelizácii SR pre rok 2026
    odhadovana_dan = zdanitelny_zisk_celkom * 0.19
    odhadovane_odvody = zdanitelny_zisk_celkom * 0.15  # Zvýšená sadzba zo 14% na 15% v SR

    col_m1, col_m2, col_m3 = st.columns(3)
    with col_m1:
        st.metric("Krátkodobý zdaniteľný zisk", f"{zdanitelny_zisk_celkom:,.2f} EUR")
    with col_m2:
        st.metric("Daň z príjmu FO (19%)", f"{odhadovana_dan:,.2f} EUR")
    with col_m3:
        st.metric("Zdravotné odvody (15%)", f"{odhadovane_odvody:,.2f} EUR")

    # =========================================================================
    # 🎯 POKROČILÝ FIFO OPTIMALIZÁTOR LOTOV (PRE VYBRANÝ TITUL)
    # =========================================================================
    st.markdown("---")
    st.header("🎯 Pokročilý FIFO Optimalizátor otvorených šarží")
    st.write("Tu uvidíte detailný rozpad nákupných šarží (lotov) pre konkrétnu akciu a zostávajúce dni do oslobodenia.")

    # Filtrujeme iba tituly, ktoré majú reálne otvorené pozície
    zoznam_otvorenych_tickerov = sorted([t for t, loty in otvorene_loty_portfólio.items() if len(loty) > 0])

    if len(zoznam_otvorenych_tickerov) > 0:
        # Generovanie položiek pre vyhľadávanie v selectboxe
        polozky_pre_select = []
        for t in zoznam_otvorenych_tickerov:
            nazov_firmy = databaza_mien.get(t, "Neznámy názov")
            polozky_pre_select.append(dict(ticker=t, nazov=nazov_firmy, zobrazenie=f"{t} — {nazov_firmy}"))
            
        # Zoradenie zoznamu podľa vybratej rádiového tlačidla v sidebare (Bezpečná flat úprava)
        if metoda_zoradenia == "Tickeru abecedne":
            polozky_pre_select = sorted(polozky_pre_select, key=lambda x: x['ticker'].lower())
        else:
            polozky_pre_select = sorted(polozky_pre_select, key=lambda x: x['nazov'].lower())

        list_zobrazeni = [p['zobrazenie'] for p in polozky_pre_select]
        
        # Filtrovanie písaním priamo v natívnom Streamlit selectboxe
        vybrany_titul_full = st.selectbox("Vyhľadajte alebo vyberte akciu pre kontrolu šarží:", list_zobrazeni)
        
        # Získanie prislúchajúceho tickeru
        vybrany_ticker = [p['ticker'] for p in polozky_pre_select if p['zobrazenie'] == vybrany_titul_full][0]
        
        sarze_akcie = otvorene_loty_portfólio[vybrany_ticker]
        dnesny_datum = datetime.now()
        
        zaznamy_sarzi_ui = []
        potencialne_danove_riziko_celkom = 0.0
        
        for index, sarza in enumerate(sarze_akcie):
            dni_drzania = (dnesny_datum - pd.to_datetime(sarza['datum_nakup'])).days
            casovany_test_splneny = dni_drzania >= 365
            dni_do_konca = max(0, 365 - dni_drzania)
            
            # Simulácia 10% zisku na šaržu pre potreby núdzového indikátora rizika
            simulovany_zisk = (sarza['množstvo'] * sarza['cena_nakup']) * 0.10
            danove_riziko_sarze = simulovany_zisk * (0.19 + 0.15) if not casovany_test_splneny else 0.0
            
            if not casovany_test_splneny:
                potencialne_danove_riziko_celkom += danove_riziko_sarze
                status_text = f"🔴 Zdaniteľná šarža (Čakať ešte {dni_do_konca} dní)"
            else:
                status_text = "🟢 OSME_OSLOBODENÉ (Časový test OK)"

            zaznamy_sarzi_ui.append({
                "Šarža": f"Šarža #{index + 1}",
                "Dátum nákupu": pd.to_datetime(sarza['datum_nakup']).strftime('%Y-%m-%d'),
                "Držané množstvo (Kusy)": round(sarza['množstvo'], 5),
                "Nákupná cena": f"{sarza['cena_nakup']:.4f} EUR",
                "Dni držania": dni_drzania,
                "Status / Časový test": status_text,
                "Modelové daňové riziko": f"{danove_riziko_sarze:.2f} EUR" if danove_riziko_sarze > 0 else "0.00 EUR"
            })
            
        st.subheader(f"📋 Rozpad otvorených frakcií pre {vybrany_ticker}")
        st.table(pd.DataFrame(zaznamy_sarzi_ui))
        
        # SIMULÁTOR NÚDZOVÉHO PREDAJA (Emergency Liquidation)
        st.subheader("🚨 Indikátor Emergency Likvidácie")
        if potencialne_danove_riziko_celkom > 0:
            st.error(f"⚠️ POZOR: Ak by ste dnes celú pozíciu {vybrany_ticker} núdzovo predali, prídete na zbytočných daniach a odvodoch v SR o približne: {potencialne_danove_riziko_celkom:,.2f} EUR (počítané pri modelovom raste trhu o 10%).")
        else:
            st.success(f"✅ Všetky otvorené pozície na titule {vybrany_ticker} úspešne prekonali 1 rok. Môžete ich kedykoľvek predať so 100% oslobodením v SR.")
    else:
        st.info("V portfóliu nemáte aktuálne žiadne otvorené akcie.")
else:
    st.info("👋 Čakám na nahranie dát. Presuňte CSV súbory z Trading 212 do poľa vyššie.")
