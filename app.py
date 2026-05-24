import os
import streamlit as st
import pandas as pd
import sqlite3
import bcrypt
import time
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import database_setup 
import threading
from iot_simulator import run_simulator 


threading.Thread(target=run_simulator, daemon=True).start()

if not os.path.exists("cold_chain_iot.db"):
    print("Database file not found, initializing database...")
    database_setup.init_db()
else:
    print("Database file found.")



st.set_page_config(page_title="Controlant-Grade Fleet Analytics", layout="wide")

# ----------------------------------------------------
# PURE DATABASE AUTHENTICATION (NO BYPASS)
# ----------------------------------------------------
def verify_login(username, password):
    try:
        conn = sqlite3.connect("cold_chain_iot.db")
        cursor = conn.cursor()
        cursor.execute("SELECT password_hash, role FROM users WHERE username = ?", (username,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            db_hash = row[0].encode('utf-8')
            if bcrypt.checkpw(password.encode('utf-8'), db_hash):
                return True, row[1]
        return False, None
    except Exception:
        return False, None

# ----------------------------------------------------
# REAL EMAIL ALERT via Gmail SMTP + secrets.toml
# ----------------------------------------------------
def send_email_alert(device_id, temperature, vibration, status):
    try:
        sender_email   = st.secrets["emails"]["sender_email"]
        app_password   = st.secrets["emails"]["app_password"]
        receiver_email = st.secrets["emails"]["receiver_email"]

        subject = f"🚨 CRITICAL BREACH ALERT: Asset {device_id}"

        body = f"""
        ⚠️ LOGISTICS COMPLIANCE ALERT - CRITICAL SYSTEM BREACH DETECTED
        ------------------------------------------------------------
        Asset Profile     : {device_id}
        Timestamp         : {time.strftime('%Y-%m-%d %H:%M:%S')}
        Core Temperature  : {temperature} °C
        Vibration Freq    : {vibration} Hz
        Current Status    : {status}

        CRITICAL ACTION REQUIRED:
        Core payload thermal protection is compromised.
        Dispatch emergency inspection or trigger backup
        refrigeration protocols immediately.
        ------------------------------------------------------------
        Automated Ingestion Pipeline, ColdChain IoT Product Suite.
        """

        msg = MIMEMultipart()
        msg['From']    = sender_email
        msg['To']      = receiver_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))

        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(sender_email, app_password)
            server.sendmail(sender_email, receiver_email, msg.as_string())

        print(f"[EMAIL SENT] Alert dispatched for {device_id}")

    except Exception as e:
        print(f"[EMAIL ERROR] Failed to send alert: {e}")
        st.toast(f"⚠️ Email dispatch failed: {e}", icon="❌")

# ----------------------------------------------------
# SESSION STATE INITIALIZATION
# ----------------------------------------------------
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
    st.session_state['user_role'] = None
    st.session_state['username'] = ""

if 'alert_fired_devices' not in st.session_state:
    st.session_state['alert_fired_devices'] = set()

# ----------------------------------------------------
# LOGIN USER INTERFACE
# ----------------------------------------------------
if not st.session_state['logged_in']:
    st.title("🔐 Enterprise Cold Chain Portal")
    st.subheader("Secure Logistics Management System")

    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submit_button = st.form_submit_button("Access Dashboard")

        if submit_button:
            success, role = verify_login(username, password)
            if success:
                st.session_state['logged_in'] = True
                st.session_state['user_role'] = role
                st.session_state['username'] = username
                st.success("Access Granted! Loading fleet manifest...")
                time.sleep(1)
                st.rerun()
            else:
                st.error("Invalid Username or Password.")

