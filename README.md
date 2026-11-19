# Notes app (React + TypeScript)

Express + SQLite backend with a React frontend (server-rendered and hydrated), all in TypeScript.

## Run locally

```
npm ci
npm run build
npm start        # serves on $PORT (default 5001)
```

Environment: `PORT`, `SECRET_KEY`, `DB_PATH` (default `instance/database.db`).

## Docker

```
docker compose up --build
```

The app listens on port 5001; SQLite data persists in the `app-data` volume.
