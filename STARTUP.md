## gif-player startup guide

This doc is the **copy/paste “get it running”** guide for:
- Local dev on a laptop (mock display)
- Single-process run (backend serves UI + API)
- Raspberry Pi `systemd` service (repo at `~/gif-player`, port `8001`)

---

## Prereqs

### Backend (Python)
- Python 3 installed

### Frontend (UI)
- Node.js + npm installed

---

## Local: backend only (mock mode)

```bash
cd ~/gif-player/backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

mkdir -p ~/gif-player/_local_gifs
PORT=8001 DISPLAY_DRIVER=mock GIF_DIR=~/gif-player/_local_gifs python run_server.py
```

Open:
- UI (if built/served): `http://localhost:8001/`
- API docs: `http://localhost:8001/docs`
- API status: `http://localhost:8001/api/status`

---

## Local: dev mode (backend + Vite dev server)

Run backend in one terminal:

```bash
cd ~/gif-player/backend
source .venv/bin/activate
mkdir -p ~/gif-player/_local_gifs
PORT=8001 DISPLAY_DRIVER=mock GIF_DIR=~/gif-player/_local_gifs python run_server.py
```

Run UI in a second terminal:

```bash
cd ~/gif-player/frontend
npm install
VITE_API_TARGET=http://127.0.0.1:8001 npm run dev
```

Open:
- UI: `http://localhost:5173/`

---

## Local: one command (single-process: backend serves UI + API)

This is the simplest “appliance-style” run locally. It builds the UI into `frontend/dist/` and then runs the backend, which serves both the UI and `/api/*`.

```bash
cd ~/gif-player
PORT=8001 DISPLAY_DRIVER=mock GIF_DIR=~/gif-player/_local_gifs make run
```

Open:
- UI: `http://localhost:8001/`
- API docs: `http://localhost:8001/docs`

---

## Raspberry Pi: systemd service (repo at `~/gif-player`, port 8001)

The unit file template is at `deploy/gif-player.service` and assumes:
- repo path: `~/gif-player`
- port: `8001`
- venv: `~/gif-player/backend/.venv`
- UI built output: `~/gif-player/frontend/dist`

### 1) Backend venv + deps (on the Pi)

```bash
cd ~/gif-player/backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2) Build UI (on the Pi)

```bash
cd ~/gif-player/frontend
npm install
npm run build
```

### 3) Install + enable service

```bash
sudo cp ~/gif-player/deploy/gif-player.service /etc/systemd/system/gif-player.service
sudo systemctl daemon-reload
sudo systemctl enable --now gif-player.service
```

### 4) Logs

```bash
sudo journalctl -u gif-player.service -f
```

Open:
- UI: `http://<pi-ip>:8001/`
- API docs: `http://<pi-ip>:8001/docs`

---

## Troubleshooting

### Port already in use

If you see `address already in use`, pick another port:

```bash
PORT=8010 python run_server.py
```

Or find the process:

```bash
lsof -nP -iTCP:8001 -sTCP:LISTEN
```

### UI shows 404 for `/api/...` on `localhost:5173`

That means the Vite dev proxy is pointing at the wrong backend port. Restart with:

```bash
VITE_API_TARGET=http://127.0.0.1:8001 npm run dev
```

### UI shows `net::ERR_CONNECTION_REFUSED` to `127.0.0.1:8001`

Backend isn’t running (or not on that port). Re-run the backend command and keep it running.

