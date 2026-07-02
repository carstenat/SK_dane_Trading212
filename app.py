import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

st.set_page_config(page_title="Trading 212 PRO Daňový Assistant (SR)", page_icon="📈", layout="wide")

# =========================================================================
# 🎨 VZHĽAD – DARK / LIGHT MODE
# =========================================================================
st.sidebar.header("⚙️ Nastavenia vzhľadu")
dark_mode = st.sidebar.checkbox("🌙 Tmavý režim (Dark Mode)", value=False)

if dark_mode:
    st.markdown("""
        <style>
        .stApp { background: linear-gradient(180deg, #0B0F19 0%, #10141F 100%) !important; color: #F1F5F9 !important; }
        h1, h2, h3, h4, label, p, span, li { color: #F1F5F9 !important; }
        [data-testid="stSidebar"] { background-color: #0F1420 !important; border-right: 1px solid #1E293B; }
        div[data-testid="stMetric"] {
            background: linear-gradient(145deg, #1A2233, #131A28) !important;
            border: 1px solid #2D3B52 !important; border-radius: 14px !important;
            padding: 16px 20px !important; box-shadow: 0 4px 14px rgba(0,0,0,0.35);
        }
        div[data-testid="stMetricValue"] { color: #38BDF8 !important; }
        .stTabs [data-baseweb="tab"] { color: #94A3B8 !important; }
        .stTabs [aria-selected="true"] { color: #38BDF8 !important; border-bottom-color: #38BDF8 !important; }
        div[data-testid="stDataFrame"] { border: 1px solid #2D3B52 !important; border-radius: 10px; }
        .stDownloadButton button, .stButton button {
            background: linear-gradient(135deg, #2563EB, #1D4ED8) !important; color: white !important;
            border: none !important; border-radius: 10px !important; font-weight: 600 !important;
        }
        div[data-testid="stExpander"] { border: 1px solid #2D3B52 !important; border-radius: 10px !important; background-color: #131A28 !important; }
        </style>
    """, unsafe_allow_html=True)
else:
    st.markdown("""
        <style>
        .stApp { background-color: #FFFFFF !important; color: #1E293B !important; }
        h1, h2, h3, h4 { color: #0F172A !important; }
        [data-testid="stSidebar"] { background-color: #F8FAFC !important; border-right: 1px solid #E2E8F0; }
        div[data-testid="stMetric"] {
            background-color: #F8FAFC !important; border: 1px solid #CBD5E1 !important;
            border-radius: 14px !important; padding: 16px 20px !important;
            box-shadow: 0 2px 8px rgba(15,23,42,0.06);
        }
        div[data-testid="stMetricValue"] { color: #0F172A !important; }
        .stDownloadButton button, .stButton button {
            background: linear-gradient(135deg, #2563EB, #1D4ED8) !important; color: white !important;
            border: none !important; border-radius: 10px !important; font-weight: 600 !important;
        }
        div[data-testid="stExpander"] { border: 1px solid #E2E8F0 !important; border-radius: 10px !important; }
        </style>
    """, unsafe_allow_html=True)

st.title("📈 Súkromný PRO Daňový Optimalizátor – Trading 212 (SR)")
st.caption("Nástroj na kontrolu časového testu, dividend a úrokov pred podaním daňového priznania. "
           "Nie je to daňové poradenstvo – presné sadzby a výnimky si vždy over s daňovým poradcom/účtovníkom.")

# =========================================================================
# 🔧 POMOCNÉ FUNKCIE
# =========================================================================

def sk_num(x, decimals=2):
    """Formátuje číslo do slovenského formátu (desatinná čiarka)."""
    try:
        return f"{x:,.{decimals}f}".replace(",", " ").replace(".", ",")
    except Exception:
        return str(x)


def rows_to_csv_sk(rows):
    """Vytvorí CSV string vhodný pre slovenský Excel (bodkočiarka, čiarka ako desatina)."""
    lines = []
    for row in rows:
        safe_row = ["" if v is None else str(v) for v in row]
        safe_row = [v.replace(";", ",") for v in safe_row]
        lines.append(";".join(safe_row))
    return "\n".join(lines)


