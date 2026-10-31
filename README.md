# Agentic AI Platform

Phase 1: bilingual responsive Liquid Glass hero landing page and FastAPI health API.

## Frontend
```bash
cd frontend
npm install
npm run dev
```

## Backend
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Authentication, AI, agents, database and admin are planned, not implemented. Never commit API keys.

## Deploy
Settings > Pages > Source: GitHub Actions. Frontend deploys automatically on main; backend requires separate hosting.