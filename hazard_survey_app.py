# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point
from streamlit_folium import st_folium
import folium
from pathlib import Path
from datetime import datetime, date
import os, smtplib, re, zipfile
from email.message import EmailMessage
from docx import Document
from fpdf import FPDF

# --- Configuration ---
BASE_DIR = Path("C:/Temp/kzn")
SAVE_DIR = BASE_DIR / "Responses"
SAVE_DIR.mkdir(parents=True, exist_ok=True)
MASTER_CSV = BASE_DIR / "all_submissions.csv"
EXCEL_PATH = Path("RiskAssessmentTool.xlsm")
TOPOJSON_PATH = Path("KZN_wards_topo.json")  # Optimized TopoJSON file

# --- Load from Streamlit Secrets ---
EMAIL_ADDRESS = st.secrets["EMAIL_ADDRESS"]
EMAIL_PASSWORD = st.secrets["EMAIL_PASSWORD"]
APP_PASSWORD = st.secrets.get("APP_PASSWORD", "kzn!23@")
ADMIN_PASSWORD = st.secrets.get("ADMIN_PASSWORD", "kzn!23&")
ADMIN_EMAILS = [st.secrets.get("ADMIN_EMAIL", EMAIL_ADDRESS), "dingaanm@gmail.com"]

LOGO_PATH = "Logo.png"
SRK_LOGO_PATH = "SRK_Logo.png"

# --- Setup ---
def ensure_save_dir():
    SAVE_DIR.mkdir(parents=True, exist_ok=True)
    MASTER_CSV.parent.mkdir(parents=True, exist_ok=True)
ensure_save_dir()

def safe_filename(name):
    return re.sub(r'[^A-Za-z0-9_-]', '_', name)

# --- Authentication ---
def password_protection():
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False
    password = st.text_input("Enter password to access the app:", type="password")
    if st.button("Login"):
        if password == APP_PASSWORD:
            st.session_state["authenticated"] = True
            st.success("Access granted. Please continue.")
            st.rerun()
        else:
            st.error("Incorrect password.")

if not st.session_state.get("authenticated", False):
    st.title("KZN Hazard Risk Assessment Survey - Login")
    password_protection()
    st.stop()

# --- Load Hazards ---
@st.cache_data(show_spinner=False, ttl=3600)
def load_hazards():
    df = pd.read_excel(EXCEL_PATH, sheet_name="Hazard information", skiprows=1)
    return df.iloc[:, 0].dropna().tolist()

# --- Email Sending ---
def send_email(subject, body, to_emails, attachments):
    try:
        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = EMAIL_ADDRESS
        msg["To"] = ", ".join(to_emails)
        msg.set_content(body)
        for attachment in attachments:
            with open(attachment, "rb") as f:
                file_data = f.read()
                msg.add_attachment(file_data, maintype="application", subtype="octet-stream", filename=Path(attachment).name)
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            smtp.send_message(msg)
        st.success(f"Email sent to {to_emails}!")
    except Exception as e:
        st.error(f"Failed to send email: {e}")

# --- Save Responses ---
def append_to_master_csv(df):
    df.to_csv(MASTER_CSV, mode="a", header=not MASTER_CSV.exists(), index=False)

def save_responses(responses, name, uid, email, date_filled, district_municipality=None, local_municipality=None, extra_info=None):
    ensure_save_dir()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base_filename = f"{safe_filename(uid)}_{safe_filename(name)}_{timestamp}"
    csv_path = SAVE_DIR / f"{base_filename}.csv"
    pdf_path = SAVE_DIR / f"{base_filename}.pdf"
    docx_path = SAVE_DIR / f"{base_filename}.docx"

    df = pd.DataFrame(responses)
    df.insert(0, "Respondent Name", name)
    df.insert(1, "District Municipality", district_municipality)
    df.insert(2, "Local Municipality", local_municipality)
    df.insert(3, "UID", uid)
    df.insert(4, "Email", email)
    df.insert(5, "Extra Info", extra_info)
    df.insert(6, "Date", date_filled)
    df.to_csv(csv_path, index=False)
    append_to_master_csv(df)

    # DOCX
    doc = Document()
    doc.add_heading("KZN Hazard Risk Assessment Survey", 0)
    doc.add_paragraph(f"Name: {name}")
    doc.add_paragraph(f"District Municipality: {district_municipality}")
    doc.add_paragraph(f"Local Municipality: {local_municipality}")
    doc.add_paragraph(f"UID: {uid}")
    doc.add_paragraph(f"Email: {email}")
    doc.add_paragraph(f"Extra Info: {extra_info}")
    doc.add_paragraph(f"Date: {date_filled}")
    doc.add_paragraph("---")
    for _, row in df.iterrows():
        doc.add_paragraph(f"Hazard: {row['Hazard']} | Question: {row['Question']} | Response: {row['Response']}")
    doc.save(docx_path)

    # PDF
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(200, 10, txt="KZN Hazard Risk Assessment Survey", ln=True, align="C")
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt=f"Name: {name}", ln=True)
    pdf.cell(200, 10, txt=f"District Municipality: {district_municipality}", ln=True)
    pdf.cell(200, 10, txt=f"Local Municipality: {local_municipality}", ln=True)
    pdf.cell(200, 10, txt=f"UID: {uid}", ln=True)
    pdf.cell(200, 10, txt=f"Email: {email}", ln=True)
    pdf.multi_cell(0, 10, txt=f"Extra Info: {extra_info}")
    pdf.cell(200, 10, txt=f"Date: {date_filled}", ln=True)
    pdf.ln(5)
    for _, row in df.iterrows():
        pdf.multi_cell(0, 10, txt=f"Hazard: {row['Hazard']} | Question: {row['Question']} | Response: {row['Response']}")
    pdf.output(pdf_path)

    return csv_path, docx_path, pdf_path