@st.cache_data(show_spinner=False)
def load_data(files):
    frames = []
    for f in files:
        frames.append(pd.read_csv(f))
    df = pd.concat(frames, ignore_index=True)

    required = ["Time", "Action", "Ticker", "No. of shares", "Total"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"V CSV chýbajú potrebné stĺpce: {', '.join(missing)}")

    df["Time"] = pd.to_datetime(df["Time"], errors="coerce", utc=True)
    df["Time"] = df["Time"].dt.tz_convert(None)
    # Iba Time musí byť validný. Ticker sa nemaže, lebo napr. úrokové riadky
    # (Interest on cash) v exporte Trading 212 nemajú vyplnený Ticker.
    df = df.dropna(subset=["Time"]).sort_values(by="Time").reset_index(drop=True)

    df["No. of shares"] = pd.to_numeric(df["No. of shares"], errors="coerce").fillna(0.0)
    df["Total"] = pd.to_numeric(df["Total"], errors="coerce").fillna(0.0)

    if "Withholding tax" not in df.columns:
        df["Withholding tax"] = 0.0
    df["Withholding tax"] = pd.to_numeric(df["Withholding tax"], errors="coerce").fillna(0.0)

    if "Name" not in df.columns:
        df["Name"] = ""

    df["Ticker_Clean"] = df["Ticker"].fillna("").astype(str).str.strip().str.upper()
    df["Action_L"] = df["Action"].fillna("").astype(str).str.lower()
    return df


def build_name_map(df):
    mapping = {}
    for _, row in df.iterrows():
        t = row["Ticker_Clean"]
        name = str(row.get("Name", "")).strip()
        if t and t != "NAN" and name and name.lower() != "nan":
            if t not in mapping or len(name) > len(mapping[t]):
                mapping[t] = name
    return mapping


def process_ticker_fifo(df_ticker):
    """FIFO spracovanie jedného tickera. Vracia (zostavajuce_loty, realizovane_predaje)."""
    lots = []
    realized = []

    for _, row in df_ticker.iterrows():
        action = row["Action_L"]
        shares = float(row["No. of shares"])
        total = float(row["Total"])
        date = row["Time"]

        is_buy = ("buy" in action) or ("nákup" in action) or ("nakup" in action)
        is_sell = ("sell" in action) or ("predaj" in action) or (shares < -1e-9 and not is_buy)

        if is_buy:
            if shares > 1e-6:
                cena_za_kus = total / shares if shares != 0 else 0.0
                lots.append({"shares": shares, "date": date, "cena_za_kus": abs(cena_za_kus)})
        elif is_sell:
            sell_shares = abs(shares)
            sell_total = abs(total)
            if sell_shares <= 1e-6:
                continue
            predajna_cena_ks = sell_total / sell_shares
            zostava = sell_shares
            while zostava > 1e-6 and lots:
                lot = lots[0]
                vziat = min(lot["shares"], zostava)
                held_days = (date.date() - lot["date"].date()).days
                exempt = held_days >= 365
                cost = vziat * lot["cena_za_kus"]
                proceeds = vziat * predajna_cena_ks
                realized.append({
                    "sell_date": date,
                    "buy_date": lot["date"],
                    "shares": vziat,
                    "cost": cost,
                    "proceeds": proceeds,
                    "gain": proceeds - cost,
                    "held_days": held_days,
                    "exempt": exempt,
                })
                lot["shares"] -= vziat
                zostava -= vziat
                if lot["shares"] <= 1e-6:
                    lots.pop(0)
    return lots, realized


