# Ankurah: SafeSight Real-Time Distress Detection 🛡️

Ankurah is a real-time, gesture-based alert system designed to detect and broadcast distress signals (Signal for Help) through edge cameras. It bridges computer vision detection with high-priority emergency notifications for police and dispatch centers.

---

## 🚀 System Architecture

The project consists of three synchronized components:
1. **The Detector (Edge AI)**: Uses Mediapipe to detect "Open Palm" -> "Thumb Tuck" -> "Closed Fist" sequences.
2. **The Backend (FastAPI)**: Receives alerts, logs incidents, and broadcasts them via SSE (Server-Sent Events) while firing SMS/Twitter notifications.
3. **The Frontend (Operations Dashboard)**: A real-time monitoring interface with an incident map and a live alert feed.

---

## 🛠️ Multi-Device Demo Setup

To run the Ankurah demo across multiple systems (e.g., Device A = Backend, Device B = Detector, Device C = Frontend), follow these network synchronization steps:

### 1. Identify the Backend IP
On the machine running the **Backend**, find your local IP address:
- **Mac/Linux**: `ifconfig` or `ipconfig getifaddr en0` (Example: `192.168.1.10`)
- **Windows**: `ipconfig`

### 2. Configure Environments
Update the configuration on **all devices** to point to the Backend IP:

- **Detector Device (`detector/.env`)**:
  ```env
  BACKEND_URL=http://<BACKEND_IP>:8000
  CAMERA_ID=CAM-02
  ```
- **Frontend Device (`frontend/.env`)**:
  ```env
  VITE_BACKEND_URL=http://<BACKEND_IP>:8000
  VITE_GMAPS_KEY=Your_Google_Maps_Key
  ```

---

## ⚙️ Running the Components

### Step 1: Start the Backend (Device A)
```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### Step 2: Start the Frontend Dashboard (Device C)
```bash
cd frontend
npm install
npm run dev -- --host 0.0.0.0
```
*Wait for the URL (e.g., `http://192.168.1.10:5173`) and open it on any device in the same network.*

### Step 3: Start the Detector (Device B)
```bash
cd detector
source venv/bin/activate
pip install -r requirements.txt
python3 main.py
```

---

## 🖐️ Gesture Induction
To trigger an alert:
1. **Open Palm**: Fingers extended towards the camera for 1 second.
2. **Tuck Thumb**: Fold the thumb into the palm.
3. **Closed Fist**: Wrap your fingers over the thumb.
   - *Wait 1 second between steps for the state machine to lock in.*

---

## 📦 Deployment Cleanliness
This repository is pre-configured to ignore bulky assets:
- `node_modules/` is excluded by `.gitignore`.
- Python virtual environments (`venv/`) are excluded.
- Local `.mp4` recordings are not tracked.
