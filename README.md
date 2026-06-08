# DroneEye AI Dashboard
Real-time operator dashboard for drone-based transmission line inspection.

## Quick Start
pip install -r requirements.txt
cp .env.example .env
python run.py
# Open http://localhost:5000

By default, `python run.py` serves both the frontend and backend, and also starts a built-in simulator feed so the dashboard shows live data without hardware.

## Render
Use these settings for a Render Web Service:

- Build Command: `pip install -r requirements.txt`
- Start Command: `python run.py`

Render provides the `PORT` environment variable automatically. Keep `ENABLE_SIMULATOR=true` for demo mode, or set it to `false` when real ESP32 hardware is sending data.

## Testing without hardware
The simulator starts automatically with `python run.py`. To run it separately instead, set `ENABLE_SIMULATOR=false` and start:

python backend/simulator.py