@st.cache_data(show_spinner=False)
def build_full_fifo(df):
    all_lots = {}
    all_realized = []
    for ticker in sorted(df["Ticker_Clean"].unique()):
        if not ticker or ticker == "NAN":
            continue
        df_t = df[df["Ticker_Clean"] == ticker].sort_values(by="Time").reset_index(drop=True)
        # iba riadky ktoré vyzerajú ako buy/sell obchody
        df_t = df_t[df_t["Action_L"].str.contains("buy|sell|nákup|nakup|predaj|market|limit", na=False)]
        lots, realized = process_ticker_fifo(df_t)
        all_lots[ticker] = lots
        for r in realized:
            r["ticker"] = ticker
            all_realized.append(r)
    realized_df = pd.DataFrame(all_realized)
    if not realized_df.empty:
        realized_df["sell_year"] = realized_df["sell_date"].dt.year
    return all_lots, realized_df


@st.cache_data(show_spinner=False)
def extract_dividends(df):
    div = df[df["Action_L"].str.contains("dividend", na=False)].copy()
    if div.empty:
        return div
    div["Brutto"] = div["Total"] + div["Withholding tax"].abs()
    div["Netto"] = div["Total"]
    div["Zrazena_dan"] = div["Withholding tax"].abs()
    div["Rok"] = div["Time"].dt.year
    return div


@st.cache_data(show_spinner=False)
def extract_interest(df):
    interest = df[df["Action_L"].str.contains("interest", na=False)].copy()
    if interest.empty:
        return interest
    interest["Rok"] = interest["Time"].dt.year
    return interest


# =========================================================================
# 📥 NAHRATIE SÚBOROV
# =========================================================================
uploaded_files = st.file_uploader(
    "Sem presuňte vaše CSV exporty z Trading 212 (môžete aj viac naraz)",
    type=["csv"], accept_multiple_files=True, key="uploader_main_final"
)

if not uploaded_files:
    st.info("⬆️ Nahraj jeden alebo viac CSV exportov z Trading 212 (History → Export).")
    st.stop()

try:
    df = load_data(uploaded_files)
except ValueError as e:
    st.error(f"❌ Chyba pri načítaní CSV: {e}")
    st.stop()

name_map = build_name_map(df)
all_lots, realized_df = build_full_fifo(df)
dividends_df = extract_dividends(df)
interest_df = extract_interest(df)

tab1, tab2, tab3, tab4 = st.tabs([
    "🎯 Optimalizátor predaja",
    "📅 Daňové priznanie za rok",
    "💰 Dividendy",
    "💶 Úroky"
])

