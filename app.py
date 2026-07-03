import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

st.set_page_config(page_title="Trading 212 PRO Daňový Assistant (SR)", page_icon="📈", layout="wide")

# =========================================================================
# 🎨 VZHĽAD – DARK / LIGHT MODE (dôkladný kontrast pre všetky prvky)
# =========================================================================
st.sidebar.markdown("### ⚙️ Vzhľad")
dark_mode = st.sidebar.checkbox("🌙 Tmavý režim", value=False)

if dark_mode:
    st.markdown("""
        <style>
        .stApp { background: linear-gradient(180deg, #0B0F19 0%, #10141F 100%) !important; color: #F1F5F9 !important; }
        h1, h2, h3, h4, h5, label, p, span, li, strong, em { color: #F1F5F9 !important; }
        [data-testid="stSidebar"] { background-color: #0B0F19 !important; border-right: 1px solid #1E293B; }
        [data-testid="stSidebar"] * { color: #F1F5F9 !important; }

        div[data-testid="stMetric"] {
            background: linear-gradient(145deg, #1A2233, #131A28) !important;
            border: 1px solid #2D3B52 !important; border-radius: 12px !important;
            padding: 14px 18px !important; box-shadow: 0 4px 14px rgba(0,0,0,0.35);
        }
        div[data-testid="stMetricValue"] { color: #38BDF8 !important; }
        div[data-testid="stMetricLabel"] { color: #94A3B8 !important; }

        div[data-testid="stDataFrame"] { border: 1px solid #2D3B52 !important; border-radius: 10px; }
        div[data-testid="stDataFrame"] * { color: #0F172A !important; }

        .stDownloadButton button, .stButton button {
            background: linear-gradient(135deg, #2563EB, #1D4ED8) !important; color: white !important;
            border: none !important; border-radius: 10px !important; font-weight: 600 !important;
        }
        div[data-testid="stExpander"] {
            border: 1px solid #2D3B52 !important; border-radius: 10px !important; background-color: #131A28 !important;
        }
        div[data-testid="stExpander"] summary { color: #F1F5F9 !important; }

        /* --- Popover (❓ vysvetlivky) --- */
        div[data-testid="stPopover"] > div { background-color: #131A28 !important; border: 1px solid #2D3B52 !important; }
        div[data-testid="stPopoverBody"] { background-color: #131A28 !important; color: #F1F5F9 !important; }

        /* --- Selectbox / Multiselect / Number input / BaseWeb prvky --- */
        [data-baseweb="select"] > div { background-color: #1A2233 !important; color: #F1F5F9 !important; border-color: #2D3B52 !important; }
        [data-baseweb="popover"] { background-color: #131A28 !important; }
        ul[role="listbox"] { background-color: #131A28 !important; }
        li[role="option"] { color: #F1F5F9 !important; background-color: #131A28 !important; }
        li[role="option"]:hover { background-color: #1A2233 !important; }
        [data-baseweb="tag"] { background-color: #2563EB !important; color: #FFFFFF !important; }
        input, textarea { background-color: #1A2233 !important; color: #F1F5F9 !important; }
        [data-testid="stNumberInput"] input { background-color: #1A2233 !important; color: #F1F5F9 !important; }
        [data-testid="stNumberInput"] button { background-color: #1A2233 !important; color: #F1F5F9 !important; }

        /* --- Radio "pilulky" (rok, sekcia) --- */
        div[role="radiogroup"] label {
            background-color: #1A2233 !important; border: 1px solid #2D3B52 !important;
            border-radius: 999px !important; padding: 8px 16px !important; margin: 4px 4px 4px 0 !important;
        }
        div[role="radiogroup"] label:has(input:checked) { border: 2px solid #38BDF8 !important; background-color: #1E293B !important; }

        code, .stCode, pre { background-color: #0B0F19 !important; color: #7DD3FC !important; }
        [data-testid="stCaptionContainer"] { color: #94A3B8 !important; }
        hr { border-color: #2D3B52 !important; }
        </style>
    """, unsafe_allow_html=True)
