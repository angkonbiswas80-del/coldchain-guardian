import sqlite3
import time
import random
from datetime import datetime

def save_to_db(device_id, temp, vib, current, lat, lon, status):
    try:
        conn = sqlite3.connect("cold_chain_iot.db")
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO telemetry_data (device_id, temperature, vibration, current_draw, latitude, longitude, status)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (device_id, temp, vib, current, lat, lon, status))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[ERROR] DB Write Failed: {e}")

def run_simulator():
    print("[INFO] Starting Global Multi-Device & GPS Fleet Simulator...")
    counter = 0
    
    # Base GPS Coordinatess (Dhaka and Chittagong routes)
    dhaka_lat, dhaka_lon = 23.8103, 90.4125
    ctg_lat, ctg_lon = 22.3569, 91.7832
    
    while True:
        counter += 1
        
        # ----------------------------------------------------
        # DEVICE 1: FREEZER_DHAKA_01 (Operating Nominally)
        # ----------------------------------------------------
        d1_temp = round(random.uniform(3.2, 4.5), 2)
        d1_vib = round(random.uniform(16.0, 20.0), 2)
        d1_current = round(random.uniform(1.2, 1.4), 2)
        # Simulate slight movement
        dhaka_lat += random.uniform(-0.001, 0.001)
        dhaka_lon += random.uniform(-0.001, 0.001)
        save_to_db("FREEZER_DHAKA_01", d1_temp, d1_vib, d1_current, dhaka_lat, dhaka_lon, "Healthy")
        
        # ----------------------------------------------------
        # DEVICE 2: FREEZER_CTG_02 (Simulating Degradation)
        # ----------------------------------------------------
        ctg_lat += random.uniform(-0.001, 0.001)
        ctg_lon += random.uniform(-0.001, 0.001)
        
        if counter < 10:
            d2_temp = round(random.uniform(4.0, 5.2), 2)
            d2_vib = round(random.uniform(18.0, 22.0), 2)
            d2_current = round(random.uniform(1.3, 1.5), 2)
            d2_status = "Healthy"
        elif counter < 20:
            d2_temp = round(random.uniform(6.2, 7.8), 2)
            d2_vib = round(random.uniform(35.0, 45.0), 2)
            d2_current = round(random.uniform(2.0, 2.5), 2)
            d2_status = "Warning"
        else:
            d2_temp = round(random.uniform(9.0, 12.5), 2)
            d2_vib = round(random.uniform(50.0, 65.0), 2)
            d2_current = round(random.uniform(2.8, 3.4), 2)
            d2_status = "Critical"
            if counter >= 25:
                counter = 0 # Reset asset 02 breakdown cycle
                
        save_to_db("FREEZER_CTG_02", d2_temp, d2_vib, d2_current, ctg_lat, ctg_lon, d2_status)
        
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Pushed Logs for Fleet: DHAKA_01 & CTG_02")
        time.sleep(3)

if __name__ == "__main__":
    run_simulator()