# =========================================================================
# TAB 1 – OPTIMALIZÁTOR PRE BUDÚCI PREDAJ (aktuálny stav skladu)
# =========================================================================
with tab1:
    st.header("🔍 Daňový Optimalizátor pre dnešný predaj")

    zoznam_tickerov_all = sorted([t for t in all_lots.keys() if t])
    if not zoznam_tickerov_all:
        st.warning("V dátach sa nenašli žiadne nákupy/predaje akcií.")
    else:
        ponuka_pre_menu = []
        mapovanie_tickerov = {}
        for t in zoznam_tickerov_all:
            full_company_name = name_map.get(t, "Spoločnosť z platformy")
            text_riadku = f"{t} - {full_company_name}"
            ponuka_pre_menu.append(text_riadku)
            mapovanie_tickerov[text_riadku] = t
        ponuka_pre_menu = sorted(set(ponuka_pre_menu))

        vybrany_text = st.selectbox("Vyberte akciu zo svojho portfólia, ktorú plánujete predať:",
                                     ponuka_pre_menu, key="sel_linearna_final")
        vybrany_ticker_pure = mapovanie_tickerov[vybrany_text]

        col1, col2 = st.columns(2)
        with col1:
            vstup_vlastnene = st.number_input("Počet kusov vlastnených na platforme Trading 212:",
                                               min_value=0.0, value=0.0, step=0.00001, format="%.5f",
                                               key="vstup_stav_final")
        with col2:
            aktualna_cena = st.number_input("Aktuálna trhová cena akcie v EUR (voliteľné):",
                                             min_value=0.0, value=0.0, step=0.01, format="%.2f",
                                             key="vstup_cena_final")

        sklad_aktualny = [dict(l) for l in all_lots.get(vybrany_ticker_pure, [])]
        max_sklad_dostupny = sum(x["shares"] for x in sklad_aktualny)

        skutocny_stav = vstup_vlastnene
        if vstup_vlastnene > max_sklad_dostupny + 1e-6:
            st.error(f"⚠️ Pozor: Zadali ste {vstup_vlastnene:.5f} ks, ale podľa histórie v CSV zostáva len "
                     f"{max_sklad_dostupny:.5f} ks {vybrany_ticker_pure}. Výpočet orezávame na reálne maximum "
                     f"z dát (môže to byť spôsobené chýbajúcim starším CSV exportom).")
            skutocny_stav = max_sklad_dostupny

        potrebne_ks = skutocny_stav
        dnes = datetime.now()
        ks_bez_dane = 0.0
        ks_mlade = 0.0
        vydavok_safe_balika = 0.0
        vydavok_mladeho_balika = 0.0
        rozpis_textov = []
        export_csv_riadky = [["Datum nakupu", "Mnozstvo (ks)", "Nakupna cena/ks", "Celkovy nakup",
                               "Danovy stav", "Datum oslobodenia", "Zostava cakat"]]

        for n in sklad_aktualny:
            if potrebne_ks < 1e-5:
                break
            vziat_ks = min(n["shares"], potrebne_ks)
            potrebne_ks -= vziat_ks

            nakup_pure = pd.to_datetime(n["date"]).to_pydatetime()
            vek_dni = (dnes.date() - nakup_pure.date()).days
            cena_balika = vziat_ks * n["cena_za_kus"]

            d_nakupu = nakup_pure.strftime("%d.%m.%Y")
            text_mnozstva = f"{vziat_ks:.5f} ks"
            text_ceny = f"{n['cena_za_kus']:.2f} EUR/ks"
            text_celkovo = f"Spolu: {cena_balika:.2f} EUR"

            if vek_dni >= 365:
                ks_bez_dane += vziat_ks
                vydavok_safe_balika += cena_balika
                rozpis_textov.append(
                    f"🟢 **BEZ DANE** | Nákup: {d_nakupu} | Množstvo: {text_mnozstva} pri cene {text_ceny} "
                    f"({text_celkovo}) | ⏳ Netreba čakať (Oslobodené)")
                export_csv_riadky.append([d_nakupu, f"{vziat_ks:.5f}", f"{n['cena_za_kus']:.2f}",
                                           f"{cena_balika:.2f}", "Bez dane", "Uz oslobodene", "0 dni"])
            else:
                ks_mlade += vziat_ks
                vydavok_mladeho_balika += cena_balika
                d_oslobodenia = (nakup_pure + timedelta(days=365)).strftime("%d.%m.%Y")
                zostava_dni = 365 - vek_dni
                rozpis_textov.append(
                    f"🔴 **ZDAŇUJE SA** | Nákup: {d_nakupu} | Množstvo: {text_mnozstva} pri cene {text_ceny} "
                    f"({text_celkovo}) | ⏳ Zostáva čakať: **{zostava_dni} dní** (Oslobodenie: {d_oslobodenia})")
                export_csv_riadky.append([d_nakupu, f"{vziat_ks:.5f}", f"{n['cena_za_kus']:.2f}",
                                           f"{cena_balika:.2f}", "Zdanuje sa", d_oslobodenia, f"{zostava_dni} dni"])

        ks_bez_dane = round(ks_bez_dane, 5)
        ks_mlade = round(ks_mlade, 5)

        if skutocny_stav > 0:
            st.markdown(f"**Vizuálny pomer safe pozície:** {ks_bez_dane:.5f} ks z {skutocny_stav:.5f} ks")
            vypocitany_pomer = float(ks_bez_dane / skutocny_stav) if skutocny_stav > 0 else 0.0
            st.progress(max(0.0, min(1.0, vypocitany_pomer)))

            trhova_hodnota_safe = ks_bez_dane * aktualna_cena
            cisty_zisk_safe = max(0.0, trhova_hodnota_safe - vydavok_safe_balika)
            st.success(f"🔓 Môžete predať IHNEĎ BEZ DANE: **{ks_bez_dane:.5f} ks** | "
                       f"Súčasná hodnota: {trhova_hodnota_safe:.2f} € "
                       f"(Čistý oslobodený zisk: +{cisty_zisk_safe:.2f} €)")

            trhova_hodnota_mlade = ks_mlade * aktualna_cena
            zisk_mlade = max(0.0, trhova_hodnota_mlade - vydavok_mladeho_balika)
            dan_19 = round(zisk_mlade * 0.19, 2)
            odvody_14 = round(zisk_mlade * 0.14, 2)
            celkovy_vypal_statu = dan_19 + odvody_14

            st.warning(f"🔒 POZOR, MLADÉ FRAKCIE (Zdaňujú sa pri predaji dnes): {ks_mlade:.5f} ks")
            st.error(f"⚠️ **Daňový rozpis pre mladé akcie:** Krátkodobý zisk: `{zisk_mlade:.2f} EUR` | "
                     f"Daň z príjmu (19%): `{dan_19:.2f} EUR` | Zdravotné odvody (14%)*: `{odvody_14:.2f} EUR` | "
                     f"**Celkovo odovzdáte štátu: -{celkovy_vypal_statu:.2f} EUR**")
            st.caption("*Zdravotné odvody z kapitálových príjmov majú výnimky a menia sa – over si aktuálny stav "
                       "s účtovníkom/zdravotnou poisťovňou.")

            st.markdown("---")
            st.subheader("📋 Detailný rozpis nákupných balíčkov (Frakcií)")
            csv_string = rows_to_csv_sk(export_csv_riadky)
            st.download_button(
                label="📥 STIAHNUŤ TENTO ROZPIS FRAKCIÍ DO EXCELU (CSV)",
                data=csv_string.encode("utf-8-sig"),
                file_name=f"t212_rozpis_frakcii_{vybrany_ticker_pure}.csv",
                mime="text/csv", key="btn_export_frakcii_v980")

            with st.expander("Zobraziť chronologický zoznam balíčkov"):
                for r_text in rozpis_textov:
                    st.write(r_text)
        else:
            st.info("Zadaj počet vlastnených kusov vyššie pre výpočet.")

