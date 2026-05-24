import os
import threading
import sqlite3
import time
import random
import smtplib
import bcrypt
import pandas as pd
import streamlit as st
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import database_setup
from streamlit_autorefresh import st_autorefresh 

# ----------------------------------------------------
# DATABASE INIT
# ----------------------------------------------------
database_setup.init_db()

st.set_page_config(page_title="Controlant-Grade Fleet Analytics", layout="wide")
st_autorefresh(interval=3000, limit=None, key="fleet_refresh")

# ----------------------------------------------------
# ENV CONFIG - .env / secrets.toml / Render env vars
# ----------------------------------------------------
def get_env(key, fallback=None):
    val = os.environ.get(key)
    if val:
        return val
    try:
        section_map = {
            "SENDER_EMAIL":   ("emails", "sender_email"),
            "APP_PASSWORD":   ("emails", "app_password"),
            "RECEIVER_EMAIL": ("emails", "receiver_email"),
        }
        if key in section_map:
            section, skey = section_map[key]
            return st.secrets[section][skey]
    except Exception:
        pass
    try:
        env_paths = [
            os.path.join(os.path.dirname(__file__), ".env"),
            os.path.join(os.path.dirname(__file__), "Render", ".env"),
        ]
        for env_path in env_paths:
            if os.path.exists(env_path):
                with open(env_path) as f:
                    for line in f:
                        line = line.strip()
                        if "=" in line and not line.startswith("#"):
                            k, v = line.split("=", 1)
                            if k.strip() == key:
                                return v.strip()
    except Exception:
        pass
    return fallback

# ----------------------------------------------------
# BACKGROUND IOT SIMULATOR
# ----------------------------------------------------
def run_simulator_background():
    print("[INFO] Background fleet simulator started...")
    counter = 0
    dhaka_lat, dhaka_lon = 23.8103, 90.4125
    ctg_lat,   ctg_lon   = 22.3569, 91.7832

    while True:
        counter += 1

        # DEVICE 1: FREEZER_DHAKA_01
        d1_temp    = round(random.uniform(3.2,  4.5),  2)
        d1_vib     = round(random.uniform(16.0, 20.0), 2)
        d1_current = round(random.uniform(1.2,  1.4),  2)
        dhaka_lat += random.uniform(-0.001, 0.001)
        dhaka_lon += random.uniform(-0.001, 0.001)

        try:
            conn = sqlite3.connect("cold_chain_iot.db", check_same_thread=False)
            conn.execute("""
                INSERT INTO telemetry_data
                (device_id, temperature, vibration, current_draw, latitude, longitude, status)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, ("FREEZER_DHAKA_01", d1_temp, d1_vib, d1_current,
                  dhaka_lat, dhaka_lon, "Healthy"))
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"[SIM DB ERROR] {e}")

        # DEVICE 2: FREEZER_CTG_02
        ctg_lat += random.uniform(-0.001, 0.001)
        ctg_lon += random.uniform(-0.001, 0.001)

        if counter < 10:
            d2_temp, d2_vib, d2_current = (
                round(random.uniform(4.0,  5.2),  2),
                round(random.uniform(18.0, 22.0), 2),
                round(random.uniform(1.3,  1.5),  2),
            )
            d2_status = "Healthy"
        elif counter < 20:
            d2_temp, d2_vib, d2_current = (
                round(random.uniform(6.2,  7.8),  2),
                round(random.uniform(35.0, 45.0), 2),
                round(random.uniform(2.0,  2.5),  2),
            )
            d2_status = "Warning"
        else:
            d2_temp, d2_vib, d2_current = (
                round(random.uniform(9.0,  12.5), 2),
                round(random.uniform(50.0, 65.0), 2),
                round(random.uniform(2.8,  3.4),  2),
            )
            d2_status = "Critical"
            if counter >= 25:
                counter = 0

        try:
            conn = sqlite3.connect("cold_chain_iot.db", check_same_thread=False)
            conn.execute("""
                INSERT INTO telemetry_data
                (device_id, temperature, vibration, current_draw, latitude, longitude, status)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, ("FREEZER_CTG_02", d2_temp, d2_vib, d2_current,
                  ctg_lat, ctg_lon, d2_status))
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"[SIM DB ERROR] {e}")

        print(f"[{datetime.now().strftime('%H:%M:%S')}] Fleet data pushed.")
        time.sleep(3)


