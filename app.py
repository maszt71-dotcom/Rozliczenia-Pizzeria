import streamlit as st
import pandas as pd
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from fpdf import FPDF
from datetime import datetime
from streamlit_cookies_manager import CookieManager
from supabase import create_client, Client

# --- 0. POŁĄCZENIE Z SUPABASE ---
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

# --- FUNKCJA BEZPIECZEŃSTWA DLA PDF ---
def pdf_safe(txt):
    if not txt: return ""
    rep = {"ą":"a","ć":"c","ę":"e","ł":"l","ń":"n","ó":"o","ś":"s","ź":"z","ż":"z",
           "Ą":"A","Ć":"C","Ę":"E","Ł":"L","Ń":"N","Ó":"O","Ś":"S","Ź":"Z","Ż":"Z"}
    t = str(txt)
    for k, v in rep.items(): t = t.replace(k, v)
    return t.encode('ascii', 'ignore').decode('ascii')

# --- FUNKCJA WYSYŁKI E-MAIL ---
def send_email_with_reports(pdf_data, csv_data):
    receiver_email = "mange929598@gmail.com"
    sender_email = "mange929598@gmail.com"
    password = "hlqivtidxgchoqdi" 

    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = receiver_email
    msg['Subject'] = f"Raport Pizzeria - {datetime.now().strftime('%d.%m.%Y %H:%M')}"
    msg.attach(MIMEText("W załączniku przesyłam aktualny raport finansowy.", 'plain'))

    part_pdf = MIMEBase('application', 'octet-stream')
    part_pdf.set_payload(pdf_data)
    encoders.encode_base64(part_pdf)
    part_pdf.add_header('Content-Disposition', f"attachment; filename=raport_{datetime.now().strftime('%d_%m')}.pdf")
    msg.attach(part_pdf)

    part_csv = MIMEBase('application', 'octet-stream')
    part_csv.set_payload(csv_data)
    encoders.encode_base64(part_csv)
    part_csv.add_header('Content-Disposition', f"attachment; filename=raport_{datetime.now().strftime('%d_%m')}.csv")
    msg.attach(part_csv)

    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(sender_email, password)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        st.sidebar.error(f"Błąd wysyłki: {e}")
        return False

# --- 1. KONFIGURACJA I LOGOWANIE ---
st.set_page_config(page_title="Pizzeria", layout="wide")
cookies = CookieManager()
if not cookies.ready(): st.stop()

if cookies.get("is_logged") != "true":
    st.title("🍕 Logowanie")
    haslo = st.text_input("Hasło", type="password")
    if st.button("Zaloguj"):
        if haslo == "dup@":
            cookies["is_logged"] = "true"
            cookies.save()
            st.rerun()
    st.stop()

# --- 2. DANE Z SUPABASE ---
def load_data():
    response = supabase.table("finanse").select("*").order("id").execute()
    if response.data:
        return pd.DataFrame(response.data)
    return pd.DataFrame(columns=['id', 'data', 'typ', 'kwota', 'opis', 'status', 'data_zdarzenia'])

def add_to_supabase(item):
    supabase.table("finanse").insert(item).execute()

data = load_data()

# --- OBLICZENIA ---
if not data.empty:
    data['kwota'] = pd.to_numeric(data['kwota'], errors='coerce').fillna(0)
    s_og = data[data['typ'] == 'Przychód ogólny']['kwota'].sum()
    s_wyd = data[data['typ'] == 'Wydatki gotówkowe']['kwota'].sum()
    s_got = data[data['typ'].astype(str).str.contains('Gotówka', na=False)]['kwota'].sum() - s_wyd
else:
    s_og, s_wyd, s_got = 0.0, 0.0, 0.0

# --- 3. GENERATOR PDF ---
def create_pdf(df, s_og, s_got, s_wyd):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", 'B', 16)
    pdf.cell(0, 10, pdf_safe(f"RAPORT PIZZERIA - {datetime.now().strftime('%d.%m.%Y')}"), ln=True, align='C')
    pdf.ln(10)
    pdf.set_font("Helvetica", 'B', 12)
    pdf.set_fill_color(212, 237, 218)
    pdf.cell(60, 10, pdf_safe(f"Przychod: {s_og:.2f} zl"), border=1, fill=True, align='C')
    if s_got < 0:
        pdf.set_fill_color(255, 0, 0); pdf.set_text_color(255, 255, 255)
    else:
        pdf.set_fill_color(255, 243, 205); pdf.set_text_color(0, 0, 0)
    pdf.cell(60, 10, pdf_safe(f"Gotowka: {s_got:.2f} zl"), border=1, fill=True, align='C')
    pdf.set_text_color(0, 0, 0); pdf.set_fill_color(248, 215, 218)
    pdf.cell(60, 10, pdf_safe(f"Wydatki: {s_wyd:.2f} zl"), border=1, ln=1, fill=True, align='C')
    pdf.ln(5)
    pdf.set_font("Helvetica", size=10)
    for _, row in df.iterrows():
        linia = f"{row['data_zdarzenia']} | {row['typ']} | {row['kwota']:.2f} zl | {row['opis']}"
        pdf.cell(0, 10, pdf_safe(linia), ln=True, border=1)
    return pdf.output(dest="S").encode("latin-1")

