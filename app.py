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
    
    # Vyčistíme a zjednotíme stĺpec Ticker
    df['Ticker_Clean'] = df['Ticker'].fillna('').astype(str).str.replace("US ", "").str.replace("_US", "").str.replace("_US_EQ", "").str.replace("_EQ", "").str.replace(".US", "").str.strip().str.replace("_", "").str.replace(".", "").str.replace(" ", "").str.upper()
    
    # Vytiahneme iba zoznam tickerov, ktoré prešli nákupom
    df_nakupov_vsetky = df[df['Action'].str.lower().str.contains('buy|investment|deposit', na=False)]
    zoznam_tickerov = sorted(list(df_nakupov_vsetky['Ticker_Clean'].unique()))
    
    if not zoznam_tickerov:
        st.info("V nahratých súboroch sa nenachádzajú žiadne nákupné transakcie.")
    else:
        vybrany_ticker = st.selectbox("Vyberte akciu zo svojho portfólia, ktorú plánujete predať:", zoznam_tickerov)
        
        skutocny_stav = st.number_input(f"Zadajte presný počet kusov pre {vybrany_ticker}, ktorý momentálne vidíte na platforme:", min_value=0.0, value=0.0, step=0.00001, format="%.5f")
        
        if skutocny_stav > 0:
            # Vytiahneme nákupy iba pre túto konkrétnu vybranú akciu
            df_filtracia = df_nakupov_vsetky[df_nakupov_vsetky['Ticker_Clean'] == vybrany_ticker].copy()
            df_filtracia = df_filtracia.sort_values(by='Time').reset_index(drop=True)
            
            potrebne_ks = skutocny_stav
            dnes = datetime.now()
            ks_bez_dane = 0.0
            ks_mlade = 0.0
            
            list_dat_nakupu = []
            list_mnozstiev = []
            list_stavov = []
            list_dat_oslobodenia = []
            list_cakania = []
            
            # Naplníme balíčky chronologicky od najstarších (Pravidlo FIFO)
            for _, r_nakup in df_filtracia.iterrows():
                if potrebne_ks <= 1e-6:
                    break
                
                sh_c = float(r_nakup['No. of shares']) if pd.notna(r_nakup['No. of shares']) else 0.0
                if sh_c > 0:
                    vziat_ks = min(sh_c, potrebne_ks)
                    potrebne_ks -= vziat_ks
                    
                    nakup_pure = pd.to_datetime(r_nakup['Time']).to_pydatetime()
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
            st.info("💡 **Ako čítať tabuľku:** Platforma Trading 212 predáva akcie chronologicky od najstarších (pravidlo FIFO). Sledujte zelené riadky – tie predáte bezpečne bez odovzdania eura štátu.")
        else:
            st.info("Pre zobrazenie daňového breakdownu zadajte do políčka vyššie množstvo väčšie ako 0.")
