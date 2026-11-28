# Deployment: reaching PyBall from outside your local network

🇬🇧 English | 🇪🇸 [Español](deployment.es.md)

By default PyBall is only reachable on its host machine's local network —
`/manage` and `/match` are plain HTTP on whatever port you configured.
This guide covers two ways to reach them from outside that network, depending on
what you have available.

| You have... | Use | Result |
|---|---|---|
| A server with a stable address (a VPS, a home server with port forwarding, etc.) | [DuckDNS + Caddy](#duckdns--caddy) | Automatic HTTPS, always-on, zero day-to-day steps |
| No server — just a PC that runs PyBall sometimes | [ngrok](#ngrok-on-demand) | On-demand tunnel, started only when needed |

Whichever you use, once the app is reachable from the public internet, set access
tokens — see [setup.md's Access tokens section](setup.md#6-access-tokens) — or
anyone who finds the URL can use `/manage` freely.

## DuckDNS + Caddy

This is the pattern used in production for the maintainer's own PyBall instances: a
[Caddy](https://caddyserver.com/) reverse proxy in front of PyBall, with a free
[DuckDNS](https://www.duckdns.org/) subdomain and Caddy's DuckDNS DNS plugin
handling automatic HTTPS certificates — no port 80/443 forwarding puzzle, no manual
certificate renewal.

1. Create a free DuckDNS account and subdomain (e.g. `myteam.duckdns.org`), and copy
   its token from the DuckDNS dashboard.

2. In the same directory as your PyBall `compose.yaml` (see
   [setup.md](setup.md#2-bootstrap-a-workspace)), create a `Caddyfile`:

   ```
   myteam.duckdns.org {
       tls {
           dns duckdns {env.DUCKDNS_TOKEN}
       }
       reverse_proxy localhost:8000
   }
   ```

   Replace `myteam.duckdns.org` with your subdomain, and `8000` with `PORT` in
   `.env` — the *host* port PyBall is published on (not `api_port`, which is the
   container's internal listening port and stays `8000` regardless).

3. Add the token to `.env` (kept out of the Caddyfile itself):

   ```
   DUCKDNS_TOKEN=your-duckdns-token
   ```

4. Add a `caddy` service alongside `pyball` — either in the same `compose.yaml` or a
   separate one run from the same directory:

   ```yaml
   services:
     caddy:
       image: lulivi/pyball-caddy:latest
       network_mode: host
       volumes:
         - "./Caddyfile:/etc/caddy/Caddyfile"
         - "caddy_data:/data"
         - "caddy_config:/config"
       env_file: .env
       restart: unless-stopped

   volumes:
     caddy_data:
     caddy_config:
   ```

   `network_mode: host` lets Caddy reach `localhost:8000` directly, without changing
   PyBall's own `compose.yaml` or Docker network.

5. Set `base_url` in `config.toml` (or `PYBALL_CORE_BASE_URL`) to
   `https://myteam.duckdns.org`, then `docker compose up -d` both services.

That's it — the subdomain and certificate don't change again, so there's nothing to
repeat before each match.

## ngrok (on demand)

If there's no server to leave running with a stable address — e.g. a PC that only
runs PyBall around match time — [ngrok](https://ngrok.com/) opens a temporary
public tunnel to a local port on demand, with no DNS or router configuration.

ngrok assigns a tunnel's public URL as soon as the tunnel opens, before anything is
even listening on the target port — so start ngrok *first*, capture the URL it was
given, and only then start PyBall, so it boots already knowing its own public
address (used in the startup log and anywhere `base_url` is used).

Add a two-line `environment:` entry to your `compose.yaml` once, wiring the
already-documented `PYBALL_CORE_BASE_URL` override (see
[setup.md's env var override](setup.md#3-configure-configtoml)) through to the
container from the shell:

```yaml
services:
  pyball:
    image: lulivi/pyball:${TAG:-latest}
    environment:
      - PYBALL_CORE_BASE_URL
    user: "${UID}:${GID}"
    ports:
      - "127.0.0.1:${PORT}:8000"
    volumes:
      - "./config.toml:/pyball/config.toml"
      - "./logs:/pyball/logs"
      - "./data:/pyball/data"
      - "./plugins:/pyball/plugins"
    restart: unless-stopped
```

Then, each time remote access is needed:

```bash
# 1. Install ngrok (https://ngrok.com/download) once, and authenticate it once
#    (ngrok config add-authtoken <your-token>, from your free ngrok dashboard).

# 2. Start ngrok pointed at the port PyBall will use — it doesn't need to be
#    running yet
ngrok http 8000 > /dev/null &

# 3. Wait for ngrok's local API to report the assigned public URL
until curl -s http://127.0.0.1:4040/api/tunnels | grep -q public_url; do sleep 1; done
export PYBALL_CORE_BASE_URL=$(curl -s http://127.0.0.1:4040/api/tunnels | python3 -c "import sys,json;print(json.load(sys.stdin)['tunnels'][0]['public_url'])")
echo "Public URL: $PYBALL_CORE_BASE_URL"

# 4. Start PyBall — it boots already knowing its public URL
docker compose up -d
```

`8000` in the `ngrok http` command is the *host* port PyBall is published on — i.e.
`PORT` in `.env` (`8000` by default from `--bootstrap`). If you changed `PORT`, use
that value instead; the container's own internal port stays `8000` either way.

This keeps `config.toml`'s own `base_url` untouched — it stays whatever your
LAN-only default is — since the override only applies for that shell
session/that `docker compose up` invocation. If PyBall is already running, just
re-run `docker compose up -d` after exporting; compose recreates the container with
the new environment.

**Set access tokens before you tunnel.** Once ngrok is open, the entire app —
including `/manage` — is reachable by anyone who finds the URL. Set `match_token`
and `manage_token` in `config.toml` first (see
[setup.md's Access tokens section](setup.md#6-access-tokens)).

The free ngrok tier assigns a new random URL every time the tunnel restarts —
that's fine with the steps above, since `PYBALL_CORE_BASE_URL` is re-captured each
time. Close the tunnel (`kill %1`, or `Ctrl+C` if run in the foreground) when done.
