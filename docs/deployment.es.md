# Despliegue: acceder a PyBall desde fuera de tu red local

🇬🇧 [English](deployment.md) | 🇪🇸 Español

Por defecto, PyBall solo es accesible en la red local de la máquina que lo aloja —
`/manage`, `/match` y `/signup` son HTTP plano en el puerto que hayas configurado.
Esta guía cubre dos formas de acceder desde fuera de esa red, según lo que tengas
disponible.

| Tienes... | Usa | Resultado |
|---|---|---|
| Un servidor con dirección estable (un VPS, un servidor doméstico con redirección de puertos, etc.) | [DuckDNS + Caddy](#duckdns--caddy) | HTTPS automático, siempre activo, cero pasos día a día |
| Ningún servidor — solo un PC que ejecuta PyBall a ratos | [ngrok](#ngrok-bajo-demanda) | Túnel puntual, activado solo cuando hace falta |

Uses lo que uses, en cuanto la app sea accesible desde internet, configura los
tokens de acceso — ver [Tokens de acceso en setup.es.md](setup.es.md#6-tokens-de-acceso)
— o cualquiera que encuentre la URL podrá usar `/manage` libremente.

## DuckDNS + Caddy

Este es el patrón usado en producción para las propias instancias de PyBall del
mantenedor: un proxy inverso [Caddy](https://caddyserver.com/) delante de PyBall,
con un subdominio gratuito de [DuckDNS](https://www.duckdns.org/) y el plugin DNS
de DuckDNS para Caddy gestionando certificados HTTPS automáticos — sin el rompecabezas
de redirigir los puertos 80/443, sin renovación manual de certificados.

1. Crea una cuenta y subdominio gratuitos en DuckDNS (ej. `mipena.duckdns.org`), y
   copia el token desde el panel de DuckDNS.

2. En el mismo directorio que el `compose.yaml` de tu PyBall (ver
   [setup.es.md](setup.es.md#2-genera-un-espacio-de-trabajo)), crea un `Caddyfile`:

   ```
   mipena.duckdns.org {
       tls {
           dns duckdns {env.DUCKDNS_TOKEN}
       }
       reverse_proxy localhost:8000
   }
   ```

   Sustituye `mipena.duckdns.org` por tu subdominio, y `8000` por el `api_port` de
   tu instancia (`PORT` en `.env`).

3. Añade el token a `.env` (así queda fuera del propio Caddyfile):

   ```
   DUCKDNS_TOKEN=tu-token-de-duckdns
   ```

4. Añade un servicio `caddy` junto a `pyball` — bien en el mismo `compose.yaml`, o
   en uno aparte ejecutado desde el mismo directorio:

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

   `network_mode: host` deja que Caddy llegue directamente a `localhost:8000`, sin
   tocar el `compose.yaml` de PyBall ni su red Docker.

5. Fija `base_url` en `config.toml` (o `PYBALL_CORE_BASE_URL`) a
   `https://mipena.duckdns.org`, y luego `docker compose up -d` en ambos servicios.

Y ya está — el subdominio y el certificado no vuelven a cambiar, así que no hay
nada que repetir antes de cada partido.

## ngrok (bajo demanda)

Si no hay ningún servidor que dejar encendido con una dirección estable — p. ej. un
PC que solo ejecuta PyBall los días de partido — [ngrok](https://ngrok.com/) abre
un túnel público temporal hacia un puerto local bajo demanda, sin configurar DNS ni
el router.

ngrok asigna la URL pública del túnel en cuanto este se abre, antes incluso de que
haya nada escuchando en el puerto de destino — así que arranca ngrok *primero*,
captura la URL que le han asignado, y solo entonces arranca PyBall, para que este
arranque ya sabiendo su propia dirección pública (usada en el log de arranque y en
cualquier sitio donde se use `base_url`).

`docker compose up` no tiene flag `-e`/`--env` para fijar una variable de entorno
puntual (solo `docker compose run` la tiene, y eso salta la política `restart:` y el
mapeo de puertos que `up` proporciona para el servicio real). En su lugar, añade una
entrada `environment:` de dos líneas a tu `compose.yaml`, una sola vez, conectando
el override ya documentado `PYBALL_CORE_BASE_URL` (ver
[el override por variable de entorno en setup.es.md](setup.es.md#3-configura-configtoml))
hasta el contenedor desde el shell:

```yaml
services:
  pyball:
    image: lulivi/pyball:${TAG:-latest}
    environment:
      - PYBALL_CORE_BASE_URL=${PYBALL_CORE_BASE_URL:-}
    user: "${UID}:${GID}"
    ports:
      - "127.0.0.1:${PORT}:8000"
    volumes:
      - "./config.toml:/pyball/config.toml"
      - "./logs:/pyball/logs"
      - "./data:/pyball/data"
    restart: unless-stopped
```

Después, cada vez que haga falta acceso remoto:

```bash
# 1. Instala ngrok (https://ngrok.com/download) una vez, y autentícalo una vez
#    (ngrok config add-authtoken <tu-token>, desde tu panel gratuito de ngrok).

# 2. Arranca ngrok apuntando al puerto que usará PyBall — no hace falta que ya
#    esté corriendo
ngrok http 8000 > /dev/null &

# 3. Espera a que la API local de ngrok informe de la URL pública asignada
until curl -s http://127.0.0.1:4040/api/tunnels | grep -q public_url; do sleep 1; done
export PYBALL_CORE_BASE_URL=$(curl -s http://127.0.0.1:4040/api/tunnels | python3 -c "import sys,json;print(json.load(sys.stdin)['tunnels'][0]['public_url'])")
echo "URL pública: $PYBALL_CORE_BASE_URL"

# 4. Arranca PyBall — ya arranca sabiendo su URL pública
docker compose up -d
```

El `8000` del comando `ngrok http` es el puerto del *host* en el que PyBall queda
publicado — es decir, `PORT` en `.env` (`8000` por defecto tras `--bootstrap`). Si
cambiaste `PORT`, usa ese valor en su lugar; el puerto interno del contenedor sigue
siendo `8000` en cualquier caso.

Esto deja intacto el `base_url` propio de `config.toml` — se queda con el valor por
defecto de tu red local — ya que el override solo aplica a esa sesión de
shell/esa invocación de `docker compose up`. Si PyBall ya estaba corriendo, basta
con volver a ejecutar `docker compose up -d` tras exportar la variable; compose
recrea el contenedor con el nuevo entorno.

**Configura los tokens de acceso antes de abrir el túnel.** En cuanto ngrok está
activo, toda la app — incluido `/manage` — es accesible para quien encuentre la
URL. Configura `match_token`, `signup_token` y `manage_token` en `config.toml`
primero (ver [Tokens de acceso en setup.es.md](setup.es.md#6-tokens-de-acceso)).

El plan gratuito de ngrok asigna una URL aleatoria nueva cada vez que el túnel se
reinicia — no supone ningún problema con los pasos anteriores, ya que
`PYBALL_CORE_BASE_URL` se vuelve a capturar cada vez. Cierra el túnel (`kill %1`, o
`Ctrl+C` si lo ejecutaste en primer plano) cuando termines.