else:
    st.markdown("""
        <style>
        .stApp { background-color: #FFFFFF !important; color: #1E293B !important; }
        h1, h2, h3, h4, h5 { color: #0F172A !important; }
        [data-testid="stSidebar"] { background-color: #F8FAFC !important; border-right: 1px solid #E2E8F0; }
        div[data-testid="stMetric"] {
            background-color: #F8FAFC !important; border: 1px solid #CBD5E1 !important;
            border-radius: 12px !important; padding: 14px 18px !important;
            box-shadow: 0 2px 8px rgba(15,23,42,0.06);
        }
        div[data-testid="stMetricValue"] { color: #0F172A !important; }
        .stDownloadButton button, .stButton button {
            background: linear-gradient(135deg, #2563EB, #1D4ED8) !important; color: white !important;
            border: none !important; border-radius: 10px !important; font-weight: 600 !important;
        }
        div[data-testid="stExpander"] { border: 1px solid #E2E8F0 !important; border-radius: 10px !important; }
        div[role="radiogroup"] label {
            background-color: #F1F5F9 !important; border: 1px solid #CBD5E1 !important;
            border-radius: 999px !important; padding: 8px 16px !important; margin: 4px 4px 4px 0 !important;
        }
        div[role="radiogroup"] label:has(input:checked) { border: 2px solid #2563EB !important; background-color: #EFF6FF !important; }
        </style>
    """, unsafe_allow_html=True)

# Spoločné CSS pre oba režimy – mobilné/tabletové rozloženie
st.markdown("""
    <style>
    div[data-testid="stHorizontalBlock"] { flex-wrap: wrap !important; gap: 10px !important; }
    div[data-testid="column"] { min-width: 200px !important; flex: 1 1 200px !important; }
    @media (max-width: 640px) {
        div[data-testid="stMetricValue"] { font-size: 1.3rem !important; }
        h1 { font-size: 1.4rem !important; }
    }
    </style>
""", unsafe_allow_html=True)

st.title("📈 Súkromný PRO Daňový Optimalizátor – Trading 212 (SR)")
st.caption("Nie je to daňové poradenstvo. Sadzby a hranice sú aktualizované k júlu 2026 – vždy si ich over "
           "s daňovým poradcom/účtovníkom pred podaním priznania.")

# =========================================================================
# 🏛️ DAŇOVÉ PARAMETRE SR (aktualizované k júlu 2026, zdroje: financnasprava.sk,
# VšZP, Sociálna poisťovňa, bluenumbers.sk, akcie.sk – over si prípadné zmeny)
# =========================================================================

def get_zdravotne_odvody_sadzba(rok):
    """Sadzba zdravotných odvodov z kapitálových/ostatných príjmov (predaj CP)."""
    if rok <= 2023:
        return 0.14
    elif rok in (2024, 2025):
        return 0.15
    else:  # 2026 a neskôr
        return 0.16


def get_prah_info(rok):
    """Informačný text o daňových pásmach pre dané zdaňovacie obdobie."""
    if rok <= 2025:
        return ("19 % z celkového základu dane (vrátane príjmu zo zamestnania a i.) do cca 48 441 € "
                 "(176,8-násobok životného minima za rok 2025), nad touto hranicou 25 %.")
    else:
        return ("Od roku 2026 platia 4 pásma z celkového základu dane: 19 % do 43 983,32 €, "
                 "25 % do 60 349,21 €, 30 % do 75 010,32 €, 35 % nad touto sumou (hranice sa každoročne "
                 "menia podľa životného minima).")


ROCNE_OSLOBODENIE_CP = 500.0  # § 9 ods. 1 zákona o dani z príjmov – kombinované pre "ostatné príjmy" § 8


def spocitaj_dan_z_predaja(zisk, rok, uplatnit_oslobodenie=True, uz_vyuzite_oslobodenie=0.0,
                            sadzba_dan=0.19, sadzba_odvody=None):
    """Vypočíta základ dane, daň a odvody zo zisku z predaja cenných papierov."""
    if sadzba_odvody is None:
        sadzba_odvody = get_zdravotne_odvody_sadzba(rok)
    volne_oslobodenie = max(0.0, ROCNE_OSLOBODENIE_CP - uz_vyuzite_oslobodenie) if uplatnit_oslobodenie else 0.0
    pouzite_oslobodenie = min(volne_oslobodenie, max(0.0, zisk))
    zaklad = max(0.0, zisk - pouzite_oslobodenie)
    dan = round(zaklad * sadzba_dan, 2)
    odvody = round(zaklad * sadzba_odvody, 2)
    return zaklad, dan, odvody, pouzite_oslobodenie