else:
    # ----------------------------------------------------
    # MAIN DASHBOARD PANEL (Post-Authentication)
    # ----------------------------------------------------
    def load_available_devices():
        try:
            conn = sqlite3.connect("cold_chain_iot.db")
            df = pd.read_sql_query("SELECT DISTINCT device_id FROM telemetry_data", conn)
            conn.close()
            return df['device_id'].tolist()
        except Exception:
            return []

    def load_device_data(selected_device):
        try:
            conn = sqlite3.connect("cold_chain_iot.db")
            query = f"SELECT * FROM telemetry_data WHERE device_id = '{selected_device}' ORDER BY id DESC LIMIT 50"
            df = pd.read_sql_query(query, conn)
            conn.close()
            return df.iloc[::-1]
        except Exception:
            return pd.DataFrame()

    st.title("❄️ Enterprise Cold Chain - Multi-Asset & GPS Dashboard")

    # Sidebar Profile Controls
    st.sidebar.markdown(f"**Current User:** `{st.session_state['username']}`")
    st.sidebar.markdown(f"**Role:** `{st.session_state['user_role']}`")

    if st.sidebar.button("Log Out"):
        st.session_state['logged_in'] = False
        st.session_state['user_role'] = None
        st.session_state['username'] = ""
        st.session_state['alert_fired_devices'].clear()
        st.rerun()

    st.sidebar.write("---")
    st.sidebar.header("🚚 Global Fleet Management")
    devices = load_available_devices()

    if devices:
        selected_device = st.sidebar.selectbox("Select Active Asset Unit", devices)
    else:
        selected_device = None
        st.sidebar.warning("No active devices found in storage pipeline.")

    placeholder = st.empty()

    if selected_device:
        while st.session_state['logged_in']:
            df = load_device_data(selected_device)

            if not df.empty:
                latest = df.iloc[-1]

                # State-controlled Anti-spam Alert Logic
                if latest['status'] == "Critical":
                    if selected_device not in st.session_state['alert_fired_devices']:
                        send_email_alert(
                            latest['device_id'],
                            latest['temperature'],
                            latest['vibration'],
                            latest['status']
                        )
                        st.session_state['alert_fired_devices'].add(selected_device)
                        # Toast notification on dashboard
                        st.toast(
                            f"🚨 Critical Alert! Email sent for {latest['device_id']}",
                            icon="🔴"
                        )
                elif latest['status'] in ("Healthy", "Warning"):
                    if selected_device in st.session_state['alert_fired_devices']:
                        st.session_state['alert_fired_devices'].remove(selected_device)

                with placeholder.container():
                    # KPI Summary Row
                    m1, m2, m3, m4 = st.columns(4)
                    m1.metric("Active Asset Profile",          str(latest['device_id']))
                    m2.metric("Core Compartment Temp",         f"{latest['temperature']} °C")
                    m3.metric("Compressor Vibration Frequency",f"{latest['vibration']} Hz")
                    m4.metric("Electrical Current Draw",       f"{latest['current_draw']} A")

                    # Status Warning Layers
                    if latest['status'] == "Healthy":
                        st.success(f"✅ SYSTEM STATUS: NOMINAL OPERATION ({latest['device_id']} is running within safe parameter thresholds)")
                    elif latest['status'] == "Warning":
                        st.warning("⚠️ PREDICTIVE ALERT: COMPRESSOR STRUCTURAL DEGRADATION DETECTED. Schedule physical audit within 48h.")
                    else:
                        st.error("🚨 CRITICAL BREACH: AUTOMATED EMAIL NOTIFICATION SENT TO MANAGEMENT TEAM!")

                    # Visualization Matrix
                    c1, c2 = st.columns(2)
                    with c1:
                        st.subheader("Thermal Integrity Tracking Stream")
                        st.line_chart(df.set_index('timestamp')['temperature'])

                        st.subheader("Real-time Active Fleet Location Link")
                        map_df = df[['latitude', 'longitude']].rename(
                            columns={'latitude': 'lat', 'longitude': 'lon'}
                        )
                        st.map(map_df, zoom=11)

                    with c2:
                        st.subheader("Mechanical System Stress Telemetry")
                        st.line_chart(df.set_index('timestamp')[['vibration', 'current_draw']])

                        st.subheader("Export Verified Compliance Records")
                        report_df = df[[
                            'timestamp', 'device_id', 'temperature',
                            'vibration', 'current_draw',
                            'latitude', 'longitude', 'status'
                        ]].iloc[::-1]

                        try:
                            excel_data = report_df.to_csv(index=False).encode('utf-8')
                            st.download_button(
                                label="📥 Download Verified Compliance Log (CSV)",
                                data=excel_data,
                                file_name=f"Compliance_Report_{selected_device}_{latest['timestamp']}.csv",
                                mime="text/csv",
                                use_container_width=True
                            )
                        except Exception as e:
                            st.error(f"Failed to generate spreadsheet manifest: {e}")

                    st.subheader("Raw Ingestion Manifest Logs")
                    st.dataframe(report_df, use_container_width=True)

            time.sleep(2)