# --- 4. WIDOK GŁÓWNY ---
st.title("🍕 Rozliczenie Pizzerii")
c1, c2, c3 = st.columns(3)

if 's' not in st.session_state: st.session_state.s = ""
if 'os' not in st.session_state: st.session_state.os = None

with c1:
    st.markdown(f'<div style="background-color:#d4edda; padding:15px; border-radius:10px; text-align:center;">Przychód: <b>{s_og:,.2f} zł</b></div>', unsafe_allow_html=True)
    if st.button("➕ DODAJ", key="p"): st.session_state.s = "P" if st.session_state.s != "P" else ""; st.rerun()
    if st.session_state.s == "P":
        with st.container(border=True):
            d_p = st.date_input("Data zdarzenia", datetime.now(), key="date_p")
            kw_p = st.number_input("Kwota", value=None, step=1.0, key="p_v")
            if st.button("DODAJ", key="save_p", use_container_width=True, type="primary"):
                if kw_p:
                    add_to_supabase({'data': datetime.now().strftime("%d.%m %H:%M"), 'typ': 'Przychód ogólny', 'kwota': float(kw_p), 'opis': '', 'status': 'Aktywny', 'data_zdarzenia': d_p.strftime("%d.%m")})
                    st.session_state.s = ""; st.rerun()
            if st.button("⬅️ POWRÓT", key="back_p", use_container_width=True): st.session_state.s = ""; st.rerun()

with c2:
    got_bg = "#FF0000" if s_got < 0 else "#fff3cd"
    got_txt = "white" if s_got < 0 else "black"
    st.markdown(f'<div style="background-color:{got_bg}; color:{got_txt}; padding:15px; border-radius:10px; text-align:center;">Gotówka: <b>{s_got:,.2f} zł</b></div>', unsafe_allow_html=True)
    if st.button("➕ DODAJ", key="g"): st.session_state.s = "G" if st.session_state.s != "G" else ""; st.session_state.os = None; st.rerun()
    if st.session_state.s == "G":
        with st.container(border=True):
            osoby = ["🏢 Bufet", "🚗 Kierowca 1", "🚗 Kierowca 2", "🚗 Kierowca 3", "🚗 Kierowca 4"]
            for o in osoby:
                if st.button(o, key=f"os_{o}", use_container_width=True): st.session_state.os = o if st.session_state.os != o else None; st.rerun()
                if st.session_state.os == o:
                    with st.container(border=True):
                        st.markdown(f"Dla: **{o}**")
                        d_g = st.date_input("Data", datetime.now(), key=f"date_g_{o}")
                        kw_g = st.number_input("Kwota", value=None, step=1.0, key=f"g_v_{o}")
                        cs, cb = st.columns(2)
                        if cs.button("DODAJ", key=f"save_g_{o}", use_container_width=True, type="primary"):
                            if kw_g:
                                add_to_supabase({'data': datetime.now().strftime("%d.%m %H:%M"), 'typ': f"Gotówka - {o}", 'kwota': float(kw_g), 'opis': '', 'status': 'Aktywny', 'data_zdarzenia': d_g.strftime("%d.%m")})
                                st.session_state.s = ""; st.session_state.os = None; st.rerun()
                        if cb.button("COFNIJ", key=f"back_g_{o}", use_container_width=True): st.session_state.os = None; st.rerun()
            if st.button("⬅️ POWRÓT", key="back_g_main", use_container_width=True): st.session_state.s = ""; st.session_state.os = None; st.rerun()

