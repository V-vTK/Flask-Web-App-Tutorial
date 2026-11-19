# Deployment

Requirements: a server with Docker and the compose plugin. Nothing else.

## 1. Quick start

```bash
cp .env.example .env
# edit .env: set SECRET_KEY to a long random value (e.g. `openssl rand -hex 32`)
docker compose up -d --build
```

No migration, seed, or admin user is needed; the SQLite database is created on first start.

## 2. Configuration

Set in `.env` (read by compose).

| Variable | Meaning | Default | Must change? |
|---|---|---|---|
| `SECRET_KEY` | Secret used to sign session cookies | `change-me` in `.env.example`; `hjshjhdjah kjshkjdhjs` if unset | **Yes** |
| `HOST_PORT` | Host port the app is published on | `5001` | No |
| `PORT` | Port the app listens on inside the container (fixed in `compose.yaml`) | `5001` | No (do not change) |

## 3. Ports

| Service | Container port | Published on host | Exposure |
|---|---|---|---|
| web | 5001/tcp | `${HOST_PORT:-5001}` | Public (the app UI) |

There is no database or cache service; SQLite runs inside `web`, so nothing else is published.

Firewall: open TCP `HOST_PORT` (default 5001), or 80/443 if you put a TLS reverse proxy in front (not included) forwarding to it.

## 4. Data and volumes

| Volume | Mount | Contents |
|---|---|---|
| `11_app-data` (compose name `app-data`; prefix is the project name) | `/app/instance` | SQLite database (all users and notes) |

Backup:

```bash
docker run --rm -v 11_app-data:/data -v "$PWD":/backup busybox \
  tar czf /backup/app-data-$(date +%F).tgz -C /data .
```

Restore: stop the stack, then extract the archive into the volume the same way (`tar xzf ... -C /data`). Check the real volume name with `docker volume ls`.

## 5. Operations

- Health check: `http://<host>:<HOST_PORT>/login` (should return 200). Docker also checks it every 30s: `docker compose ps`.
- Logs: `docker compose logs -f web`
- Update: `git pull && docker compose up -d --build`
- Stop: `docker compose down` (data kept)
- Reset (**deletes all data**): `docker compose down -v && docker compose up -d --build`