def spocitaj_dan_z_dividend(brutto, zrazena_zahranicna, sadzba_sk=0.07):
    """Zrážková daň SK + zápočet zahraničnej zrazenej dane (žiadne zdravotné odvody - dividendy 2017+)."""
    dan_sk = round(brutto * sadzba_sk, 2)
    zapocet = min(zrazena_zahranicna, dan_sk)
    doplatok = round(max(0.0, dan_sk - zapocet), 2)
    return dan_sk, zapocet, doplatok

# =========================================================================
# 🔧 POMOCNÉ FUNKCIE (dátová logika)
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
# 🎴 POMOCNÉ FUNKCIE PRE ZOBRAZENIE
# =========================================================================

def help_popover(text, title=None):
    """Malá ❓ ikona, ktorá po kliknutí otvorí plávajúce okno s vysvetlením."""
    with st.popover("❓", use_container_width=False):
        if title:
            st.markdown(f"**{title}**")
        st.write(text)


def section_header(title, help_text, help_title=None):
    c1, c2 = st.columns([12, 1])
    with c1:
        st.subheader(title)
    with c2:
        help_popover(help_text, help_title)


def build_frakcie_table(lots, ticker, name):
    """Zostaví kompaktnú tabuľku frakcií (1 riadok = 1 balíček) s farebným stavom."""
    dnes = datetime.now()
    riadky = []
    for lot in lots:
        nakup = pd.to_datetime(lot["date"]).to_pydatetime()
        vek_dni = (dnes.date() - nakup.date()).days
        exempt = vek_dni >= 365
        datum_testu = (nakup + timedelta(days=365)).strftime("%d.%m.%Y")
        riadky.append({
            "Dátum nákupu": nakup.strftime("%d.%m.%Y"),
            "Ticker": ticker,
            "Názov": name,
            "Kusy": round(lot["shares"], 5),
            "Cena/ks (€)": round(lot["cena_za_kus"], 2),
            "Dátum uplynutia testu": datum_testu,
            "Stav": "🟢 Môže predať" if exempt else "🔴 Ešte nie",
            "Dní do predaja": 0 if exempt else (365 - vek_dni),
            "_sort": nakup,
        })
    dfr = pd.DataFrame(riadky).sort_values("_sort").drop(columns=["_sort"]).reset_index(drop=True)
    return dfr


def farebna_tabulka(dfr):
    def farba(row):
        if "🟢" in str(row["Stav"]):
            return ["background-color: rgba(34,197,94,0.28)"] * len(row)
        else:
            return ["background-color: rgba(239,68,68,0.28)"] * len(row)
    return dfr.style.apply(farba, axis=1)


# =========================================================================
# 📁 NAHRATIE DÁT (bočný panel)
# =========================================================================
st.sidebar.markdown("---")
st.sidebar.markdown("### 📁 Dáta")

if "files_confirmed" not in st.session_state:
    st.session_state.files_confirmed = None

uploaded_files = st.sidebar.file_uploader(
    "CSV exporty z Trading 212",
    type=["csv"], accept_multiple_files=True, key="uploader_main_final",
    help="Trading 212 → Účet → History → Export → CSV. Môžeš nahrať aj viac súborov naraz."
)

if not uploaded_files:
    st.info("👈 Najprv v bočnom paneli nahraj aspoň jeden CSV export z Trading 212, aby si mohol pokračovať.")
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

st.sidebar.success(f"✅ {len(df)} riadkov z {len(uploaded_files)} súboru(-ov)")

# =========================================================================
# 🧭 NAVIGÁCIA (bočný panel) – sekcia
# =========================================================================
st.sidebar.markdown("---")
st.sidebar.markdown("### 🧭 Sekcia")
sekcia = st.sidebar.radio("Sekcia", ["📈 Akcie", "💰 Dividendy", "💶 Úroky"],
                           label_visibility="collapsed", key="sekcia_nav")

