# SCI Factures

Application de gestion de factures pour SCI.

## Fonctionnalités
- Scan et extraction automatique des factures par IA (GPT-4o Vision)
- Saisie manuelle de factures
- Tableau de bord avec KPIs
- Gestion complète : ajout, modification, suppression
- Stockage sécurisé des photos de factures

## Stack
- **Backend** : FastAPI (Python)
- **Frontend** : HTML/CSS/JS + Jinja2
- **Base de données** : Supabase (PostgreSQL)
- **IA** : OpenAI GPT-4o Vision
- **Déploiement** : Render

## Installation locale
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Crée un fichier `.env` :
```
SUPABASE_URL=...
SUPABASE_ANON_KEY=...
SUPABASE_SERVICE_ROLE_KEY=...
OPENAI_API_KEY=...
```

Lance le serveur :
```bash
uvicorn main:app --reload
```

## Variables d'environnement requises
| Variable | Description |
|---|---|
| `SUPABASE_URL` | URL du projet Supabase |
| `SUPABASE_ANON_KEY` | Clé publique Supabase |
| `SUPABASE_SERVICE_ROLE_KEY` | Clé secrète Supabase |
| `OPENAI_API_KEY` | Clé API OpenAI |
| `ENVIRONMENT` | Mettre `production` en prod |
