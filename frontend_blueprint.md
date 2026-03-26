# Ankurah Frontend: Architectural Blueprint

This document serves as the technical blueprint for the Ankurah "SafeSight" Operation Center frontend. It outlines the component structure, real-time data flow, and integration points required for a production-grade implementation.

## 1. System Overview

The Ankurah Frontend is a real-time monitoring dashboard designed for emergency response teams. It visualizes gesture-based distress signals detected by remote edge cameras.

### Technology Stack
- **Framework**: Vite + React
- **Styling**: Tailwind CSS (Mobile-responsive, dark-ops theme)
- **Maps**: Google Maps JavaScript API
- **Real-time**: Server-Sent Events (SSE)

---

## 2. Component Architecture

### Core Layout (`Dashboard.jsx`)
The central orchestrator of the UI. It manages:
- **Clock & Identity**: Self-updating timestamp and system branding.
- **Connection Status**: Visual indicator of backend connectivity (Live/Disconnected).
- **Global State**: Managed via the `useSSE` hook.

### Component Breakdown
1. **ThreatBanner**: A high-priority overlay that triggers a "RED ALERT" visual when a new incident is received. It stays active for a short duration or until dismissed.
2. **AlertMap**: An interactive map that plots active incidents as markers. In production, this should support clustering and auto-panning to the latest alert.
3. **CameraGrid**: Displays available camera nodes (e.g., Koramangala, MG Road). It should provide visual feedback if a camera is currently reporting a threat.
4. **AlertLog**: A scrollable history of past alerts, showing location, time, and AI confidence score.
5. **ConfidenceBadge**: A color-coded utility for displaying the AI's detection certainty (High/Medium/Low).

---

## 3. Communication Logic & Data Flow

The frontend operates on a "Hydrate and Stream" model.

### 1. Initial Hydration (REST)
Upon mounting, the frontend performs a `GET` request to `${BACKEND_URL}/alerts` to populate the `AlertLog` with the most recent 50 incidents.

### 2. Real-time Streaming (SSE)
The application avoids polling by using **Server-Sent Events**.
- **Hook**: `useSSE.js`
- **Endpoint**: `${BACKEND_URL}/stream`
- **Logic**:
    - Opens a persistent connection.
    - Listens for `type: "alert"` events.
    - When an alert arrives, it updates the `latestAlert` state (triggering the `ThreatBanner`) and prepends it to the `alerts` log.
    - **Heartbeats**: Listens for heartbeat events to maintain connection status.
    - **Resilience**: Implements exponential backoff for auto-reconnection.

---

## 4. Backend Integration Points

To ensure production-grade reliability, the frontend expects the following from the backend:

| Endpoint | Method | Purpose | Payload Example |
| :--- | :--- | :--- | :--- |
| `/alerts` | `GET` | History retrieval | `{"alerts": [...]}` |
| `/stream` | `GET` | Real-time events | `data: {"type": "alert", "location_name": "...", "confidence": 0.95}` |
| `/health` | `GET` | Connectivity check| `{"status": "ok"}` |

---

## 5. Production Requirements
- **Environment Variables**:
    - `VITE_BACKEND_URL`: The production API gateway.
    - `VITE_GMAPS_KEY`: API key with Maps/Places permissions.
- **Styling Tokens**: Uses a custom "ops-black" and "ops-dark" palette to reduce eye strain in monitoring environments.
- **Performance**: SSE allows the frontend to handle high frequencies of alerts without the overhead of WebSocket handshakes or constant HTTP polling.