# =========================================================================
# 📈 SEKCIA: AKCIE
# =========================================================================
if sekcia == "📈 Akcie":

    # --- Roky dostupné pre daňové priznanie (roky s realizovanými predajmi) ---
    dostupne_roky = sorted(realized_df["sell_year"].dropna().astype(int).unique(), reverse=True) \
        if not realized_df.empty else []

    st.sidebar.markdown("---")
    st.sidebar.markdown("### 📅 Daňový rok")
    if dostupne_roky:
        zvoleny_rok = st.sidebar.radio("Daňový rok", [str(r) for r in dostupne_roky],
                                        label_visibility="collapsed", key="rok_nav")
        zvoleny_rok = int(zvoleny_rok)
    else:
        st.sidebar.caption("Zatiaľ nemáš žiadne realizované predaje.")
        zvoleny_rok = None

    # =====================================================================
    # 1) PREHĽAD ZA ZVOLENÝ ROK – BRUTTO → NETTO
    # =====================================================================
    if zvoleny_rok is not None:
        section_header(
            f"📊 Prehľad za rok {zvoleny_rok}",
            "Toto je spätný pohľad na obchody, ktoré si v tomto roku SKUTOČNE zrealizoval (predal). "
            "Tieto čísla použi do daňového priznania za tento rok (podáva sa do konca marca nasledujúceho roka).",
            "Čo je toto?"
        )

        r_year = realized_df[realized_df["sell_year"] == zvoleny_rok]
        oslobodene = r_year[r_year["exempt"] == True]
        zdanitelne = r_year[r_year["exempt"] == False]

        nakupy_spolu = r_year["cost"].sum()
        predaje_spolu = r_year["proceeds"].sum()
        hruby_zisk = r_year["gain"].sum()
        zisk_oslobodeny = oslobodene["gain"].sum() if not oslobodene.empty else 0.0
        zisk_zdanitelny = zdanitelne["gain"].sum() if not zdanitelne.empty else 0.0

        st.markdown("**🔵 Brutto (pred zdanením)**")
        b1, b2, b3 = st.columns(3)
        b1.metric("Nákupy spolu", f"{sk_num(nakupy_spolu)} €")
        b2.metric("Predaje spolu", f"{sk_num(predaje_spolu)} €")
        b3.metric("Hrubý zisk/strata", f"{sk_num(hruby_zisk)} €")

        st.markdown("**🟢🔴 Rozdelenie podľa 365-dňového testu**")
        r1, r2 = st.columns(2)
        r1.metric("Oslobodené (>365 dní)", f"{sk_num(zisk_oslobodeny)} €")
        r2.metric("Zdaniteľné (<365 dní)", f"{sk_num(zisk_zdanitelny)} €")

        with st.expander("⚙️ Daňové nastavenia pre tento výpočet (predvyplnené aktuálnou legislatívou)"):
            c1, c2 = st.columns(2)
            with c1:
                uplatnit_oslob = st.checkbox("Uplatniť 500 € ročné oslobodenie (§9)", value=True,
                                              key=f"oslob_{zvoleny_rok}")
                sadzba_dan_predaj = st.number_input("Sadzba dane z príjmu (%)", value=19.0, step=0.1,
                                                     key=f"sadzba_dan_{zvoleny_rok}") / 100
            with c2:
                sadzba_odvody_predaj = st.number_input(
                    "Zdravotné odvody (%)", value=get_zdravotne_odvody_sadzba(zvoleny_rok) * 100, step=0.1,
                    key=f"sadzba_odv_{zvoleny_rok}") / 100
                uz_vyuzite = st.number_input("Už využité z 500 € oslobodenia (iným príjmom, €)", value=0.0,
                                              step=10.0, key=f"vyuzite_{zvoleny_rok}")
            st.caption(get_prah_info(zvoleny_rok))

        zaklad, dan, odvody, pouzite_oslob = spocitaj_dan_z_predaja(
            zisk_zdanitelny, zvoleny_rok, uplatnit_oslob, uz_vyuzite, sadzba_dan_predaj, sadzba_odvody_predaj)
        cisty_zisk = hruby_zisk - dan - odvody

        st.markdown("**⚪ Netto (po dani)**")
        n1, n2, n3 = st.columns(3)
        n1.metric("Základ dane (po 500€ oslobodení)", f"{sk_num(zaklad)} €")
        n2.metric("Daň + odvody spolu", f"{sk_num(dan + odvody)} €",
                  help=f"Daň z príjmu: {sk_num(dan)} € · Zdravotné odvody: {sk_num(odvody)} €")
        n3.metric("Čistý zisk po zdanení", f"{sk_num(cisty_zisk)} €")

        with st.expander("🧮 Over si výpočet dane sám"):
            st.code(
f"""Zdaniteľný zisk (<365 dní)   = {zisk_zdanitelny:.2f} €
Použité 500€ oslobodenie     = {pouzite_oslob:.2f} €
Základ dane                  = {zisk_zdanitelny:.2f} € − {pouzite_oslob:.2f} € = {zaklad:.2f} €

Daň z príjmu ({sadzba_dan_predaj*100:.1f} %)     = {zaklad:.2f} € × {sadzba_dan_predaj:.3f} = {dan:.2f} €
Zdravotné odvody ({sadzba_odvody_predaj*100:.1f} %) = {zaklad:.2f} € × {sadzba_odvody_predaj:.3f} = {odvody:.2f} €

Čistý zisk po zdanení = Hrubý zisk − Daň − Odvody
                       = {hruby_zisk:.2f} € − {dan:.2f} € − {odvody:.2f} € = {cisty_zisk:.2f} €""")

        with st.expander(f"📋 Detail všetkých predajov za rok {zvoleny_rok}"):
            show = r_year.copy()
            show["Ticker"] = show["ticker"]
            show["Nákup"] = show["buy_date"].dt.strftime("%d.%m.%Y")
            show["Predaj"] = show["sell_date"].dt.strftime("%d.%m.%Y")
            show["Stav"] = show["exempt"].map({True: "Oslobodené", False: "Zdaňuje sa"})
            show = show[["Ticker", "Nákup", "Predaj", "shares", "cost", "proceeds", "gain", "held_days", "Stav"]]
            show.columns = ["Ticker", "Nákup", "Predaj", "Množstvo", "Náklady (€)", "Výnos (€)",
                             "Zisk/Strata (€)", "Dní držania", "Daňový stav"]
            st.dataframe(show, width="stretch")

            report_rows = [["Ticker", "Datum nakupu", "Datum predaja", "Mnozstvo", "Naklady EUR",
                             "Vynos EUR", "Zisk EUR", "Dni drzania", "Stav"]]
            for _, rr in r_year.iterrows():
                report_rows.append([rr["ticker"], rr["buy_date"].strftime("%d.%m.%Y"),
                                     rr["sell_date"].strftime("%d.%m.%Y"), f"{rr['shares']:.5f}",
                                     f"{rr['cost']:.2f}", f"{rr['proceeds']:.2f}", f"{rr['gain']:.2f}",
                                     str(rr["held_days"]), "Oslobodene" if rr["exempt"] else "Zdanuje sa"])
            st.download_button("📥 Stiahnuť detail predajov (CSV)",
                                data=rows_to_csv_sk(report_rows).encode("utf-8-sig"),
                                file_name=f"t212_predaje_{zvoleny_rok}.csv", mime="text/csv",
                                key=f"dl_predaje_{zvoleny_rok}")

        st.markdown("---")

    # =====================================================================
    # 2) ČO MÔŽEM PREDAŤ K DNEŠNÉMU DŇU
    # =====================================================================
    section_header(
        "🎯 Čo môžem predať k dnešnému dňu",
        "Toto je pohľad dopredu (nie za konkrétny rok). Zobrazuje VŠETKY tvoje aktuálne vlastnené balíčky "
        "(frakcie) danej akcie a ukáže, ktoré už splnili 365-dňový časový test (zelené – bez dane) "
        "a ktoré ešte nie (červené – zdanili by sa, keby si predal dnes).",
        "Čo je toto?"
    )

    zoznam_tickerov_all = sorted([t for t in all_lots.keys() if t and all_lots[t]])
    if not zoznam_tickerov_all:
        st.warning("V dátach sa nenašli žiadne aktuálne vlastnené akcie.")
    else:
        ponuka_pre_menu, mapovanie_tickerov = [], {}
        for t in zoznam_tickerov_all:
            full_company_name = name_map.get(t, "Spoločnosť z platformy")
            text_riadku = f"{t} - {full_company_name}"
            ponuka_pre_menu.append(text_riadku)
            mapovanie_tickerov[text_riadku] = t
        ponuka_pre_menu = sorted(set(ponuka_pre_menu))

        col1, col2 = st.columns(2)
        with col1:
            vybrany_text = st.selectbox("Vyber akciu z portfólia:", ponuka_pre_menu, key="sel_ticker_dnes")
        with col2:
            aktualna_cena = st.number_input("Aktuálna trhová cena za kus (EUR):", min_value=0.0, value=0.0,
                                             step=0.01, format="%.2f", key="cena_dnes")
        vybrany_ticker_pure = mapovanie_tickerov[vybrany_text]
        vybrany_nazov = name_map.get(vybrany_ticker_pure, "Spoločnosť z platformy")

        lots_ticker = all_lots.get(vybrany_ticker_pure, [])
        dfr = build_frakcie_table(lots_ticker, vybrany_ticker_pure, vybrany_nazov)

        celkovo_ks = dfr["Kusy"].sum()
        zelene = dfr[dfr["Stav"].str.contains("🟢")]
        cervene = dfr[dfr["Stav"].str.contains("🔴")]
        ks_zelene = zelene["Kusy"].sum()
        ks_cervene = cervene["Kusy"].sum()

        naklady_zelene = (zelene["Kusy"] * zelene["Cena/ks (€)"]).sum()
        hodnota_zelene = ks_zelene * aktualna_cena
        cisty_zisk_zelene = max(0.0, hodnota_zelene - naklady_zelene)

        naklady_cervene = (cervene["Kusy"] * cervene["Cena/ks (€)"]).sum()
        hodnota_cervene = ks_cervene * aktualna_cena
        zisk_cervene = max(0.0, hodnota_cervene - naklady_cervene)

        aktualny_rok = datetime.now().year
        uz_realizovane_tento_rok = 0.0
        if not realized_df.empty:
            tento_rok_df = realized_df[(realized_df["sell_year"] == aktualny_rok) & (realized_df["exempt"] == False)]
            uz_realizovane_tento_rok = max(0.0, tento_rok_df["gain"].sum())

        with st.expander("⚙️ Daňové nastavenia pre tento výpočet (predvyplnené aktuálnou legislatívou)"):
            c1, c2 = st.columns(2)
            with c1:
                uplatnit_oslob2 = st.checkbox("Uplatniť 500 € ročné oslobodenie (§9)", value=True, key="oslob_dnes")
                sadzba_dan2 = st.number_input("Sadzba dane z príjmu (%)", value=19.0, step=0.1,
                                               key="sadzba_dan_dnes") / 100
            with c2:
                sadzba_odvody2 = st.number_input(
                    "Zdravotné odvody (%)", value=get_zdravotne_odvody_sadzba(aktualny_rok) * 100, step=0.1,
                    key="sadzba_odv_dnes") / 100
                uz_vyuzite2 = st.number_input(
                    "Už využité z 500 € oslobodenia tento rok (€)", value=round(min(500.0, uz_realizovane_tento_rok), 2),
                    step=10.0, key="vyuzite_dnes",
                    help="Automaticky predvyplnené podľa tvojich už zrealizovaných zdaniteľných predajov "
                         "tento rok. Uprav, ak máš aj iné 'ostatné príjmy'.")
            st.caption(get_prah_info(aktualny_rok))

        _, dan_cervene, odvody_cervene, _ = spocitaj_dan_z_predaja(
            zisk_cervene, aktualny_rok, uplatnit_oslob2, uz_vyuzite2, sadzba_dan2, sadzba_odvody2)

        m1, m2, m3 = st.columns(3)
        m1.metric("📦 Celkovo vlastníš", f"{sk_num(celkovo_ks, 5)} ks")
        m2.metric("🟢 Môžeš predať bez dane", f"{sk_num(ks_zelene, 5)} ks",
                  help=f"Hodnota: {sk_num(hodnota_zelene)} € · Čistý zisk: {sk_num(cisty_zisk_zelene)} €")
        m3.metric("🔴 Ešte čaká na test", f"{sk_num(ks_cervene, 5)} ks",
                  help=f"Ak by si predal dnes: daň {sk_num(dan_cervene)} € + odvody {sk_num(odvody_cervene)} € "
                       f"= {sk_num(dan_cervene + odvody_cervene)} € štátu")

        if ks_zelene > 0:
            st.success(f"🔓 **{sk_num(ks_zelene, 5)} ks** môžeš predať IHNEĎ bez dane. "
                       f"Čistý zisk pri cene {aktualna_cena:.2f} €/ks: **{sk_num(cisty_zisk_zelene)} €**")
        if ks_cervene > 0:
            st.warning(f"🔒 **{sk_num(ks_cervene, 5)} ks** by sa pri predaji dnes zdanilo. "
                       f"Odviedol by si štátu **{sk_num(dan_cervene + odvody_cervene)} €** "
                       f"(daň {sk_num(dan_cervene)} € + odvody {sk_num(odvody_cervene)} €).")

        with st.expander(f"📋 Zobraziť všetky frakcie – {vybrany_ticker_pure} (zoradené od najstaršej)"):
            st.dataframe(farebna_tabulka(dfr), width="stretch")
            frakcie_csv_rows = [list(dfr.columns)] + dfr.astype(str).values.tolist()
            st.download_button("📥 Stiahnuť tento zoznam frakcií (CSV)",
                                data=rows_to_csv_sk(frakcie_csv_rows).encode("utf-8-sig"),
                                file_name=f"t212_frakcie_{vybrany_ticker_pure}.csv", mime="text/csv",
                                key="dl_frakcie_dnes")

