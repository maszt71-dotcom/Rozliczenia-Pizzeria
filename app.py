import streamlit as st
import pandas as pd
import smtplib
import base64
import hashlib
import hmac
import json
import time
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from fpdf import FPDF
from datetime import datetime
import pytz
from streamlit_cookies_manager import CookieManager
from supabase import create_client, Client

# --- 0. POŁĄCZENIE Z SUPABASE ---
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

DEFAULT_SECRETS = {
    "APP_PASSWORD": "dup@",
    "AUTH_COOKIE_SECRET": "dup@_sekret_cookie_2026",
    "REPORT_RECEIVER_EMAIL": "maszt71@gmail.com",
    "REPORT_SENDER_EMAIL": "mange989592@gmail.com",
    "REPORT_EMAIL_PASSWORD": "zfuodazqsegtekel",
}

def get_secret(name, default=None):
    try:
        return st.secrets.get(name, DEFAULT_SECRETS.get(name, default))
    except Exception:
        return DEFAULT_SECRETS.get(name, default)

def get_now():
    return datetime.now(pytz.timezone("Europe/Warsaw"))

# --- FUNKCJA BEZPIECZEŃSTWA DLA PDF ---
def pdf_safe(txt):
    if not txt:
        return ""
    rep = {
        "ą": "a", "ć": "c", "ę": "e", "ł": "l", "ń": "n", "ó": "o", "ś": "s", "ź": "z", "ż": "z",
        "Ą": "A", "Ć": "C", "Ę": "E", "Ł": "L", "Ń": "N", "Ó": "O", "Ś": "S", "Ź": "Z", "Ż": "Z"
    }
    t = str(txt)
    for k, v in rep.items():
        t = t.replace(k, v)
    return t.encode("ascii", "ignore").decode("ascii")

