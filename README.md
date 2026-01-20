# 🚀 Flight Telemetry Dashboard

A real-time rocket telemetry visualization system that displays flight data from a LoRa-based ground station receiver.

![Dashboard Preview](./dashboard_preview.png)

## Features

- **Real-time Data Display**: Live charts for velocity, altitude, and trajectory
- **3D Rocket Visualization**: Interactive 3D model that rotates based on accelerometer data
- **Detailed Sensor Readings**: Accelerometer (ax, ay, az) and Gyroscope (gx, gy, gz) values
- **Connection Status**: Visual indicators for serial connection and packet count

---

## Hardware Requirements

### Ground Station Receiver

- **Microcontroller**: Arduino/ESP32 with LoRa module (SX1276/SX1278)
- **Connection**: USB to Serial (appears as COM port on Windows)
- **Baud Rate**: 115200

### Rocket Transmitter

- **Sensors**: MPU6050 (accelerometer + gyroscope), BMP280 (altitude)
- **Communication**: LoRa radio module matching ground station frequency

### Expected JSON Data Format

The ground station should output JSON in this format:

```json
{"alt":0,"ax":0.78,"ay":-0.18,"az":0.25,"gx":0.54,"gy":0.52,"gz":-2.33,"launched":false,"ejected":false,"sim":true,"ts":1120641}
```

| Field                  | Description               |
| ---------------------- | ------------------------- |
| `alt`                | Altitude in meters        |
| `ax`, `ay`, `az` | Accelerometer values (g)  |
| `gx`, `gy`, `gz` | Gyroscope values (°/s)   |
| `launched`           | Launch detection flag     |
| `ejected`            | Parachute ejection flag   |
| `ts`                 | Timestamp in milliseconds |

---

## Software Setup

### Prerequisites

- Python 3.8+
- pip (Python package manager)

### Installation

1. **Clone or download this project**

   ```bash
   cd telemetry
   ```
2. **Create a virtual environment**

   ```bash
   python -m venv .venv
   ```
3. **Activate the virtual environment**

   ```bash
   # Windows
   .\.venv\Scripts\activate

   # Linux/Mac
   source .venv/bin/activate
   ```
4. **Install dependencies**

   ```bash
   pip install flask flask-cors pyserial
   ```

---

## Configuration

Edit `app.py` to set your serial port:

```python
# ================= CONFIG =================
SERIAL_PORT = "COM3"      # Change to your port (e.g., COM3, /dev/ttyUSB0)
BAUD_RATE = 115200
```

### Finding Your Serial Port

**Windows:**

1. Open Device Manager
2. Expand "Ports (COM & LPT)"
3. Look for your USB-Serial device (e.g., "USB-SERIAL CH340 (COM3)")

**Linux/Mac:**

```bash
ls /dev/tty*
# Look for /dev/ttyUSB0 or /dev/ttyACM0
```

---

## Running the Dashboard

1. **Connect your ground station receiver via USB**
2. **Start the server**

   ```bash
   .\.venv\Scripts\python.exe app.py
   ```
3. **Open the dashboard**

   - Open your browser and go to: `http://localhost:5000`
   - Or access from another device on the network: `http://<your-ip>:5000`
4. **Verify connection**

   - The status indicator should turn green when connected
   - Packet count should increment as data is received

---

## API Endpoints

| Endpoint               | Description                        |
| ---------------------- | ---------------------------------- |
| `GET /`              | Main dashboard page                |
| `GET /telemetry`     | Latest telemetry packet            |
| `GET /telemetry/all` | All stored telemetry data          |
| `GET /status`        | Connection status and packet count |
| `GET /ports`         | List available COM ports           |
| `GET /test-data`     | Inject mock data for testing       |
| `GET /api/model-stl` | Serve 3D rocket model              |
| `GET /db/stats`      | Database statistics                |
| `POST /db/clear`     | Clear all data from database       |

---

## Troubleshooting

### "Disconnected" status

- Check that the correct COM port is set in `app.py`
- Ensure the ground station is powered and connected
- Verify baud rate matches (default: 115200)

### No data appearing

- Check terminal for "RAW LINE" debug output
- Ensure ground station is receiving LoRa packets
- Verify JSON format from transmitter

### LoRa init failed

- This error appears in terminal when the ground station's LoRa module fails to initialize
- Check hardware connections on the ground station
- Verify antenna is connected

### 3D Model not loading

- The dashboard will use a procedural fallback rocket if STL fails to load
- Place your STL file in the project root as `Retro_Rocket.STL`

---

## Project Structure

```
telemetry/
├── app.py                  # Flask backend server
├── telemetry.db            # SQLite database (auto-created)
├── template/
│   └── index.html          # Frontend dashboard
├── Retro_Rocket.STL        # 3D rocket model (optional)
├── .venv/                  # Python virtual environment
└── README.md               # This file
```