# =========================================================================
# TAB 2 – DAŇOVÉ PRIZNANIE ZA KONKRÉTNY ROK
# =========================================================================
with tab2:
    st.header("📅 Súhrn pre daňové priznanie za zvolený rok")

    years = set()
    if not realized_df.empty:
        years |= set(realized_df["sell_year"].dropna().astype(int).tolist())
    if not dividends_df.empty:
        years |= set(dividends_df["Rok"].dropna().astype(int).tolist())
    if not interest_df.empty:
        years |= set(interest_df["Rok"].dropna().astype(int).tolist())

    if not years:
        st.info("V nahraných dátach sa nenašli žiadne predaje, dividendy ani úroky.")
    else:
        years_sorted = sorted(years, reverse=True)
        zvoleny_rok = st.selectbox("Vyber daňový rok (rok, za ktorý sa podáva priznanie v SR):", years_sorted)

        # --- Realizované predaje za rok ---
        r_year = realized_df[realized_df["sell_year"] == zvoleny_rok] if not realized_df.empty else pd.DataFrame()

        oslobodene = r_year[r_year["exempt"] == True] if not r_year.empty else pd.DataFrame()
        zdanitelne = r_year[r_year["exempt"] == False] if not r_year.empty else pd.DataFrame()

        zisk_oslobodeny = oslobodene["gain"].sum() if not oslobodene.empty else 0.0
        zisk_zdanitelny_net = zdanitelne["gain"].sum() if not zdanitelne.empty else 0.0
        zaklad_dane = max(0.0, zisk_zdanitelny_net)
        dan_z_predaja = round(zaklad_dane * 0.19, 2)
        odvody_z_predaja = round(zaklad_dane * 0.14, 2)

        st.subheader("📈 Realizované predaje (kapitálové zisky)")
        c1, c2, c3 = st.columns(3)
        c1.metric("Zisk oslobodený od dane (>365 dní)", f"{sk_num(zisk_oslobodeny)} €")
        c2.metric("Zdaniteľný zisk/strata (<365 dní), netto", f"{sk_num(zisk_zdanitelny_net)} €")
        c3.metric("Základ dane (min. 0)", f"{sk_num(zaklad_dane)} €")

        st.error(f"⚠️ Odhadovaná daň z kapitálových príjmov za {zvoleny_rok}: daň z príjmu (19%) "
                 f"`{sk_num(dan_z_predaja)} €` + zdravotné odvody (14%)* `{sk_num(odvody_z_predaja)} €` "
                 f"= **{sk_num(dan_z_predaja + odvody_z_predaja)} €**")
        st.caption("*Straty a zisky sa tu netujú len v rámci zdaniteľnej (mladej) skupiny. Oslobodené obchody "
                   "(>365 dní) sa do základu dane nezapočítavajú. Toto je orientačný výpočet, nie daňové poradenstvo.")

        if not r_year.empty:
            with st.expander("Zobraziť detail všetkých predajov za rok " + str(zvoleny_rok)):
                show = r_year.copy()
                show["Ticker"] = show["ticker"]
                show["Nákup"] = show["buy_date"].dt.strftime("%d.%m.%Y")
                show["Predaj"] = show["sell_date"].dt.strftime("%d.%m.%Y")
                show["Dni_drzania"] = show["held_days"]
                show["Stav"] = show["exempt"].map({True: "Oslobodené", False: "Zdaňuje sa"})
                show = show[["Ticker", "Nákup", "Predaj", "shares", "cost", "proceeds", "gain",
                              "Dni_drzania", "Stav"]]
                show.columns = ["Ticker", "Dátum nákupu", "Dátum predaja", "Množstvo", "Náklady (€)",
                                 "Výnos (€)", "Zisk/Strata (€)", "Dní držania", "Daňový stav"]
                st.dataframe(show, use_container_width=True)

        # --- Dividendy za rok ---
        d_year = dividends_df[dividends_df["Rok"] == zvoleny_rok] if not dividends_df.empty else pd.DataFrame()
        brutto_div = d_year["Brutto"].sum() if not d_year.empty else 0.0
        zrazena_div = d_year["Zrazena_dan"].sum() if not d_year.empty else 0.0

        st.subheader("💰 Dividendy")
        d1, d2, d3 = st.columns(3)
        d1.metric("Brutto dividendy", f"{sk_num(brutto_div)} €")
        d2.metric("Zahraničná zrazená daň", f"{sk_num(zrazena_div)} €")
        d3.metric("Netto prijaté", f"{sk_num(brutto_div - zrazena_div)} €")

        # --- Úroky za rok ---
        i_year = interest_df[interest_df["Rok"] == zvoleny_rok] if not interest_df.empty else pd.DataFrame()
        uroky_total = i_year["Total"].sum() if not i_year.empty else 0.0
        dan_uroky = round(max(0.0, uroky_total) * 0.19, 2)

        st.subheader("💶 Úroky z nevloženej hotovosti")
        u1, u2 = st.columns(2)
        u1.metric("Prijaté úroky spolu", f"{sk_num(uroky_total)} €")
        u2.metric("Odhadovaná daň (19%)", f"{sk_num(dan_uroky)} €")

        # --- Kompletný CSV export pre rok ---
        st.markdown("---")
        st.subheader(f"📥 Kompletný report pre účtovníka – rok {zvoleny_rok}")

        report_rows = [["=== SÚHRN ZA ROK", str(zvoleny_rok), "", "", "", "", ""]]
        report_rows.append(["Kategória", "Suma (EUR)", "", "", "", "", ""])
        report_rows.append(["Oslobodený zisk z predaja akcií", f"{zisk_oslobodeny:.2f}"])
        report_rows.append(["Zdaniteľný zisk/strata z predaja akcií (netto)", f"{zisk_zdanitelny_net:.2f}"])
        report_rows.append(["Základ dane z predaja (min. 0)", f"{zaklad_dane:.2f}"])
        report_rows.append(["Daň z príjmu z predaja (19%)", f"{dan_z_predaja:.2f}"])
        report_rows.append(["Zdravotné odvody z predaja (14%, orientačne)", f"{odvody_z_predaja:.2f}"])
        report_rows.append(["Dividendy brutto", f"{brutto_div:.2f}"])
        report_rows.append(["Dividendy - zahraničná zrazená daň", f"{zrazena_div:.2f}"])
        report_rows.append(["Dividendy netto", f"{brutto_div - zrazena_div:.2f}"])
        report_rows.append(["Úroky spolu", f"{uroky_total:.2f}"])
        report_rows.append(["Odhadovaná daň z úrokov (19%)", f"{dan_uroky:.2f}"])
        report_rows.append([""])
        report_rows.append(["=== DETAIL PREDAJOV", "", "", "", "", "", ""])
        report_rows.append(["Ticker", "Datum nakupu", "Datum predaja", "Mnozstvo", "Naklady EUR",
                             "Vynos EUR", "Zisk/Strata EUR", "Dni drzania", "Danovy stav"])
        if not r_year.empty:
            for _, rr in r_year.iterrows():
                report_rows.append([
                    rr["ticker"], rr["buy_date"].strftime("%d.%m.%Y"), rr["sell_date"].strftime("%d.%m.%Y"),
                    f"{rr['shares']:.5f}", f"{rr['cost']:.2f}", f"{rr['proceeds']:.2f}", f"{rr['gain']:.2f}",
                    str(rr["held_days"]), "Oslobodene" if rr["exempt"] else "Zdanuje sa"
                ])
        report_rows.append([""])
        report_rows.append(["=== DETAIL DIVIDEND", "", "", "", "", "", ""])
        report_rows.append(["Ticker", "Datum", "Brutto EUR", "Zrazena dan EUR", "Netto EUR"])
        if not d_year.empty:
            for _, dd in d_year.iterrows():
                report_rows.append([
                    dd["Ticker_Clean"], dd["Time"].strftime("%d.%m.%Y"),
                    f"{dd['Brutto']:.2f}", f"{dd['Zrazena_dan']:.2f}", f"{dd['Netto']:.2f}"
                ])
        report_rows.append([""])
        report_rows.append(["=== DETAIL UROKOV", "", "", "", "", "", ""])
        report_rows.append(["Datum", "Suma EUR"])
        if not i_year.empty:
            for _, ii in i_year.iterrows():
                report_rows.append([ii["Time"].strftime("%d.%m.%Y"), f"{ii['Total']:.2f}"])

        full_csv = rows_to_csv_sk(report_rows)
        st.download_button(
            label=f"📥 STIAHNUŤ KOMPLETNÝ DAŇOVÝ REPORT ZA ROK {zvoleny_rok} (CSV)",
            data=full_csv.encode("utf-8-sig"),
            file_name=f"t212_danovy_report_{zvoleny_rok}.csv",
            mime="text/csv", key="btn_export_rocny_report")