def parse_event_date(value):
    txt = str(value).strip()
    if not txt or txt.lower() in ("none", "nan", "nat"):
        return None
    for fmt in ("%d.%m.%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(txt, fmt).date()
        except ValueError:
            pass
    return None

def short_pdf_text(value, max_len=58):
    text = pdf_safe(value).replace("\n", " ").strip()
    return text if len(text) <= max_len else text[: max_len - 3] + "..."

def make_auth_token(ttl_seconds=60 * 60 * 12):
    secret = str(get_secret("AUTH_COOKIE_SECRET") or get_secret("APP_PASSWORD") or "")
    if not secret:
        return ""
    payload = {"logged": True, "exp": int(time.time()) + ttl_seconds}
    payload_raw = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    payload_b64 = base64.urlsafe_b64encode(payload_raw).decode("ascii")
    signature = hmac.new(secret.encode("utf-8"), payload_b64.encode("ascii"), hashlib.sha256).hexdigest()
    return f"{payload_b64}.{signature}"

def is_valid_auth_token(token):
    secret = str(get_secret("AUTH_COOKIE_SECRET") or get_secret("APP_PASSWORD") or "")
    if not token or not secret or "." not in str(token):
        return False
    payload_b64, signature = str(token).rsplit(".", 1)
    expected = hmac.new(secret.encode("utf-8"), payload_b64.encode("ascii"), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(signature, expected):
        return False
    try:
        payload = json.loads(base64.urlsafe_b64decode(payload_b64.encode("ascii")))
    except Exception:
        return False
    return bool(payload.get("logged")) and int(payload.get("exp", 0)) > int(time.time())

def check_secret_password(value, secret_name):
    expected = str(get_secret(secret_name) or "")
    return bool(expected) and hmac.compare_digest(str(value or ""), expected)

def insert_report_with_ids(date_from, date_to, total_income, entry_ids):
    payload = {
        "data_wygenerowania": get_now().isoformat(),
        "okres_od": date_from.strftime("%d.%m.%Y"),
        "okres_do": date_to.strftime("%d.%m.%Y"),
        "suma_przychodow": float(total_income),
        "entry_ids": [int(x) for x in entry_ids],
    }
    try:
        return supabase.table("raporty").insert(payload).execute()
    except Exception:
        payload.pop("entry_ids", None)
        st.warning("Tabela raporty nie ma kolumny entry_ids. Raport zapisano, ale archiwum będzie odtwarzane po datach.")
        return supabase.table("raporty").insert(payload).execute()

def load_report_rows(report_row):
    entry_ids = report_row.get("entry_ids", None)
    if isinstance(entry_ids, str):
        try:
            entry_ids = json.loads(entry_ids)
        except Exception:
            entry_ids = None

    if isinstance(entry_ids, list) and entry_ids:
        res = supabase.table("finanse").select("*").in_("id", [int(x) for x in entry_ids]).execute()
        return sort_df_by_data_zdarzenia(pd.DataFrame(res.data)) if res.data else pd.DataFrame()

    d_from_parsed = datetime.strptime(report_row["okres_od"], "%d.%m.%Y").date()
    d_to_parsed = datetime.strptime(report_row["okres_do"], "%d.%m.%Y").date()
    return sort_df_by_data_zdarzenia(filter_data_by_date_range(load_data(), d_from_parsed, d_to_parsed))

# --- POPRAWIONA I UPORZĄDKOWANA FUNKCJA WYSYŁKI E-MAIL ---
def clean_app_password(value):
    return str(value or "").replace(" ", "").strip()

def get_email_configs():
    configs = []
    
    # 1. Sprawdź najpierw ustawienia użytkownika w st.secrets
    secrets_receiver = st.secrets.get("REPORT_RECEIVER_EMAIL")
    secrets_sender = st.secrets.get("REPORT_SENDER_EMAIL")
    secrets_password = st.secrets.get("REPORT_EMAIL_PASSWORD")
    
    if secrets_receiver and secrets_sender and secrets_password:
        configs.append({
            "receiver": str(secrets_receiver).strip(),
            "sender": str(secrets_sender).strip(),
            "password": clean_app_password(secrets_password),
            "source": "Streamlit secrets"
        })
        
    # 2. Zawsze dodaj wartości domyślne jako rezerwę awaryjną
    configs.append({
        "receiver": DEFAULT_SECRETS["REPORT_RECEIVER_EMAIL"],
        "sender": DEFAULT_SECRETS["REPORT_SENDER_EMAIL"],
        "password": clean_app_password(DEFAULT_SECRETS["REPORT_EMAIL_PASSWORD"]),
        "source": "Kod aplikacji"
    })

    unique = []
    seen = set()
    for cfg in configs:
        key = (cfg["receiver"], cfg["sender"], cfg["password"])
        if cfg["receiver"] and cfg["sender"] and cfg["password"] and key not in seen:
            unique.append(cfg)
            seen.add(key)
    return unique

def has_email_config():
    return bool(get_email_configs())

def build_email_message(sender_email, receiver_email, pdf_data, csv_data):
    msg = MIMEMultipart()
    msg["From"] = sender_email
    msg["To"] = receiver_email
    msg["Subject"] = f"Raport Pizzeria - {get_now().strftime('%d.%m.%Y %H:%M')}"
    msg.attach(MIMEText("Automatyczny raport z systemu.", "plain"))

    for content, ext in [(pdf_data, "pdf"), (csv_data, "csv")]:
        part = MIMEBase("application", "octet-stream")
        part.set_payload(content)
        encoders.encode_base64(part)
        part.add_header("Content-Disposition", f"attachment; filename=raport.{ext}")
        msg.attach(part)
    return msg

def send_email_with_reports(pdf_data, csv_data):
    configs = get_email_configs()
    if not configs:
        st.error("Błąd: Kompletnie brakuje konfiguracji serwera pocztowego.")
        return False

    auth_failed_senders = set()
    
    for cfg in configs:
        try:
            msg = build_email_message(cfg["sender"], cfg["receiver"], pdf_data, csv_data)
            with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
                server.login(cfg["sender"], cfg["password"])
                server.send_message(msg)
            return True
        except smtplib.SMTPAuthenticationError:
            auth_failed_senders.add(cfg["sender"])
        except Exception:
            continue

    if auth_failed_senders:
        st.error(
            "Nie udało się wysłać maila: Gmail odrzucił hasło logowania konta nadawcy. "
            "Upewnij się, że wygenerowałeś 16-znakowe 'Hasło aplikacji' w ustawieniach konta Google dla konta: " 
            + ", ".join(sorted(auth_failed_senders))
        )
    else:
        st.error("Nie udało się połączyć z serwerem pocztowym SMTP. Sprawdź połączenie sieciowe lub konfigurację Gmail.")
    return False

# --- 1. KONFIGURACJA I LOGOWANIE ---
st.set_page_config(
    page_title="Pizzeria",
    layout="wide",
    initial_sidebar_state="expanded"
)

cookies = CookieManager()
if not cookies.ready():
    st.stop()

if not is_valid_auth_token(cookies.get("auth_token")):
    st.title("🍕 Logowanie")
    if not get_secret("APP_PASSWORD"):
        st.error("Brakuje APP_PASSWORD w st.secrets.")
        st.stop()

    with st.container(border=True):
        haslo = st.text_input("Hasło", type="password")
        if st.button("Zaloguj", type="primary", use_container_width=True):
            if check_secret_password(haslo, "APP_PASSWORD"):
                cookies["auth_token"] = make_auth_token()
                cookies.save()
                st.rerun()
            else:
                st.error("Nieprawidłowe hasło.")
    st.stop()

# --- 2. DANE Z SUPABASE ---
def load_data():
    res = supabase.table("finanse").select("*").order("id").execute()
    if res.data:
        df = pd.DataFrame(res.data)
    else:
        df = pd.DataFrame()

    expected_cols = ["id", "data", "typ", "kwota", "opis", "status", "data_zdarzenia"]
    defaults = {
        "id": None,
        "data": "",
        "typ": "",
        "kwota": 0.0,
        "opis": "",
        "status": "Aktywny",
        "data_zdarzenia": "",
    }
    for col in expected_cols:
        if col not in df.columns:
            df[col] = defaults[col]
            
    if not df.empty and "status" in df.columns:
        df["status"] = df["status"].fillna("Aktywny")
    return df

def load_archived_reports():
    res = supabase.table("raporty").select("*").order("id", desc=True).execute()
    expected_cols = ["id", "data_wygenerowania", "okres_od", "okres_do", "suma_przychodow", "entry_ids"]
    
    if res.data:
        df = pd.DataFrame(res.data)
        for col in expected_cols:
            if col not in df.columns:
                if col == "suma_przychodow":
                    df[col] = 0.0
                elif col == "entry_ids":
                    df[col] = None
                else:
                    df[col] = "Brak daty"
        df["suma_przychodow"] = pd.to_numeric(df["suma_przychodow"], errors="coerce").fillna(0.0)
        return df
        
    return pd.DataFrame(columns=expected_cols)

def filter_data_by_date_range(df, date_from, date_to):
    if df.empty:
        return df.copy()

    temp = df.copy()
    if "data_zdarzenia" not in temp.columns:
        temp["data_zdarzenia"] = ""
    temp["date_str"] = temp["data_zdarzenia"].astype(str).str.strip()

    parsed_dates = []
    for val in temp["date_str"]:
        parsed_dates.append(parse_event_date(val))

    temp["parsed_date"] = parsed_dates
    
    filtered = temp[
        (temp["parsed_date"].notna()) &
        (temp["parsed_date"] >= date_from) &
        (temp["parsed_date"] <= date_to)
    ].copy()

    return filtered.drop(columns=["parsed_date", "date_str"], errors="ignore")

CARRYOVER_TYPE = "Gotówka z przeniesienia"

def public_csv_data(df):
    export_df = df.copy()
    export_df = export_df.drop(columns=["status"], errors="ignore")
    return export_df.to_csv(index=False).encode("utf-8")

def calculate_range_sums(df):
    if df.empty:
        return 0.0, 0.0, 0.0

    temp = df.copy()
    if "kwota" not in temp.columns:
        temp["kwota"] = 0.0
    if "typ" not in temp.columns:
        temp["typ"] = ""
    temp["kwota"] = pd.to_numeric(temp["kwota"], errors="coerce").fillna(0)

    przychod = temp[temp["typ"] == "Przychód ogólny"]["kwota"].sum()
    wydatki = temp[temp["typ"] == "Wydatki gotówkowe"]["kwota"].sum()
    gotowka = temp[temp["typ"].astype(str).str.contains("Gotówka", na=False)]["kwota"].sum() - wydatki

    return przychod, gotowka, wydatki

def sort_df_by_data_zdarzenia(df):
    if df.empty:
        return df
    temp = df.copy()
    if "data_zdarzenia" not in temp.columns:
        temp["data_zdarzenia"] = ""
    if "id" not in temp.columns:
        temp["id"] = 0
    parsed = []
    for val in temp["data_zdarzenia"].astype(str).str.strip():
        parsed.append(parse_event_date(val) or datetime.min.date())
    temp["_sort_date"] = parsed
    temp = temp.sort_values(by=["_sort_date", "id"], ascending=[False, False])
    return temp.drop(columns=["_sort_date"], errors="ignore")


# Ładowanie danych
data = load_data()

def get_default_date_range(df):
    dates = []
    if not df.empty and "data_zdarzenia" in df.columns:
        for val in df["data_zdarzenia"].astype(str).str.strip():
            parsed = parse_event_date(val)
            if parsed:
                dates.append(parsed)
    if dates:
        latest = max(dates)
        return latest.replace(day=1), latest
    today = get_now().date()
    return today.replace(day=1), today

def get_latest_event_date(df):
    dates = []
    if not df.empty and "data_zdarzenia" in df.columns:
        for val in df["data_zdarzenia"].astype(str).str.strip():
            parsed = parse_event_date(val)
            if parsed:
                dates.append(parsed)
    return max(dates) if dates else get_now().date()


default_date_from, default_date_to = get_default_date_range(data)
df_current_all = data.copy()
current_month_start = get_now().date().replace(day=1)

# --- PASEK BOCZNY ---
with st.sidebar:
    st.header("⚙️ Menu")
    st.markdown("**Kwoty narastająco:**")
    cumulative_date_from = st.date_input("Pokaż od", value=current_month_start, key="cumulative_date_from")
    st.divider()

cumulative_date_to = get_latest_event_date(df_current_all)
if cumulative_date_from > cumulative_date_to:
    df_current = pd.DataFrame(columns=data.columns)
else:
    df_current = filter_data_by_date_range(df_current_all, cumulative_date_from, cumulative_date_to).copy()

df_active_calc = df_current.copy()
df_history = df_current.copy()

if not df_active_calc.empty:
    df_active_calc["kwota"] = pd.to_numeric(df_active_calc["kwota"], errors="coerce").fillna(0)
    s_og = df_active_calc[df_active_calc["typ"] == "Przychód ogólny"]["kwota"].sum()
    s_wyd = df_active_calc[df_active_calc["typ"] == "Wydatki gotówkowe"]["kwota"].sum()
    s_przeniesienie = df_active_calc[df_active_calc["typ"] == CARRYOVER_TYPE]["kwota"].sum()
    s_got = df_active_calc[df_active_calc["typ"].astype(str).str.contains("Gotówka", na=False)]["kwota"].sum() - s_wyd
else:
    s_og, s_wyd, s_got, s_przeniesienie = 0.0, 0.0, 0.0, 0.0

# --- 3. GENERATOR PDF ---
def infer_report_range(df):
    dates = []
    if not df.empty && "data_zdarzenia" in df.columns:
        for val in df["data_zdarzenia"].astype(str).str.strip():
            parsed = parse_event_date(val)
            if parsed:
                dates.append(parsed)
    if dates:
        return min(dates), max(dates)
    today = get_now().date()
    return today, today

def create_pdf(df, p, g, w, date_from=None, date_to=None):
    if date_from is None or date_to is None:
        inferred_from, inferred_to = infer_report_range(df)
        date_from = date_from or inferred_from
        date_to = date_to or inferred_to

    generated_at = get_now()
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, pdf_safe("RAPORT SZCZEGOLOWY"), ln=True, align="C")
    pdf.set_font("Helvetica", size=10)
    pdf.cell(0, 7, pdf_safe(f"Zakres raportu: {date_from.strftime('%d.%m.%Y')} - {date_to.strftime('%d.%m.%Y')}"), ln=True, align="C")
    pdf.cell(0, 7, pdf_safe(f"Wygenerowano: {generated_at.strftime('%d.%m.%Y %H:%M')}"), ln=True, align="C")
    pdf.ln(5)

    pdf.set_font("Helvetica", "B", 12)
    pdf.set_fill_color(212, 237, 218)
    pdf.cell(63, 10, pdf_safe(f"Przychod: {p:,.2f} zl"), border=1, fill=True, align="C")

    if g < 0:
        pdf.set_fill_color(255, 0, 0)
        pdf.set_text_color(255, 255, 255)
    else:
        pdf.set_fill_color(255, 243, 205)
        pdf.set_text_color(0, 0, 0)

    pdf.cell(64, 10, pdf_safe(f"Gotowka: {g:,.2f} zl"), border=1, fill=True, align="C")
    pdf.set_text_color(0, 0, 0)
    pdf.set_fill_color(248, 215, 218)
    pdf.cell(63, 10, pdf_safe(f"Wydatki: {w:,.2f} zl"), border=1, ln=1, fill=True, align="C")
    pdf.ln(10)

    pdf.set_font("Helvetica", "B", 10)
    pdf.set_fill_color(200, 200, 200)
    pdf.cell(28, 8, "Data", border=1, fill=True, align="C")
    pdf.cell(52, 8, "Typ", border=1, fill=True, align="C")
    pdf.cell(30, 8, "Kwota", border=1, fill=True, align="C")
    pdf.cell(80, 8, "Opis", border=1, ln=1, fill=True, align="C")

    pdf.set_font("Helvetica", size=9)
    fill = False

    df_to_print = df.copy()
    if "kwota" in df_to_print.columns:
        df_to_print["kwota"] = pd.to_numeric(df_to_print["kwota"], errors="coerce").fillna(0)

    for _, row in df_to_print.iterrows():
        if fill:
            pdf.set_fill_color(245, 245, 245)
        else:
            pdf.set_fill_color(255, 255, 255)

        data_txt = str(row.get("data_zdarzenia", ""))
        typ_txt = str(row.get("typ", ""))
        kwota_txt = f"{float(row.get('kwota', 0)):,.2f} zl"
        opis_txt = short_pdf_text(row.get("opis", ""))

        pdf.cell(28, 8, pdf_safe(data_txt), border=1, fill=True, align="C")
        pdf.cell(52, 8, pdf_safe(typ_txt), border=1, fill=True)
        pdf.cell(30, 8, pdf_safe(kwota_txt), border=1, fill=True, align="R")
        pdf.cell(80, 8, opis_txt, border=1, ln=1, fill=True)

        fill = not fill

    pdf_output = pdf.output(dest="S")
    if isinstance(pdf_output, (bytes, bytearray)):
        return bytes(pdf_output)
    return pdf_output.encode("latin-1")

# --- FUNKCJA STYLIZOWANIA KOLORÓW DLA WIERSZY W HISTORII ---
def style_row_by_type(row):
    typ = str(row["typ"])
    if CARRYOVER_TYPE in typ:
        return ["background-color: #dbeafe; color: black;"] * len(row)
    elif "Przychód ogólny" in typ:
        return ["background-color: #d4edda; color: black;"] * len(row)
    elif "Gotówka" in typ:
        return ["background-color: #fff3cd; color: black;"] * len(row)
    elif "Wydatki" in typ:
        return ["background-color: #f8d7da; color: black;"] * len(row)
    return [""] * len(row)

# --- 4. STANY SESJI ---
if "s" not in st.session_state:
    st.session_state.s = ""
if "os" not in st.session_state:
    st.session_state.os = None
if "selected_ids" not in st.session_state:
    st.session_state.selected_ids = []
if "lock_step" not in st.session_state:
    st.session_state.lock_step = 0
if "show_delete_confirm" not in st.session_state:
    st.session_state.show_delete_confirm = False
if "show_report_picker" not in st.session_state:
    st.session_state.show_report_picker = False
if "show_send_picker" not in st.session_state:
    st.session_state.show_send_picker = False
if "show_archive_picker" not in st.session_state:
    st.session_state.show_archive_picker = False

if "lock_confirm_1" not in st.session_state:
    st.session_state.lock_confirm_1 = False

# --- 5. WIDOK GŁÓWNY ---
st.title("🍕 Rozliczenie Pizzerii")
st.caption(f"Kwoty narastająco od {cumulative_date_from.strftime('%d.%m.%Y')} do {cumulative_date_to.strftime('%d.%m.%Y')}")

st.markdown(
    f'<div style="background-color:#dbeafe; padding:15px; border-radius:10px; text-align:center; margin-bottom:12px;">Gotówka z przeniesienia: <b>{s_przeniesienie:,.2f} zł</b></div>',
    unsafe_allow_html=True
)
if st.button("➕ DODAJ", key="zp"):
    st.session_state.s = "ZP" if st.session_state.s != "ZP" else ""
    st.rerun()

if st.session_state.s == "ZP":
    with st.container(border=True):
        d_zp = st.date_input("Data zdarzenia", get_now().date(), key="date_zp")
        kw_zp = st.number_input("Kwota", value=None, step=1.0, key="zp_v", placeholder="Wpisz kwotę")
        op_zp = st.text_input("Opis", key="desc_zp", placeholder="Opcjonalnie")
        if st.button("DODAJ", key="save_zp", use_container_width=True, type="primary"):
            if kw_zp is not None and kw_zp > 0:
                supabase.table("finanse").insert({
                    "data": get_now().strftime("%d.%m %H:%M"),
                    "typ": CARRYOVER_TYPE,
                    "kwota": float(kw_zp),
                    "opis": op_zp,
                    "status": "Aktywny",
                    "data_zdarzenia": d_zp.strftime("%d.%m.%Y")
                }).execute()
                st.session_state.s = ""
                st.rerun()

c1, c2, c3 = st.columns(3)

with c1:
    st.markdown(
        f'<div style="background-color:#d4edda; padding:15px; border-radius:10px; text-align:center;">Przychód: <b>{s_og:,.2f} zł</b></div>',
        unsafe_allow_html=True
    )
    if st.button("➕ DODAJ", key="p"):
        st.session_state.s = "P" if st.session_state.s != "P" else ""
        st.rerun()

    if st.session_state.s == "P":
        with st.container(border=True):
            d_p = st.date_input("Data zdarzenia", get_now().date(), key="date_p")
            kw_p = st.number_input("Kwota", value=None, step=1.0, key="p_v", placeholder="Wpisz kwotę")
            if st.button("DODAJ", key="save_p", use_container_width=True, type="primary"):
                if kw_p is not None and kw_p > 0:
                    supabase.table("finanse").insert({
                        "data": get_now().strftime("%d.%m %H:%M"),
                        "typ": "Przychód ogólny",
                        "kwota": float(kw_p),
                        "opis": "",
                        "status": "Aktywny",
                        "data_zdarzenia": d_p.strftime("%d.%m.%Y")
                    }).execute()
                    st.session_state.s = ""
                    st.rerun()

with c2:
    got_bg = "#FF0000" if s_got < 0 else "#fff3cd"
    got_txt = "white" if s_got < 0 else "black"
    st.markdown(
        f'<div style="background-color:{got_bg}; color:{got_txt}; padding:15px; border-radius:10px; text-align:center;">Gotówka: <b>{s_got:,.2f} zł</b></div>',
        unsafe_allow_html=True
    )
    if st.button("➕ DODAJ", key="g"):
        st.session_state.s = "G" if st.session_state.s != "G" else ""
        st.session_state.os = None
        st.rerun()

    if st.session_state.s == "G":
        with st.container(border=True):
            osoby = ["🏢 Bufet", "🚗 Kierowca 1", "🚗 Kierowca 2", "🚗 Kierowca 3", "🚗 Kierowca 4"]
            for o in osoby:
                if st.button(o, key=f"os_{o}", use_container_width=True):
                    st.session_state.os = o if st.session_state.os != o else None
                    st.rerun()

                if st.session_state.os == o:
                    with st.container(border=True):
                        st.markdown(f"Dla: **{o}**")
                        d_g = st.date_input("Data", get_now().date(), key=f"date_g_{o}")
                        kw_g = st.number_input("Kwota", value=None, step=1.0, key=f"g_v_{o}", placeholder="Wpisz kwotę")
                        if st.button("DODAJ", key=f"save_g_{o}", use_container_width=True, type="primary"):
                            if kw_g is not None and kw_g > 0:
                                supabase.table("finanse").insert({
                                    "data": get_now().strftime("%d.%m %H:%M"),
                                    "typ": f"Gotówka - {o}",
                                    "kwota": float(kw_g),
                                    "opis": "",
                                    "status": "Aktywny",
                                    "data_zdarzenia": d_g.strftime("%d.%m.%Y")
                                }).execute()
                                st.session_state.s = ""
                                st.session_state.os = None
                                st.rerun()

with c3:
    st.markdown(
        f'<div style="background-color:#f8d7da; padding:15px; border-radius:10px; text-align:center;">Wydatki: <b>{s_wyd:,.2f} zł</b></div>',
        unsafe_allow_html=True
    )
    if st.button("➕ DODAJ", key="w"):
        st.session_state.s = "W" if st.session_state.s != "W" else ""
        st.rerun()

    if st.session_state.s == "W":
        with st.container(border=True):
            d_w = st.date_input("Data zdarzenia", get_now().date(), key="date_w")
            kw_w = st.number_input("Kwota", value=None, step=1.0, key="w_v", placeholder="Wpisz kwotę")
            op_w = st.text_input("Opis", key="desc_w")
            if st.button("DODAJ", key="save_w
