import streamlit as st
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Trading 212 Optimalizátor", page_icon="📈", layout="wide")

st.title("📈 Súkromný Optimalizátor pre Trading 212 (SR)")
st.write("Tento nástroj slúži výhradne na kontrolu časového testu (1 rok) pred plánovaným predajom akcií.")

uploaded_files = st.file_uploader("Nahrajte vaše CSV súbory z Trading 212:", type=["csv"], accept_multiple_files=True)

if uploaded_files:
    zoznam_df = []
    for file in uploaded_files:
        zoznam_df.append(pd.read_csv(file))
        
    df = pd.concat(zoznam_df, ignore_index=True)
    df['Time'] = pd.to_datetime(df['Time'], errors='coerce').dt.tz_localize(None)
    df = df.dropna(subset=['Time']).sort_values(by='Time').reset_index(drop=True)
    
    # Zjednotenie textu tickerov
    df['Ticker_Clean'] = df['Ticker'].fillna('').astype(str).str.replace("US ", "").str.replace("_US", "").str.replace("_US_EQ", "").str.replace("_EQ", "").str.replace(".US", "").str.strip().str.replace("_", "").str.replace(".", "").str.replace(" ", "").str.upper()
    
    # Filtrujeme iba transakcie, ktoré menia stav skladu (Buy a Sell)
    df_akcie = df[df['Action'].str.lower().str.contains('buy|investment|deposit|sell|divestment|withdrawal|rebalancing', na=False)].copy()
    zoznam_tickerov = sorted(list(df_akcie['Ticker_Clean'].unique()))
    
    if not zoznam_tickerov:
        st.info("V nahratých súboroch sa nenachádzajú žiadne transakcie akcií.")
    else:
        vybrany_ticker = st.selectbox("Vyberte akciu zo svojho portfólia, ktorú plánujete predať:", zoznam_tickerov)
        
        skutocny_stav = st.number_input(f"Zadajte presný počet kusov pre {vybrany_ticker}, ktorý momentálne reálne vidíte na platforme:", min_value=0.0, value=0.0, step=0.00001, format="%.5f", key="vstup_autenticky_fifo_fix")
        
        # 1. REKONŠTRUKCIA SKUTREČNÉHO SKLADU POMOCOU HISTORICKÉHO FIFO
        df_ticker = df_akcie[df_akcie['Ticker_Clean'] == vybrany_ticker].copy()
        df_ticker = df_ticker.sort_values(by='Time').reset_index(drop=True)
        
        sklad_aktualny = []
        
        for _, riadok in df_ticker.iterrows():
            typ = str(riadok['Action']).lower()
            shares = float(riadok['No. of shares']) if pd.notna(riadok['No. of shares']) else 0.0
            datum = riadok['Time']
            
            if 'buy' in typ or 'investment' in typ or 'deposit' in typ:
                if shares > 0:
                    sklad_aktualny.append({'shares': shares, 'date': datum})
            elif 'sell' in typ or 'divestment' in typ or 'withdrawal' in typ or 'rebalancing' in typ or shares < 0:
                predat_este = abs(shares)
                
                # Odpočítame predané kusy z najstarších nákupov (FIFO)
                temp_sklad = []
                for balicek in sklad_aktualny:
                    if predat_este <= 1e-6:
                        temp_sklad.append(balicek)
                    else:
                        if balicek['shares'] <= predat_este:
                            predat_este -= balicek['shares']
                        else:
                            balicek['shares'] -= predat_este
                            predat_este = 0.0
                            temp_sklad.append(balicek)
                sklad_aktualny = temp_sklad
        
        # 2. KROK: PREPOČET PRE ZADANÉ MNOŽSTVO NA ZÁKLADE REÁLNEHO ZOSTATKU
        if skutocny_stav > 0:
            potrebne_ks = skutocny_stav
            dnes = datetime.now()
            ks_bez_dane = 0.0
            ks_mlade = 0.0
            
            list_dat_nakupu = []
            list_mnozstiev = []
            list_stavov = []
            list_dat_oslobodenia = []
            list_cakania = []
            
            # Prechádzame iba tie nákupné balíčky, ktoré reálne prežili minulé predaje
            for n in sklad_aktualny:
                if potrebne_ks <= 1e-6:
                    break
                
                vziat_ks = min(n['shares'], potrebne_ks)
                potrebne_ks -= vziat_ks
                
                nakup_pure = pd.to_datetime(n['date']).to_pydatetime()
                vek_dni = (dnes.date() - nakup_pure.date()).days
                
                list_dat_nakupu.append(nakup_pure.strftime('%d.%m.%Y'))
                list_mnozstiev.append(f"{vziat_ks:.5f}")
                
                if vek_dni >= 365:
                    ks_bez_dane += vziat_ks
                    list_stavov.append("🟢 Bez dane (Nad 1 rok)")
                    list_dat_oslobodenia.append("Už oslobodené")
                    list_cakania.append("0 dní")
                else:
                    ks_mlade += vziat_ks
                    list_stavov.append("🔴 Zdaňuje sa (Mladá akcia)")
                    list_dat_oslobodenia.append((nakup_pure + pd.Timedelta(days=365)).strftime('%d.%m.%Y'))
                    list_cakania.append(f"⏳ {365 - vek_dni} dní")
            
            st.markdown("---")
            c1, c2 = st.columns(2)
            c1.success(f"🔓 Môžete predať IHNEĎ BEZ DANE:\n**{ks_bez_dane:.5f} ks**")
            c2.warning(f"🔒 MLADÉ FRAKCIE (Zdaňujú sa pri predaji dnes):\n**{ks_mlade:.5f} ks**")
            
            st.markdown("### 📋 Detailný rozpis balíčkov na vašom sklade:")
            tovarna_tabulky = pd.DataFrame({
                "Dátum nákupu": list_dat_nakupu,
                "Množstvo (ks)": list_mnozstiev,
                "Daňový stav": list_stavov,
                "Dátum oslobodenia": list_dat_oslobodenia,
                "Zostáva čakať": list_cakania
            })
            st.dataframe(tovarna_tabulky, use_container_width=True, hide_index=True)
            st.info("💡 **Ako čítať tabuľku:** Platforma Trading 212 predáva akcie chronologicky od najstarších (pravidlo FIFO).")
        else:
            st.info("Pre zobrazenie daňového breakdownu zadajte do políčka vyššie množstvo väčšie ako 0.")