if 'simulator_started' not in st.session_state:
    st.session_state['simulator_started'] = True
    t = threading.Thread(target=run_simulator_background, daemon=True)
    t.start()

# ----------------------------------------------------
# DATABASE AUTHENTICATION
# ----------------------------------------------------
def verify_login(username, password):
    try:
        conn   = sqlite3.connect("cold_chain_iot.db")
        cursor = conn.cursor()
        cursor.execute(
            "SELECT password_hash, role FROM users WHERE username = ?",
            (username,)
        )
        row = cursor.fetchone()
        conn.close()
        if row:
            if bcrypt.checkpw(password.encode('utf-8'), row[0].encode('utf-8')):
                return True, row[1]
        return False, None
    except Exception as e:
        print(f"[AUTH ERROR] {e}")
        return False, None

# ----------------------------------------------------
# EMAIL ALERT
# ----------------------------------------------------
def send_email_alert(device_id, temperature, vibration, status):
    try:
        sender_email   = get_env("SENDER_EMAIL")
        app_password   = get_env("APP_PASSWORD")
        receiver_email = get_env("RECEIVER_EMAIL")

        if not all([sender_email, app_password, receiver_email]):
            print("[EMAIL ERROR] Missing email configuration.")
            st.toast("⚠️ Email config missing.", icon="❌")
            return

        subject = f"🚨 CRITICAL BREACH ALERT: Asset {device_id}"
        body    = f"""
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

        msg            = MIMEMultipart()
        msg['From']    = sender_email
        msg['To']      = receiver_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))

        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(sender_email, app_password)
            server.sendmail(sender_email, receiver_email, msg.as_string())

        print(f"[EMAIL SENT] Alert dispatched for {device_id}")

    except Exception as e:
        print(f"[EMAIL ERROR] {e}")
        st.toast(f"⚠️ Email dispatch failed: {e}", icon="❌")

# ----------------------------------------------------
# SESSION STATE
# ----------------------------------------------------
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
    st.session_state['user_role'] = None
    st.session_state['username']  = ""

if 'alert_fired_devices' not in st.session_state:
    st.session_state['alert_fired_devices'] = set()

# ----------------------------------------------------
# LOGIN UI
# ----------------------------------------------------
if not st.session_state['logged_in']:
    st.title("🔐 Enterprise Cold Chain Portal")
    st.subheader("Secure Logistics Management System")

    with st.form("login_form"):
        username      = st.text_input("Username")
        password      = st.text_input("Password", type="password")
        submit_button = st.form_submit_button("Access Dashboard")

        if submit_button:
            success, role = verify_login(username, password)
            if success:
                st.session_state['logged_in'] = True
                st.session_state['user_role'] = role
                st.session_state['username']  = username
                st.success("Access Granted! Loading fleet manifest...")
                time.sleep(1)
                st.rerun()
            else:
                st.error("Invalid Username or Password.")

# ----------------------------------------------------
# MAIN DASHBOARD
# ----------------------------------------------------
else:
    def load_available_devices():
        try:
            conn = sqlite3.connect("cold_chain_iot.db")
            df   = pd.read_sql_query(
                "SELECT DISTINCT device_id FROM telemetry_data", conn
            )
            conn.close()
            return df['device_id'].tolist()
        except Exception as e:
            print(f"[DB ERROR] {e}")
            return []

    def load_device_data(device):
        try:
            conn = sqlite3.connect("cold_chain_iot.db")
            df   = pd.read_sql_query(
                """SELECT * FROM telemetry_data
                   WHERE device_id = ?
                   ORDER BY id DESC LIMIT 50""",
                conn, params=(device,)
            )
            conn.close()
            return df.iloc[::-1]
        except Exception as e:
            print(f"[DB ERROR] {e}")
            return pd.DataFrame()

    # ---- Sidebar ----
    st.title("❄️ Enterprise Cold Chain - Multi-Asset & GPS Dashboard")
    st.sidebar.markdown(f"**Current User:** `{st.session_state['username']}`")
    st.sidebar.markdown(f"**Role:** `{st.session_state['user_role']}`")

    if st.sidebar.button("Log Out"):
        st.session_state['logged_in'] = False
        st.session_state['user_role'] = None
        st.session_state['username']  = ""
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

    # ---- Dashboard ----
    if selected_device:
        df = load_device_data(selected_device)

        if not df.empty:
            latest = df.iloc[-1]

            # Alert Logic
            if latest['status'] == "Critical":
                if selected_device not in st.session_state['alert_fired_devices']:
                    send_email_alert(
                        latest['device_id'],
                        latest['temperature'],
                        latest['vibration'],
                        latest['status']
                    )
                    st.session_state['alert_fired_devices'].add(selected_device)
                    st.toast(
                        f"🚨 Critical Alert! Email sent for {latest['device_id']}",
                        icon="🔴"
                    )
            elif latest['status'] in ("Healthy", "Warning"):
                if selected_device in st.session_state['alert_fired_devices']:
                    st.session_state['alert_fired_devices'].remove(selected_device)

            # KPI Row
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Active Asset Profile",           str(latest['device_id']))
            m2.metric("Core Compartment Temp",          f"{latest['temperature']} °C")
            m3.metric("Compressor Vibration Frequency", f"{latest['vibration']} Hz")
            m4.metric("Electrical Current Draw",        f"{latest['current_draw']} A")

            # Status Banner
            if latest['status'] == "Healthy":
                st.success(
                    f"✅ SYSTEM STATUS: NOMINAL OPERATION "
                    f"({latest['device_id']} running within safe thresholds)"
                )
            elif latest['status'] == "Warning":
                st.warning(
                    "⚠️ PREDICTIVE ALERT: COMPRESSOR STRUCTURAL DEGRADATION DETECTED. "
                    "Schedule physical audit within 48h."
                )
            else:
                st.error(
                    "🚨 CRITICAL BREACH: AUTOMATED EMAIL NOTIFICATION "
                    "SENT TO MANAGEMENT TEAM!"
                )

            # Charts
            c1, c2 = st.columns(2)
            with c1:
                st.subheader("Thermal Integrity Tracking Stream")
                st.line_chart(df.set_index('timestamp')['temperature'])

                st.subheader("Real-time Active Fleet Location")
                map_df = df[['latitude', 'longitude']].rename(
                    columns={'latitude': 'lat', 'longitude': 'lon'}
                )
                st.map(map_df, zoom=11)

            with c2:
                st.subheader("Mechanical System Stress Telemetry")
                st.line_chart(
                    df.set_index('timestamp')[['vibration', 'current_draw']]
                )

                st.subheader("Export Verified Compliance Records")
                report_df = df[[
                    'timestamp', 'device_id', 'temperature',
                    'vibration', 'current_draw',
                    'latitude', 'longitude', 'status'
                ]].iloc[::-1]

                try:
                    csv_data = report_df.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        label="📥 Download Verified Compliance Log (CSV)",
                        data=csv_data,
                        file_name=(
                            f"Compliance_Report_{selected_device}"
                            f"_{latest['timestamp']}.csv"
                        ),
                        mime="text/csv",
                        use_container_width=True
                    )
                except Exception as e:
                    st.error(f"Failed to generate report: {e}")

            st.subheader("Raw Ingestion Manifest Logs")
            st.dataframe(report_df, use_container_width=True)

        else:
            st.info("⏳ Waiting for device data... Please wait a few seconds.")