# --- Create ZIP ---
def create_zip(local_municipality, files):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    zip_name = f"{safe_filename(local_municipality)}_{timestamp}.zip"
    zip_path = SAVE_DIR / zip_name
    with zipfile.ZipFile(zip_path, "w") as zipf:
        for file in files:
            zipf.write(file, os.path.basename(file))
    return zip_path

# --- Hazard Questions ---
questions_with_descriptions = {
    "Has this hazard occurred in the past?": ["0 - No chance", "1 - Potential", "2 - Once", "3 - Rarely", "4 - Regularly", "5 - Multiple times/year"],
    "How frequently does it occur?": ["0 - Unknown", "1 - Decreasing", "2 - Stable", "3 - Slightly increasing", "4 - Increasing", "5 - Rapidly increasing"],
    "What is the typical duration of the hazard?": ["0 - Unknown", "1 - Minutes", "2 - Hours", "3 - Days", "4 - Weeks", "5 - Months"],
    "What is the area of impact?": ["0 - None", "1 - Single property", "2 - Single Ward", "3 - Few wards", "4 - Entire municipality", "5 - Larger than municipality"],
    "What is the impact on people?": ["0 - None", "1 - Low impact", "2 - Minor injuries", "3 - Serious injuries", "4 - Fatalities (confined)", "5 - Multiple fatalities"],
    "What is the impact on infrastructure and services?": ["0 - None", "1 - Minor damage", "2 - Some damage", "3 - Medium damage", "4 - Serious damage", "5 - Total disruption"],
    "What is the impact on the environment?": ["0 - None", "1 - Minor effects", "2 - Moderate effects", "3 - Severe effects", "4 - Wide severe effects", "5 - Total destruction"],
    "What is the level of economic disruption?": ["0 - None", "1 - Some disruption", "2 - Medium", "3 - Severe short-term", "4 - Severe long-term", "5 - Total stop"],
    "How predictable is the hazard?": ["0 - Not applicable", "1 - Effective early warning", "3 - Partially predictable", "5 - No early warning"],
    "What is the urgency or priority level?": ["0 - None", "1 - Low", "2 - Medium", "3 - Medium-high", "4 - High", "5 - Very high"]
}

def build_hazard_questions(hazards_to_ask):
    responses = []
    for hazard in hazards_to_ask:
        st.markdown(f"### {hazard}")
        for q, opts in questions_with_descriptions.items():
            response = st.radio(q, opts, key=f"{hazard}_{q}")
            responses.append({"Hazard": hazard, "Question": q, "Response": response})
    return responses

# --- Map Display ---
def display_map():
    m = folium.Map(location=[-29.5, 31.1], zoom_start=7)
    folium.TopoJson(
        data=open(TOPOJSON_PATH),
        object_path="objects.KZN_wards",
        style_function=lambda x: {"fillColor": "#3186cc", "color": "black", "weight": 1, "fillOpacity": 0.4},
        highlight_function=lambda x: {"fillColor": "#ffcc00", "color": "black", "weight": 2, "fillOpacity": 0.7},
        tooltip=folium.GeoJsonTooltip(fields=["UID"], aliases=["UID:"], sticky=True)
    ).add_to(m)
    return st_folium(m, height=700, width=1000)

