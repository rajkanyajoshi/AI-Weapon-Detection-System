from flask import Flask, Response, jsonify
from flask_cors import CORS
import cv2
from ultralytics import YOLO
import torch
import clip
from PIL import Image
import numpy as np
import os

# ------------------- Flask App -------------------
app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

# ------------------- YOLO Model -------------------
MODEL_PATH = r"D:\Course Project\EDI\Backend\models\best-weapon-2.pt"
model = YOLO(MODEL_PATH)

CLASS_NAMES = {
    0: '0',
    1: 'Knife',
    2: 'Person',
    3: 'Pistol',
    4: 'Sword',
    5: 'Handgun',
    6: 'Pistol',
    7: 'Rifle'
}

# ------------------- CLIP Model -------------------
device = "cuda" if torch.cuda.is_available() else "cpu"
clip_model, preprocess_clip = clip.load("ViT-B/32", device=device)

# Text prompts for CLIP
clip_texts = [
    "a real gun",
    "a child holding a real gun",
    "a person holding a gun",
    "a pistol",
    "a rifle",
    "a toy gun",
    "a water gun",
    "a person holding a toy gun"
]

# Indexes of real weapon prompts
real_gun_prompts = [0, 1, 2, 3, 4]  # first five entries are real guns

def is_real_weapon(cropped_frame):
    """
    cropped_frame: numpy array (BGR)
    Returns True if CLIP thinks the cropped image contains a real weapon.
    """
    if cropped_frame.size == 0:
        return False

    # Convert BGR to RGB and PIL
    image = cv2.cvtColor(cropped_frame, cv2.COLOR_BGR2RGB)
    image = Image.fromarray(image)
    image_input = preprocess_clip(image).unsqueeze(0).to(device)

    with torch.no_grad():
        image_features = clip_model.encode_image(image_input)
        text_features = clip_model.encode_text(clip.tokenize(clip_texts).to(device))

        # Normalize
        image_features /= image_features.norm(dim=-1, keepdim=True)
        text_features /= text_features.norm(dim=-1, keepdim=True)

        # Cosine similarity
        similarity_scores = (100.0 * image_features @ text_features.T).squeeze(0)

        # Check if any real gun prompt has similarity above threshold
        threshold = 25  # tune this based on your dataset
        for idx in real_gun_prompts:
            if similarity_scores[idx] > threshold:
                return True
    return False

# ------------------- Camera Setup -------------------
camera = cv2.VideoCapture(0)
latest_detections = []  # store detections for frontend

def generate_frames():
    global latest_detections
    while True:
        success, frame = camera.read()
        if not success:
            break

        results = model.predict(frame, conf=0.25, verbose=False)
        annotated = results[0].plot()
        latest_detections = []

        for box in results[0].boxes:
            cls = int(box.cls[0])
            conf = float(box.conf[0])
            label = CLASS_NAMES.get(cls, "Unknown")

            # Crop the detected box
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            x1, y1 = max(0, x1), max(0, y1)
            x2, y2 = min(frame.shape[1]-1, x2), min(frame.shape[0]-1, y2)
            cropped = frame[y1:y2, x1:x2]

            if cropped.size == 0:
                continue

            # Apply CLIP for gun-like objects
            if label in ["Pistol", "Handgun", "Rifle"]:
                if not is_real_weapon(cropped):
                    continue  # skip false positives

            latest_detections.append({
                "type": label,
                "confidence": round(conf * 100, 1)
            })

        _, buffer = cv2.imencode('.jpg', annotated)
        frame_bytes = buffer.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

# ------------------- Routes -------------------
@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route('/detections')
def get_detections():
    return jsonify({"detections": latest_detections})

# ------------------- Main -------------------
if __name__ == '__main__':
    print("🚀 Flask weapon detection server running...")
    print("👉 Video Feed: http://127.0.0.1:5000/video_feed")
    print("👉 Detection API: http://127.0.0.1:5000/detections")
    os.makedirs("uploads", exist_ok=True)
    app.run(host='0.0.0.0', port=5000, debug=True)