# =========================================================================
# 💰 SEKCIA: DIVIDENDY
# =========================================================================
elif sekcia == "💰 Dividendy":
    section_header(
        "💰 Dividendy",
        "Brutto = dividenda pred zdanením. Zahraničná zrazená daň = to, čo už strhol štát emitenta "
        "(napr. USA) priamo pri výplate. Netto = suma, ktorá ti reálne prišla na účet. Moderné dividendy "
        "(zisk vytvorený od r. 2017) v SR NEPODLIEHAJÚ zdravotným odvodom – len zrážkovej dani "
        "(zvyčajne 7 %, pri zisku z r. 2024 bolo 10 %, pri nezmluvných štátoch 35 %).",
        "Čo je toto?"
    )

    if dividends_df.empty:
        st.info("V nahraných CSV sa nenašli žiadne dividendové platby.")
    else:
        spolocnosti = (dividends_df.groupby("Ticker_Clean")
                        .agg(Brutto=("Brutto", "sum"), Zrazena=("Zrazena_dan", "sum"), Netto=("Netto", "sum"))
                        .reset_index().sort_values("Brutto", ascending=False))
        spolocnosti["Názov"] = spolocnosti["Ticker_Clean"].map(lambda t: name_map.get(t, ""))
        spolocnosti = spolocnosti[["Ticker_Clean", "Názov", "Brutto", "Zrazena", "Netto"]]
        spolocnosti.columns = ["Ticker", "Názov", "Brutto (€)", "Zahr. zrazená daň (€)", "Netto (€)"]

        st.markdown("**📜 Prehľad podľa spoločností (celé obdobie)**")
        st.dataframe(spolocnosti, width="stretch")

        t1, t2, t3 = st.columns(3)
        t1.metric("Brutto spolu (celé obdobie)", f"{sk_num(dividends_df['Brutto'].sum())} €")
        t2.metric("Zahr. zrazená daň spolu", f"{sk_num(dividends_df['Zrazena_dan'].sum())} €")
        t3.metric("Netto spolu", f"{sk_num(dividends_df['Netto'].sum())} €")

        st.markdown("---")
        st.markdown("**📅 Filter podľa daňového roka**")
        roky_div = sorted(dividends_df["Rok"].unique(), reverse=True)
        zvoleny_rok_div = st.selectbox("Vyber rok:", ["Všetky roky"] + [str(r) for r in roky_div], key="rok_div")

        show_div = dividends_df if zvoleny_rok_div == "Všetky roky" else dividends_df[
            dividends_df["Rok"] == int(zvoleny_rok_div)]

        brutto_r = show_div["Brutto"].sum()
        zrazena_r = show_div["Zrazena_dan"].sum()

        with st.expander("⚙️ Daňové nastavenia pre výpočet dane z dividend"):
            sadzba_div = st.number_input(
                "Sadzba SK dane z dividend (%)", value=7.0, step=0.1, key="sadzba_div",
                help="7 % je štandardná sadzba pre zisk z rokov 2017-2023 a 2025+. Pri zisku vytvorenom "
                     "v roku 2024 bola sadzba 10 %. Pri dividendách z 'nezmluvných štátov' (daňové raje) "
                     "platí 35 %. Uprav podľa svojej konkrétnej situácie.") / 100

        dan_sk, zapocet, doplatok = spocitaj_dan_z_dividend(brutto_r, zrazena_r, sadzba_div)

        st.markdown(f"**💶 Daň za {zvoleny_rok_div}**")
        d1, d2, d3 = st.columns(3)
        d1.metric("Brutto dividendy", f"{sk_num(brutto_r)} €")
        d2.metric("SK daň (pred zápočtom)", f"{sk_num(dan_sk)} €",
                  help="Zdravotné odvody sa pri moderných dividendách (zisk 2017+) neplatia.")
        d3.metric("Na doplatenie v SR", f"{sk_num(doplatok)} €",
                  help=f"Zahraničná zrazená daň {sk_num(zrazena_r)} € sa započíta voči SK dani "
                       f"(započítaných {sk_num(zapocet)} €). Prípadný prebytok sa nevracia.")

        with st.expander("📋 Detail jednotlivých výplat"):
            display = show_div[["Time", "Ticker_Clean", "Brutto", "Zrazena_dan", "Netto"]].copy()
            display["Time"] = display["Time"].dt.strftime("%d.%m.%Y")
            display.columns = ["Dátum", "Ticker", "Brutto (€)", "Zrazená daň (€)", "Netto (€)"]
            st.dataframe(display, width="stretch")

            div_csv_rows = [["Datum", "Ticker", "Brutto EUR", "Zrazena dan EUR", "Netto EUR"]]
            for _, row in show_div.iterrows():
                div_csv_rows.append([row["Time"].strftime("%d.%m.%Y"), row["Ticker_Clean"],
                                      f"{row['Brutto']:.2f}", f"{row['Zrazena_dan']:.2f}", f"{row['Netto']:.2f}"])
            st.download_button("📥 Stiahnuť dividendy (CSV)",
                                data=rows_to_csv_sk(div_csv_rows).encode("utf-8-sig"),
                                file_name="t212_dividendy.csv", mime="text/csv", key="btn_export_dividendy")

