from flask import Flask, jsonify, render_template, send_file
from flask_cors import CORS
import serial
import serial.tools.list_ports
import threading
import json
import time
import os
import re
import sqlite3

# ================= CONFIG =================
SERIAL_PORT = "COM3"      # Change to your port
BAUD_RATE = 115200
DB_PATH = os.path.join(os.path.dirname(__file__), "telemetry.db")

# ================= APP =================
app = Flask(__name__, template_folder='template')
CORS(app)

latest_data = {}
flight_data = []
serial_connected = False

# ================= DATABASE =================
def init_db():
    """Initialize SQLite database"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS telemetry (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp INTEGER,
            altitude REAL,
            ax REAL, ay REAL, az REAL,
            gx REAL, gy REAL, gz REAL,
            launched BOOLEAN,
            ejected BOOLEAN,
            sim BOOLEAN,
            raw_json TEXT,
            received_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()
    print("Database initialized at:", DB_PATH)

def save_to_db(data):
    """Save telemetry packet to database"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO telemetry (timestamp, altitude, ax, ay, az, gx, gy, gz, launched, ejected, sim, raw_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            data.get('ts', 0),
            data.get('alt', 0),
            data.get('ax', 0), data.get('ay', 0), data.get('az', 0),
            data.get('gx', 0), data.get('gy', 0), data.get('gz', 0),
            data.get('launched', False),
            data.get('ejected', False),
            data.get('sim', False),
            json.dumps(data)
        ))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"DB Error: {e}")

