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

    # 📅 TRI ROČNÉ ZÁLOŽKY - PEVNÁ, RUČNÁ ŠTUKTÚRA BEZ RISKANTNÝCH CYKLOV
    tab2024, tab2025, tab2026 = st.tabs(["📅 Daňový rok 2024", "📅 Daňový rok 2025", "📅 Daňový rok 2026"])
    
    # =========================================================================
    # 📑 SEKCIA 1: DAŇOVÝ ROK 2024
    # =========================================================================
    with tab2024:
        st.header("Optimalizátor a podklady pre rok 2024")
        df_akcie_2024 = df_global[(df_global['Action'].str.lower().str.contains('buy|sell|nákup|nakup|predaj|market|limit', na=False)) & (df_global['Rok'] <= 2024)].copy()
        tickerov_2024 = sorted([x for x in df_akcie_2024['Ticker_Clean'].unique() if x and x != 'nan' and x != ''])
        
        if tickerov_2024:
            ponuka_2024 = [f"{t} - {databaza_mien.get(t, 'Spoločnosť')}" for t in tickerov_2024]
            vybrany_text_2024 = st.selectbox("Vyberte akciu zo svojho portfólia (2024):", ponuka_2024, key="sel_2024")
            ticker_pure_2024 = vybrany_text_2024.split(" - ")[0]
            
            c1_24, c2_24 = st.columns(2)
            with c1_24:
                vlastnene_24 = st.number_input("Počet kusov vlastnených na platforme (2024):", min_value=0.0, value=0.0, step=0.00001, format="%.5f", key="v_2024")
            with c2_24:
                cena_24 = st.number_input("Aktuálna trhová cena v EUR (2024):", min_value=0.0, value=0.0, step=0.01, format="%.2f", key="c_2024")
                
            df_ticker_24 = df_akcie_2024[df_akcie_2024['Ticker_Clean'] == ticker_pure_2024].sort_values(by='Time').reset_index(drop=True)
            sklad_24 = []
            for _, r in df_ticker_24.iterrows():
                typ = str(r['Action']).lower()
                shares = float(r['No. of shares'])
                total = float(r['Total'])
                if 'buy' in typ or 'nákup' in typ or 'nakup' in typ:
                    if shares > 0.00001: sklad_24.append({'shares': shares, 'date': r['Time'], 'cena_za_kus': total/shares})
                elif 'sell' in typ or 'predaj' in typ or shares < 0:
                    pe = abs(shares)
                    for b in sklad_24:
                        if pe > 1e-6 and b['shares'] > 0:
                            v = min(b['shares'], pe)
                            b['shares'] -= v
                            pe -= v
                    sklad_24 = [x for x in sklad_24 if x['shares'] > 1e-6]
                    
            max_24 = sum([x['shares'] for x in sklad_24])
            stav_24 = min(vlastnene_24, max_24)
            if vlastnene_24 > max_24: st.error(f"⚠️ Maximálny dostupný sklad pre rok 2024 je {max_24:.5f} ks.")
            
            p_ks_24 = stav_24
            dnes = datetime.now()
            sb_24, mb_24, v_sb_24, v_mb_24 = 0.0, 0.0, 0.0, 0.0
            txt_24, csv_24 = [], [["Datum nakupu", "Mnozstvo (ks)", "Nakupna cena/ks", "Celkovy nakup", "Danovy stav", "Datum oslobodenia", "Zostava cakat"]]
            
            for n in sklad_24:
                if p_ks_24 < 1e-5: break
                vk = min(n['shares'], p_ks_24)
                p_ks_24 -= vk
                vek = (dnes.date() - pd.to_datetime(n['date']).date()).days
                cb = vk * n['cena_za_kus']
                dn = pd.to_datetime(n['date']).strftime('%d.%m.%Y')
                
                if vek >= 365:
                    sb_24 += vk
                    v_sb_24 += cb
                    txt_24.append(f"🟢 **BEZ DANE** | Nákup: {dn} | Množstvo: {vk:.5f} ks pri cene {n['cena_za_kus']:.2f} EUR (Spolu: {cb:.2f} EUR) | ⏳ Oslobodené")
                    csv_24.append([dn, f"{vk:.5f}", f"{n['cena_za_kus']:.2f}", f"{cb:.2f}", "Bez dane", "Uz oslobodene", "0 dni"])
                else:
                    mb_24 += vk
                    v_mb_24 += cb
                    do = (pd.to_datetime(n['date']) + pd.Timedelta(days=365)).strftime('%d.%m.%Y')
                    txt_24.append(f"🔴 **ZDAŇUJE SA** | Nákup: {dn} | Množstvo: {vk:.5f} ks pri cene {n['cena_za_kus']:.2f} EUR (Spolu: {cb:.2f} EUR) | ⏳ Čakať: {365-vek} dní (Oslobodenie: {do})")
                    csv_24.append([dn, f"{vk:.5f}", f"{n['cena_za_kus']:.2f}", f"{cb:.2f}", "Zdanuje sa", do, f"{365-vek} dni"])
                    
            if stav_24 > 0:
                st.markdown(f"**Vizuálny pomer safe pozície:** {sb_24:.5f} ks z {stav_24:.5f} ks")
                st.progress(max(0.0, min(1.0, float(sb_24 / stav_24))))
                
                if cena_24 > 0:
                    st.success(f"🔓 Predaj bez dane ihneď v 2024: **{sb_24:.5f} ks** | Hodnota: {sb_24*cena_24:.2f} € (Zisk: +{max(0.0, (sb_24*cena_24)-v_sb_24):.2f} €)")
                else:
                    st.success(f"🔓 Predaj bez dane ihneď v 2024: **{sb_24:.5f} ks**")
                    
                st.warning(f"🔒 POZOR, MLADÉ FRAKCIE (Zdaňujú sa v 2024): **{mb_24:.5f} ks**")
                if mb_24 > 0 and cena_24 > 0:
                    zm = max(0.0, (mb_24*cena_24)-v_mb_24)
                    st.error(f"⚠️ **Daňový rozpis:** Krátkodobý zisk: `{zm:.2f} €` | Daň (19%): `{zm*0.19:.2f} €` | Odvody (14%): `{zm*0.14:.2f} €` | **Celkovo štátu: -{zm*0.33:.2f} €**")
                
                st.markdown("---")
                st.subheader("📋 Detailný rozpis nákupných balíčkov (2024)")
                csv_str_24 = "\n".join([",".join(row) for row in csv_24])
                st.download_button(label="📥 STIAHNUŤ ROZPIS FRAKCIÍ ZA ROK 2024 (CSV)", data=csv_str_24.encode('utf-8'), file_name=f"t212_frakcie_{ticker_pure_2024}_2024.csv", mime="text/csv", key="btn_24")
                for t in txt_24: st.write(t)
                
        # Dividendy 2024
        st.markdown("##")
        df_div_24 = df_global[(df_global['Action'].str.lower().str.contains('dividend|dividenda', na=False)) & (df_global['Rok'] == 2024) & (df_global['Ticker_Clean'] == ticker_pure_2024 if tickererv_2024 := locals().get('tickerov_2024') else False)].copy()
        exp_div_24 = st.expander("💰 Zobraziť podklady pre Dividendy za daňový rok 2024")
        if len(df_div_24) > 0:
            tb, tt = 0.0, 0.0
            for _, r in df_div_24.iterrows():
                b = float(r['Total']) + float(r['Withholding tax'])
                tb += b; tt += float(r['Withholding tax'])
                exp_div_24.write(f"📅 {pd.to_datetime(r['Time']).strftime('%d.%m.%Y')} | Brutto: {b:.2f} EUR | Daň v zahraničí: {r['Withholding tax']:.2f} EUR")
            exp_div_24.write(f"**Celkový príjem Brutto (Riadok 1):** `{tb:.2f} EUR` | **Zaplatená daň v zahraničí:** `{tt:.2f} EUR`")
        else: exp_div_24.info("V daňovom roku 2024 neboli nájdené žiadne dividendy pre túto akciu.")
        
        # Úroky 2024
        df_ur_24 = df_global[(df_global['Action'].str.lower().str.contains('interest on cash|úrok|urok', na=False)) & (df_global['Rok'] == 2024)].copy()
        exp_ur_24 = st.expander("💶 Zobraziť sumár Úrokov z neinvestovanej hotovosti za daňový rok 2024")
        if len(df_ur_24) > 0:
