# 🚀 RAAH System - Installation & Quickstart

Welcome to the **RAAH** (Real-time AI Highway monitoring) installation guide. This system is designed for high-performance highway monitoring using a 3-layer intelligence architecture.

---

## 🛠️ Prerequisites

Ensure your system meets these requirements before starting:

| Component | Requirement |
|-----------|-------------|
| **OS** | Windows 10/11 (WSL2 recommended) or Ubuntu 22.04+ |
| **Python** | 3.10 or 3.11 (Check: `python --version`) |
| **Node.js** | 20.x or 22.x (Check: `node -v`) |
| **Docker** | Desktop or Engine (with `docker compose`) |
| **RAM** | 8GB minimum (16GB recommended) |

---

## ⚡ 1-Click Setup (Quickstart)

We provide a master setup script that handles dependency installation, database migrations, and seed data generation.

```bash
# Clone the repository
git clone https://github.com/user/raah-system.git
cd raah-system

# Run the unified setup script
# This script creates venvs, installs packages, and boots infrastructure
./scripts/setup_all.sh
```

---

## 📦 Manual Step-by-Step Installation

If you prefer manual control or the 1-click script fails, follow these steps in order:

### 1. Infrastructure Boot
RAAH requires PostgreSQL for long-term storage and Redis for real-time streams.
```bash
docker compose up -d postgres redis
```

### 2. Backend & Database Setup
```bash
cd backend
python -m venv venv
source venv/bin/activate  # venv\Scripts\activate on Windows
pip install -r requirements.txt
python -m backend.db.seed  # Create tables and load seed
```

### 3. ML Service Initialization
```bash
cd ../ml_service
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python scripts/train_models.py  # Initial model training
```

### 4. Simulator Boot
```bash
cd ../simulator
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
# Simulator runs on port 8001
python main.py
```

### 5. Frontend Dashboards
```bash
# Authority Dashboard (Officer View)
cd ../authority-dashboard
npm install
npm run dev

# Commuter Portal (Mobile View)
cd ../commuter-portal
npm install
npm run dev
```

---

## 🏁 Verification Checkpoint

Once everything is running, visit these URLs:

1.  **Authority Dashboard**: `http://localhost:5173` (Login: `authority` / `raah2024`)
2.  **Commuter Portal**: `http://localhost:5174`
3.  **API Docs**: `http://localhost:8000/docs`
4.  **Simulator Control**: `http://localhost:8001/status`

---

## 📂 Project Structure

- `/backend`: FastAPI core, Ingestion, Hard Logic Engine.
- `/ml_service`: Scikit-learn models & scoring pipelines.
- `/simulator`: Traffic generation & scenario engine.
- `/authority-dashboard`: Admin control room (React).
- `/commuter-portal`: Mobile-optimized user portal (React).
- `/docs`: Technical specifications and system architecture.

---

## 🆘 Troubleshooting

- **Redis Connection Error**: Ensure Redis is running (`docker ps`). Check `.env` for `REDIS_URL`.
- **Database Migrations**: If tables are missing, re-run `python -m backend.db.seed`.
- **Node Modules**: If build fails, delete `node_modules` and `package-lock.json` then `npm install`.

---

> **Hackathon Note**: For the best demo experience, keep the Simulator window open alongside the Dashboard to observe real-time event logs.