# =========================================================================
# 💶 SEKCIA: ÚROKY
# =========================================================================
elif sekcia == "💶 Úroky":
    section_header(
        "💶 Úroky z nevloženej hotovosti",
        "Trading 212 platí úrok z hotovosti, ktorú máš na účte a nemáš zainvestovanú. Tento príjem sa "
        "v SR zdaňuje ako 'ostatný príjem' (§8) – rovnakou logikou a sadzbami ako predaj cenných "
        "papierov (19 %/25 %/30 %/35 % podľa výšky základu dane), ALE bez 365-dňového časového testu "
        "a bez 500 € oslobodenia (to platí len pre predaj cenných papierov).",
        "Čo je toto?"
    )

    if interest_df.empty:
        st.info("V nahraných CSV sa nenašli žiadne úrokové platby.")
    else:
        t1, t2 = st.columns(2)
        t1.metric("Úroky spolu (celé obdobie)", f"{sk_num(interest_df['Total'].sum())} €")
        t2.metric("Počet platieb", f"{len(interest_df)}")

        st.markdown("---")
        st.markdown("**📅 Filter podľa daňového roka**")
        roky_int = sorted(interest_df["Rok"].unique(), reverse=True)
        zvoleny_rok_int = st.selectbox("Vyber rok:", ["Všetky roky"] + [str(r) for r in roky_int], key="rok_int")

        show_int = interest_df if zvoleny_rok_int == "Všetky roky" else interest_df[
            interest_df["Rok"] == int(zvoleny_rok_int)]
        total_int = show_int["Total"].sum()

        rok_pre_sadzbu = int(zvoleny_rok_int) if zvoleny_rok_int != "Všetky roky" else datetime.now().year
        with st.expander("⚙️ Daňové nastavenia pre výpočet dane z úrokov"):
            sadzba_int = st.number_input("Sadzba dane z príjmu (%)", value=19.0, step=0.1, key="sadzba_int") / 100
            st.caption(get_prah_info(rok_pre_sadzbu))

        dan_int = round(max(0.0, total_int) * sadzba_int, 2)

        st.markdown(f"**💶 Daň za {zvoleny_rok_int}**")
        u1, u2 = st.columns(2)
        u1.metric("Prijaté úroky", f"{sk_num(total_int)} €")
        u2.metric("Odhadovaná daň", f"{sk_num(dan_int)} €")

        with st.expander("📋 Detail jednotlivých platieb"):
            display_i = show_int[["Time", "Total"]].copy()
            display_i["Time"] = display_i["Time"].dt.strftime("%d.%m.%Y")
            display_i.columns = ["Dátum", "Suma (€)"]
            st.dataframe(display_i, width="stretch")

            int_csv_rows = [["Datum", "Suma EUR"]]
            for _, row in show_int.iterrows():
                int_csv_rows.append([row["Time"].strftime("%d.%m.%Y"), f"{row['Total']:.2f}"])
            st.download_button("📥 Stiahnuť úroky (CSV)",
                                data=rows_to_csv_sk(int_csv_rows).encode("utf-8-sig"),
                                file_name="t212_uroky.csv", mime="text/csv", key="btn_export_uroky")
