# AI-Weapon-Detection-System
Real-time weapon detection using YOLOv8, Flask, and React
This project detects weapons in real-time using YOLOv8 and OpenCV.

The system captures video from a camera and identifies weapons such as pistols, rifles, or knives.  
If a weapon is detected, the system sends an alert and stores the detection information.

## Features
- Real-time weapon detection
- SMS alert system using Twilio
- Detection history stored in SQLite database
- Web dashboard for monitoring

## Technologies Used
- Python
- Flask
- YOLOv8
- OpenCV
- React
- SQLite
- Twilio API

## Setup Instructions

### 1. Install backend dependencies

```
pip install -r requirements.txt
```

### 2. Run the backend server

```
python app.py
```

### 3. Install frontend dependencies

```
npm install
```

### 4. Start the frontend

```
npm run dev
```

## Note

Place the trained YOLO model file **best-weapon-2.pt** inside the `models` folder before running the project.
