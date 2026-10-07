# TaskFlow — Generated Golden Application

This is the first executable candidate for the Tiannara ESAP Golden Coherence Suite.

## Local run

```bash
docker compose up --build
```

Frontend: http://localhost:3000
API: http://localhost:8000/docs

## Verification

Backend tests:

```bash
cd backend
python -m pytest -q
```

Required verification covers authentication, workspace isolation, RBAC, assignee isolation, task lifecycle and audit effect creation.

## Portfolio status

This candidate is generated from the committed TaskFlow ISR and acceptance contract. It is not certified until the complete build, security, integration, E2E, deployment and runtime-evidence gates pass.