# =========================================================================
# TAB 3 – DIVIDENDY (celá história, filtrovateľná)
# =========================================================================
with tab3:
    st.header("💰 História dividend")
    if dividends_df.empty:
        st.info("V nahraných CSV sa nenašli žiadne dividendové platby.")
    else:
        rok_filter = st.multiselect("Filtrovať podľa roka:",
                                     sorted(dividends_df["Rok"].unique(), reverse=True),
                                     key="div_rok_filter")
        show_div = dividends_df.copy()
        if rok_filter:
            show_div = show_div[show_div["Rok"].isin(rok_filter)]

        c1, c2, c3 = st.columns(3)
        c1.metric("Brutto spolu", f"{sk_num(show_div['Brutto'].sum())} €")
        c2.metric("Zahr. zrazená daň spolu", f"{sk_num(show_div['Zrazena_dan'].sum())} €")
        c3.metric("Netto spolu", f"{sk_num(show_div['Netto'].sum())} €")

        display = show_div[["Time", "Ticker_Clean", "Brutto", "Zrazena_dan", "Netto"]].copy()
        display["Time"] = display["Time"].dt.strftime("%d.%m.%Y")
        display.columns = ["Dátum", "Ticker", "Brutto (€)", "Zrazená daň (€)", "Netto (€)"]
        st.dataframe(display, use_container_width=True)

        div_csv_rows = [["Datum", "Ticker", "Brutto EUR", "Zrazena dan EUR", "Netto EUR"]]
        for _, row in show_div.iterrows():
            div_csv_rows.append([row["Time"].strftime("%d.%m.%Y"), row["Ticker_Clean"],
                                  f"{row['Brutto']:.2f}", f"{row['Zrazena_dan']:.2f}", f"{row['Netto']:.2f}"])
        st.download_button("📥 Stiahnuť dividendy (CSV)",
                            data=rows_to_csv_sk(div_csv_rows).encode("utf-8-sig"),
                            file_name="t212_dividendy.csv", mime="text/csv", key="btn_export_dividendy")

        st.caption("Sadzba dane z dividend v SR závisí od krajiny pôvodu spoločnosti a zmluvy o zamedzení "
                   "dvojitého zdanenia (typicky 7 % alebo 35 %) + 14 % zdravotné odvody. Presnú sadzbu si "
                   "over podľa krajiny emitenta – tento nástroj zámerne neuhaduje sadzbu automaticky.")