def load_from_db(limit=1000):
    """Load telemetry data from database"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT raw_json FROM telemetry ORDER BY id DESC LIMIT ?
        ''', (limit,))
        rows = cursor.fetchall()
        conn.close()
        return [json.loads(row[0]) for row in reversed(rows)]
    except Exception as e:
        print(f"DB Load Error: {e}")
        return []


# ================= HELPER FUNCTIONS =================
def list_available_ports():
    ports = serial.tools.list_ports.comports()
    return [port.device for port in ports]

# ================= SERIAL THREAD =================
def read_serial():
    global latest_data, flight_data, serial_connected

    print(f"🔄 Serial thread started. Target: {SERIAL_PORT}")

    while True:
        try:
            if not serial_connected:
                available_ports = list_available_ports()
                if SERIAL_PORT in available_ports:
                    ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
                    serial_connected = True
                    print(f"✅ Serial connected on {SERIAL_PORT}")
                else:
                    # Optional: Auto-detect if COM7 is missing but others exist?
                    # For now just wait for COM7
                    time.sleep(2)
                    continue

            while serial_connected:
                try:
                    line = ser.readline().decode("utf-8", errors="ignore").strip()

                    if not line:
                        continue
                    
                    # Log every line we receive for debugging
                    print(f"RAW LINE: {repr(line)}")
                    
                    # Try to find JSON in the line (handles noisy serial)
                    match = re.search(r'(\{.*\})', line)
                    if match:
                        print(f"DEBUG: Found potential JSON: {match.group(1)}")
                        try:
                            json_str = match.group(1)
                            data = json.loads(json_str)
                            
                            latest_data = data
                            flight_data.append(data)
                            
                            # Save to database
                            save_to_db(data)

                            if len(flight_data) > 5000:
                                flight_data.pop(0)
                        except Exception as parse_e:
                            print(f"⚠️ JSON Parse error on '{match.group(1)}': {parse_e}")
                    elif line.startswith("RSSI"):
                        continue
                    else:
                        # Log non-JSON lines if they look interesting (optional)
                        # print(f"RAW: {line}")
                        pass

                except serial.SerialException as e:
                    print(f"❌ Serial connection lost: {e}")
                    serial_connected = False
                    ser.close()
                except Exception as e:
                    print(f"⚠️ Parse error on line '{line}': {e}")

        except Exception as e:
            print(f"🛑 Serial thread error: {e}")
            serial_connected = False
            time.sleep(2)

# ================= API ROUTES =================

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/telemetry", methods=["GET"])
def telemetry():
    return jsonify(latest_data)

@app.route("/telemetry/all", methods=["GET"])
def telemetry_all():
    return jsonify(flight_data)

@app.route("/status", methods=["GET"])
def status():
    return jsonify({
        "connected": serial_connected and bool(latest_data),
        "serial_connected": serial_connected,
        "packets_received": len(flight_data),
        "latest_ts": latest_data.get('ts') if latest_data else None,
        "port": SERIAL_PORT
    })

@app.route("/test-data", methods=["GET"])
def test_data():
    """Generate test telemetry data for debugging"""
    global latest_data, flight_data
    
    test_packets = [
        {'alt': 0, 'ax': 0.008026, 'ay': 0.001121, 'az': 0.986108, 'gx': 0.072626, 'gy': 0.175359, 'gz': 0.01771, 'launched': False, 'ejected': False, 'sim': True, 'ts': 858441},
        {'alt': 5, 'ax': 0.01, 'ay': 0.002, 'az': 0.99, 'gx': 0.08, 'gy': 0.18, 'gz': 0.02, 'launched': False, 'ejected': False, 'sim': True, 'ts': 858741},
        {'alt': 15, 'ax': 0.02, 'ay': 0.005, 'az': 0.98, 'gx': 0.1, 'gy': 0.2, 'gz': 0.03, 'launched': True, 'ejected': False, 'sim': True, 'ts': 859041},
        {'alt': 50, 'ax': 0.05, 'ay': 0.01, 'az': 0.97, 'gx': 0.15, 'gy': 0.25, 'gz': 0.05, 'launched': True, 'ejected': False, 'sim': True, 'ts': 859341},
    ]
    
    flight_data.extend(test_packets)
    latest_data = test_packets[-1]
    
    return jsonify({
        "status": "Test data loaded",
        "packets_added": len(test_packets),
        "total_packets": len(flight_data)
    })

@app.route("/ports", methods=["GET"])
def ports():
    """Get list of available COM ports"""
    available = list_available_ports()
    return jsonify({
        "available_ports": available,
        "current_port": SERIAL_PORT
    })

@app.route("/db/stats", methods=["GET"])
def db_stats():
    """Get database statistics"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM telemetry")
        total = cursor.fetchone()[0]
        cursor.execute("SELECT MIN(received_at), MAX(received_at) FROM telemetry")
        dates = cursor.fetchone()
        conn.close()
        return jsonify({
            "total_packets": total,
            "first_packet": dates[0],
            "last_packet": dates[1],
            "db_path": DB_PATH
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/db/clear", methods=["POST"])
def db_clear():
    """Clear all data from database"""
    global flight_data, latest_data
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM telemetry")
        conn.commit()
        conn.close()
        flight_data = []
        latest_data = {}
        return jsonify({"status": "Database cleared"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/model", methods=["GET"])
def get_model():
    """Serve the 3D rocket model"""
    # Try different possible paths
    possible_paths = [
        os.path.join(os.path.dirname(__file__), "66-scifi-cartoon-rocket-obj", "scifi_cartoon_rocket.obj"),
        os.path.join(os.path.dirname(__file__), "scifi_cartoon_rocket.obj")
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            return send_file(path, mimetype='application/octet-stream')
            
    return jsonify({"error": "Model not found"}), 404

@app.route("/api/materials", methods=["GET"])
def get_materials():
    """Serve the MTL materials file"""
    mtl_path = os.path.join(os.path.dirname(__file__), "66-scifi-cartoon-rocket-obj", "scifi_cartoon_rocket.mtl")
    
    if os.path.exists(mtl_path):
        return send_file(mtl_path, mimetype='application/octet-stream')
    else:
        return jsonify({"error": "Materials file not found"}), 404

@app.route("/api/model-stl", methods=["GET"])
def get_model_stl():
    """Serve the STL rocket model"""
    stl_path = os.path.join(os.path.dirname(__file__), "Retro_Rocket.STL")
    
    if os.path.exists(stl_path):
        return send_file(stl_path, mimetype='application/octet-stream', 
                        download_name='Retro_Rocket.STL')
    else:
        return jsonify({"error": "STL model not found"}), 404

# ================= MAIN =================
if __name__ == "__main__":
    print("\nStarting Flight Telemetry Server...")
    print(f"Target Serial Port: {SERIAL_PORT}")
    
    # Initialize database
    init_db()
    
    # Load historical data from database
    flight_data = load_from_db(limit=5000)
    if flight_data:
        latest_data = flight_data[-1]
        print(f"Loaded {len(flight_data)} packets from database")
    
    t = threading.Thread(target=read_serial, daemon=True)
    t.start()

    print("Server running on http://localhost:5000")
    print("Database: " + DB_PATH)
    print("Load test data: http://localhost:5000/test-data")
    print("Check ports: http://localhost:5000/ports\n")
    
    app.run(host="0.0.0.0", port=5000, debug=False)