# --- Survey ---
def run_survey():
    st.title("KZN Hazard Risk Assessment Survey")
    hazards = load_hazards()
    map_data = display_map()

    clicked_uid = map_data.get("last_active_drawing", {}).get("properties", {}).get("UID", "")
    if clicked_uid:
        st.session_state["selected_uid"] = clicked_uid

    uid_display = st.session_state.get("selected_uid", "")
    if uid_display:
        st.success(f"Selected UID: {uid_display}")

    st.subheader("Select Applicable Hazards")
    selected = st.multiselect("Choose hazards:", hazards)
    custom = st.text_input("Other hazard") if st.checkbox("Add custom hazard") else ""

    if selected or custom:
        if "active_tab" not in st.session_state:
            st.session_state.active_tab = "Respondent Info"

        if st.session_state.active_tab == "Respondent Info":
            st.subheader("Respondent Info")
            st.session_state["name"] = st.text_input("Full Name", st.session_state.get("name", ""))
            st.session_state["district_municipality"] = st.text_input("District Municipality", st.session_state.get("district_municipality", ""))
            st.session_state["local_municipality"] = st.text_input("Local Municipality", st.session_state.get("local_municipality", ""))
            st.session_state["final_uid"] = uid_display or st.text_input("UID (if not using map)", st.session_state.get("final_uid", ""))
            st.session_state["today"] = st.date_input("Date", value=st.session_state.get("today", date.today()))
            st.session_state["user_email"] = st.text_input("Your Email", st.session_state.get("user_email", ""))
            st.session_state["extra_info"] = st.text_area("Any extra information", st.session_state.get("extra_info", ""))

            if st.button("Go to Hazard Questions"):
                st.session_state.active_tab = "Hazard Risk Evaluation"
                st.rerun()

        elif st.session_state.active_tab == "Hazard Risk Evaluation":
            st.subheader("Hazard Risk Evaluation")
            hazards_to_ask = selected + ([custom] if custom else [])
            with st.form("hazard_form"):
                responses = build_hazard_questions(hazards_to_ask)
                submit = st.form_submit_button("Submit Survey")
                if submit:
                    if not st.session_state.get("name") or not st.session_state.get("final_uid"):
                        st.error("Please fill in your name and UID.")
                    else:
                        csv_file, doc_file, pdf_file = save_responses(
                            responses,
                            st.session_state["name"],
                            st.session_state["final_uid"],
                            st.session_state["user_email"],
                            st.session_state["today"],
                            st.session_state["district_municipality"],
                            st.session_state["local_municipality"],
                            st.session_state["extra_info"]
                        )
                        zip_file = create_zip(st.session_state["local_municipality"], [csv_file, doc_file, pdf_file])
                        st.session_state["files_saved"] = (csv_file, doc_file, pdf_file, zip_file)
                        st.success(f"Survey submitted successfully! Files saved in: {SAVE_DIR}")

                        if st.session_state["user_email"]:
                            send_email(
                                "Your KZN Hazard Survey Submission",
                                "Thank you for completing the survey. Your files are attached.",
                                [st.session_state["user_email"]],
                                [zip_file]
                            )
                        send_email(
                            "New KZN Hazard Survey Submission",
                            "A new survey has been submitted. See attached ZIP file.",
                            ADMIN_EMAILS,
                            [zip_file]
                        )

        if "files_saved" in st.session_state:
            csv_file, doc_file, pdf_file, zip_file = st.session_state["files_saved"]
            with open(csv_file, "rb") as f:
                st.download_button("Download CSV", f, file_name=os.path.basename(csv_file), mime="text/csv")
            with open(doc_file, "rb") as f:
                st.download_button("Download DOCX", f, file_name=os.path.basename(doc_file),
                                   mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
            with open(pdf_file, "rb") as f:
                st.download_button("Download PDF", f, file_name=os.path.basename(pdf_file), mime="application/pdf")
            with open(zip_file, "rb") as zf:
                st.download_button("Download All (ZIP)", zf, file_name=os.path.basename(zip_file), mime="application/zip")

# --- Main App ---
st.set_page_config(page_title="KZN Hazard Risk Assessment", layout="wide")
st.markdown("<style>div.block-container{padding-top: 1rem;}</style>", unsafe_allow_html=True)

menu = st.sidebar.radio("Navigation", ["Survey", "Admin Dashboard"])

if os.path.exists(LOGO_PATH): st.sidebar.image(LOGO_PATH, width=180)
if os.path.exists(SRK_LOGO_PATH): st.sidebar.image(SRK_LOGO_PATH, width=160)

st.sidebar.markdown(
    "<small><i>Disclaimer: The software is developed by Dingaan Mahlangu and should not be used without prior permission.</i></small>",
    unsafe_allow_html=True
)

if menu == "Survey":
    run_survey()
elif menu == "Admin Dashboard":
    st.title("Admin Dashboard - KZN Hazard Survey")
    if "admin_authenticated" not in st.session_state:
        st.session_state["admin_authenticated"] = False
    if not st.session_state["admin_authenticated"]:
        admin_password = st.text_input("Enter Admin Password:", type="password")
        if st.button("Login as Admin"):
            if admin_password == ADMIN_PASSWORD:
                st.session_state["admin_authenticated"] = True
                st.success("Admin Access Granted.")
                st.rerun()
            else:
                st.error("Incorrect Admin Password.")
        st.stop()
    if MASTER_CSV.exists():
        df = pd.read_csv(MASTER_CSV)
        st.dataframe(df)
        st.download_button("Download CSV", df.to_csv(index=False).encode("utf-8"),
                           file_name="all_submissions.csv", mime="text/csv")
    else:
        st.warning("No submissions found.")