with c3:
    st.markdown(f'<div style="background-color:#f8d7da; padding:15px; border-radius:10px; text-align:center;">Wydatki: <b>{s_wyd:,.2f} zł</b></div>', unsafe_allow_html=True)
    if st.button("➕ DODAJ", key="w"): st.session_state.s = "W" if st.session_state.s != "W" else ""; st.rerun()
    if st.session_state.s == "W":
        with st.container(border=True):
            d_w = st.date_input("Data zdarzenia", datetime.now(), key="date_w")
            kw_w = st.number_input("Kwota", value=None, step=1.0, key="w_v")
            op_w = st.text_input("Opis", key="desc_w")
            if st.button("DODAJ", key="save_w", use_container_width=True, type="primary"):
                if kw_w:
                    add_to_supabase({'data': datetime.now().strftime("%d.%m %H:%M"), 'typ': 'Wydatki gotówkowe', 'kwota': float(kw_w), 'opis': op_w, 'status': 'Aktywny', 'data_zdarzenia': d_w.strftime("%d.%m")})
                    st.session_state.s = ""; st.rerun()
            if st.button("⬅️ POWRÓT", key="back_w", use_container_width=True): st.session_state.s = ""; st.rerun()

# --- 5. PASEK BOCZNY ---
with st.sidebar:
    st.header("⚙️ Menu")
    if st.button("📧 WYŚLIJ RAPORT", use_container_width=True, type="primary"):
        pdf_file = create_pdf(data, s_og, s_got, s_wyd)
        csv_file = data.to_csv(index=False).encode('utf-8')
        if send_email_with_reports(pdf_file, csv_file): st.success("✅ Wysłano!")

    st.divider()
    # TRWAŁE USUWANIE LINII
    if 'selected_ids' in st.session_state and len(st.session_state.selected_ids) > 0:
        if st.button(f"🗑️ USUŃ LINIE ({len(st.session_state.selected_ids)})", use_container_width=True, type="primary"):
            st.session_state.ask_del_line = True
        
        if st.session_state.get('ask_del_line'):
            st.error("USUNĄĆ TRWALE?")
            cy, cn = st.columns(2)
            if cy.button("TAK", key="line_y"):
                for rid in st.session_state.selected_ids:
                    # TUTAJ ZMIANA: .delete() zamiast .update()
                    supabase.table("finanse").delete().eq("id", int(rid)).execute()
                st.session_state.ask_del_line = False
                st.session_state.selected_ids = []
                st.rerun()
            if cn.button("NIE", key="line_n"):
                st.session_state.ask_del_line = False; st.rerun()

    st.divider()
    st.download_button("📥 Pobierz CSV", data=data.to_csv(index=False).encode('utf-8'), file_name="raport.csv", use_container_width=True)
    st.download_button("📥 Pobierz PDF", data=create_pdf(data, s_og, s_got, s_wyd), file_name="raport.pdf", use_container_width=True)
    
    st.divider()
    if 'del_step' not in st.session_state: st.session_state.del_step = 0
    if st.button("🗑️ USUŃ CAŁĄ HISTORIĘ", use_container_width=True): st.session_state.del_step = 1
    if st.session_state.del_step >= 1:
        with st.container(border=True):
            st.warning("Potwierdź usunięcie CAŁOŚCI")
            check = st.checkbox("Zgadzam się")
            if check:
                if st.button("🔥 WYCZYŚĆ WSZYSTKO", use_container_width=True, type="primary"): st.session_state.del_step = 2
            if st.session_state.del_step == 2:
                st.error("CZY JESTEŚ PEWIEN?")
                ct, cn = st.columns(2)
                if ct.button("TAK", key="full_y", use_container_width=True):
                    # TUTAJ ZMIANA: .delete() zamiast .update()
                    for _, row in data.iterrows():
                        supabase.table("finanse").delete().eq("id", int(row['id'])).execute()
                    st.session_state.del_step = 0; st.rerun()
                if cn.button("NIE", key="full_n", use_container_width=True): st.session_state.del_step = 0; st.rerun()

    st.divider()
    if st.button("🔓 Wyloguj", use_container_width=True):
        cookies["is_logged"] = "false"; cookies.save(); st.rerun()

# --- 6. HISTORIA ---
st.divider()
st.subheader("Historia wpisów")
if not data.empty:
    df_display = data.iloc[::-1].copy()
    df_editor_input = df_display[["id", "data", "data_zdarzenia", "typ", "kwota", "opis", "status"]].copy()
    df_editor_input.insert(0, "Wybierz", False)
    
    res = st.data_editor(
        df_editor_input,
        column_config={
            "Wybierz": st.column_config.CheckboxColumn("Wybierz", width="small"),
            "id": None,
            "kwota": st.column_config.NumberColumn("Kwota", format="%.2f zł"),
        },
        disabled=["data", "data_zdarzenia", "typ", "kwota", "opis", "status"],
        hide_index=True, use_container_width=True, key="pizza_editor"
    )
    
    selected_ids = res[res["Wybierz"] == True]["id"].tolist()
    if 'selected_ids' not in st.session_state or st.session_state.selected_ids != selected_ids:
        st.session_state.selected_ids = selected_ids
        st.rerun()
else:
    st.info("Brak wpisów.")