# =========================================================================
# TAB 4 – ÚROKY
# =========================================================================
with tab4:
    st.header("💶 História úrokov z nevloženej hotovosti")
    if interest_df.empty:
        st.info("V nahraných CSV sa nenašli žiadne úrokové platby.")
    else:
        rok_filter_i = st.multiselect("Filtrovať podľa roka:",
                                       sorted(interest_df["Rok"].unique(), reverse=True),
                                       key="int_rok_filter")
        show_int = interest_df.copy()
        if rok_filter_i:
            show_int = show_int[show_int["Rok"].isin(rok_filter_i)]

        total_int = show_int["Total"].sum()
        dan_int = round(max(0.0, total_int) * 0.19, 2)

        c1, c2 = st.columns(2)
        c1.metric("Úroky spolu", f"{sk_num(total_int)} €")
        c2.metric("Odhadovaná daň (19%)", f"{sk_num(dan_int)} €")

        display_i = show_int[["Time", "Total"]].copy()
        display_i["Time"] = display_i["Time"].dt.strftime("%d.%m.%Y")
        display_i.columns = ["Dátum", "Suma (€)"]
        st.dataframe(display_i, use_container_width=True)

        int_csv_rows = [["Datum", "Suma EUR"]]
        for _, row in show_int.iterrows():
            int_csv_rows.append([row["Time"].strftime("%d.%m.%Y"), f"{row['Total']:.2f}"])
        st.download_button("📥 Stiahnuť úroky (CSV)",
                            data=rows_to_csv_sk(int_csv_rows).encode("utf-8-sig"),
                            file_name="t212_uroky.csv", mime="text/csv", key="btn_export_uroky")

        st.caption("Úroky z hotovosti sa v SR zdaňujú ako 'ostatný príjem' sadzbou 19 % (nad určitú ročnú "
                   "hranicu základu dane môže platiť vyššia sadzba 25 %). Over si aktuálny limit pre daný rok.")
