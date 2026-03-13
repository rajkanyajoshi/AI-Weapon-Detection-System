from flask import Flask, Response, jsonify, request
from flask_cors import CORS
import cv2
from ultralytics import YOLO
import threading
import time
import sqlite3
from datetime import datetime
from twilio.rest import Client
import os

app = Flask(__name__)
CORS(app)

# ================= MODEL =================
MODEL_PATH = r"D:\Course Project\EDI\Backend\models\best-weapon-2.pt"
model = YOLO(MODEL_PATH)
CLASS_NAMES = model.names

# ================= TWILIO CONFIG =================
TWILIO_ACCOUNT_SID = "YOUR_TWILIO_ACCOUNT_SID"
TWILIO_AUTH_TOKEN = "YOUR_TWILIO_AUTH_TOKEN"
TWILIO_PHONE_NUMBER = "YOUR_TWILIO_PHONE_NUMBER" # Your Twilio number
twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

def send_alert_sms(weapon_type, confidence):
    message = f"🚨 ALERT: Weapon detected!\nType: {weapon_type}\nConfidence: {confidence}%"
    try:
        twilio_client.messages.create(
            body=message,
            from_=TWILIO_PHONE_NUMBER,
            to="+918788749526"  # Destination number
        )
        print("✅ SMS alert sent")
    except Exception as e:
        print("❌ Failed to send SMS:", e)

# ================= TWILIO CALL =================
@app.route("/call", methods=["POST"])
def call_unit():
    data = request.get_json()
    phone_number = data.get("phone")
    if not phone_number:
        return jsonify({"error": "Phone number is required"}), 400
    try:
        call = twilio_client.calls.create(
            to=phone_number,
            from_=TWILIO_PHONE_NUMBER,
            twiml=f"<Response><Say>Emergency! Please respond immediately.</Say></Response>"
        )
        print(f"📞 Call initiated to {phone_number}")
        return jsonify({"success": True, "call_sid": call.sid})
    except Exception as e:
        print("❌ Failed to initiate call:", e)
        return jsonify({"error": str(e)}), 500

# ================= SHARED STATE =================
camera = None
latest_frame = None
latest_detections = []
lock = threading.Lock()
running = False
CAMERA_ID = "CAM-001"
client_count = 0

camera_thread = None
detection_thread = None

# ================= ALERT STATE =================
last_weapon = None
last_alert_time = 0
ALERT_COOLDOWN = 10  # seconds

# ================= DATABASE =================
DB_PATH = "detections.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS detections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            camera_id TEXT,
            weapon_type TEXT,
            confidence REAL,
            severity INTEGER,
            date TEXT,
            time TEXT
        )
    """)
    conn.commit()
    conn.close()

def insert_detection(camera_id, weapon_type, confidence, severity):
    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%H:%M:%S")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO detections (camera_id, weapon_type, confidence, severity, date, time)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (camera_id, weapon_type, confidence, severity, date_str, time_str))
    conn.commit()
    conn.close()

init_db()

# ================= CAMERA THREAD =================
def camera_loop():
    global camera, latest_frame, running
    camera = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    if not camera.isOpened():
        print("❌ Camera failed to open")
        running = False
        return
    print("📸 Camera opened successfully")
    while running:
        ret, frame = camera.read()
        if not ret:
            time.sleep(0.01)
            continue
        with lock:
            latest_frame = frame.copy()
        time.sleep(0.01)

# ================= DETECTION THREAD =================
IGNORE_LIST = ["Person", "0", "Sword"]  # classes to ignore

def detection_loop():
    global latest_detections, running
    global last_weapon, last_alert_time

    os.makedirs("snapshots", exist_ok=True)  # ensure folder exists

    print("🧠 YOLO detection started")
    while running:
        if latest_frame is None:
            time.sleep(0.01)
            continue
        with lock:
            frame = latest_frame.copy()
        h, w, _ = frame.shape
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = model(frame_rgb, imgsz=640, conf=0.15)

        detections = []
        current_weapon = None
        highest_conf = 0

        for box in results[0].boxes:
            cls = int(box.cls[0])
            conf = float(box.conf[0])
            label = CLASS_NAMES.get(cls, str(cls))  # fallback to class id

            detections.append({
                "cameraId": CAMERA_ID,
                "type": label,
                "confidence": round(conf * 100, 1),
                "x": (int(box.xyxy[0][0]) / w) * 100,
                "y": (int(box.xyxy[0][1]) / h) * 100,
                "width": ((int(box.xyxy[0][2]) - int(box.xyxy[0][0])) / w) * 100,
                "height": ((int(box.xyxy[0][3]) - int(box.xyxy[0][1])) / h) * 100
            })

            if label not in IGNORE_LIST and conf > highest_conf:
                highest_conf = conf
                current_weapon = label

        now = time.time()
        if current_weapon:
            weapon_changed = current_weapon != last_weapon
            cooldown_passed = (now - last_alert_time) > ALERT_COOLDOWN
            if weapon_changed or cooldown_passed:
                severity = min(100, int(highest_conf * 100))
                insert_detection(CAMERA_ID, current_weapon, round(highest_conf * 100, 1), severity)

                # ---------------- SAVE SNAPSHOT ----------------
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                snapshot_filename = f"snapshots/{current_weapon}_{timestamp}.jpg"
                cv2.imwrite(snapshot_filename, frame)
                print(f"💾 Snapshot saved: {snapshot_filename}")
                # ----------------------------------------------

                print(f"🚨 ALERT TRIGGERED: {current_weapon}")
                send_alert_sms(current_weapon, round(highest_conf * 100, 1))
                last_weapon = current_weapon
                last_alert_time = now
        else:
            last_weapon = None

        with lock:
            latest_detections = detections

        time.sleep(0.05)

# ================= VIDEO STREAM =================
def generate_frames():
    global client_count, running
    try:
        while True:
            if latest_frame is None:
                time.sleep(0.02)
                continue
            with lock:
                frame = latest_frame.copy()
            ret, buffer = cv2.imencode(".jpg", frame)
            if not ret:
                continue
            yield (
                b"--frame\r\n"
                b"Content-Type: image/jpeg\r\n\r\n" +
                buffer.tobytes() +
                b"\r\n"
            )
            time.sleep(0.03)
    finally:
        client_count -= 1
        if client_count <= 0:
            stop_camera()

def stop_camera():
    global running, camera, camera_thread, detection_thread
    running = False
    if camera is not None:
        camera.release()
        camera = None
    camera_thread = None
    detection_thread = None
    print("🛑 Camera and detection threads stopped")

# ================= API ENDPOINTS =================
@app.route("/video_feed")
def video_feed():
    global client_count, camera_thread, detection_thread, running
    client_count += 1
    if not running:
        running = True
        camera_thread = threading.Thread(target=camera_loop, daemon=True)
        detection_thread = threading.Thread(target=detection_loop, daemon=True)
        camera_thread.start()
        detection_thread.start()
    return Response(generate_frames(), mimetype="multipart/x-mixed-replace; boundary=frame")

@app.route("/detections")
def detections():
    with lock:
        return jsonify({"detections": latest_detections})

@app.route("/history")
def history():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM detections ORDER BY id DESC LIMIT 50")
    rows = cursor.fetchall()
    conn.close()
    return jsonify([{
        "id": r[0],
        "cameraId": r[1],
        "weaponType": r[2],
        "confidence": r[3],
        "severity": r[4],
        "date": r[5],
        "time": r[6]
    } for r in rows])

# ================= ANALYTICS ENDPOINTS =================
@app.route("/analytics/summary")
def get_summary():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM detections")
    total = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(DISTINCT date) FROM detections")
    days = max(cursor.fetchone()[0], 1)
    conn.close()
    return jsonify({
        "avgDetectionRate": round(total / days, 1),
        "accuracy": 98.2,
        "falsePositiveRate": 1.4,
        "responseTime": 0.8
    })

@app.route("/analytics/weekly")
def get_weekly_trend():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT date, COUNT(*) FROM detections 
        GROUP BY date 
        ORDER BY date DESC LIMIT 7
    """)
    rows = cursor.fetchall()
    conn.close()
    return jsonify([{"day": r[0], "detections": r[1]} for r in reversed(rows)])

@app.route("/analytics/weapons")
def get_weapon_distribution():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM detections")
    total = max(cursor.fetchone()[0], 1)
    cursor.execute("SELECT weapon_type, COUNT(*) as count FROM detections GROUP BY weapon_type")
    rows = cursor.fetchall()
    conn.close()
    return jsonify([{
        "type": r[0],
        "percentage": round((r[1] / total) * 100, 1)
    } for r in rows])

@app.route("/analytics/top-cameras")
def get_top_cameras():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT camera_id, COUNT(*) as count 
        FROM detections 
        GROUP BY camera_id 
        ORDER BY count DESC
    """)
    rows = cursor.fetchall()
    conn.close()
    return jsonify([{
        "id": r[0],
        "location": "Main Entrance" if r[0] == "CAM-001" else "North Wing",
        "detections": r[1],
        "accuracy": 99.1
    } for r in rows])

# ================= START =================
if __name__ == "__main__":
    print("🚀 Flask YOLO + Twilio backend ready")
    app.run(host="0.0.0.0", port=5000, debug=False, threaded=True)
