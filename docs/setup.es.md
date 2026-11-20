# Guía de instalación

🇬🇧 [English](setup.md) | 🇪🇸 Español

Esta guía cubre instalar, configurar y ejecutar PyBall como usuario final. Si quieres
construir PyBall desde el código fuente o contribuir, mira en su lugar la
[guía de contribución](../CONTRIBUTING.es.md).

Esta guía asume Linux con Docker instalado — la forma más simple y probada de
ejecutar PyBall. ¿Vas a instalarlo en un PC con Windows? Sigue esta misma guía tal
cual, pero lee antes [Ejecutar en Windows (WSL2)](#ejecutar-en-windows-wsl2).

## 1. Elige una topología

PyBall se distribuye como dos imágenes Docker, construidas desde el mismo código:

| Imagen | Qué ejecuta | ¿Necesita un bot de Telegram? |
|---|---|---|
| `lulivi/pyball` | FastAPI — `/manage`, `/match`, y opcionalmente alta por cuenta propia en `/signup` (ver abajo) | No |
| `lulivi/pyball-telegram` | Bot de Telegram + FastAPI (`/manage` y `/match`) | Sí |

Todas las funciones — crear partidos, generar equipos (clásico o triangular), seguir un
partido, cerrar una sesión triangular, ver estadísticas — están disponibles desde
`/manage` y `/match` en cualquiera de las dos imágenes; Telegram y `/signup` son capas
de conveniencia añadidas encima, nunca un requisito. Si tu grupo no usa Telegram, usa
`pyball`: pon `enable_web_signup = true` en `config.toml` si quieres que los jugadores
se apunten o se bajen ellos mismos de un partido con su código personal en `/signup`
(ver [Flujo de la aplicación](workflow.es.md#alta-por-cuenta-propia-en-signup)) sin
tocar `/manage`, o déjalo en `false` (por defecto) para que el alta siga siendo una
tarea de admin, hecha desde `/manage`. Usa `pyball-telegram` si quieres que las
convocatorias se publiquen automáticamente en un grupo, comandos de admin desde
Telegram, y reacciones/notificaciones en el chat.

## 2. Genera un espacio de trabajo

Elige un directorio vacío para la configuración y los datos de esta instancia, y ejecuta:

```bash
mkdir pyball && cd pyball
docker run --rm --user "$(id -u):$(id -g)" -v "$(pwd):/pyball" lulivi/pyball --bootstrap
# o, para Telegram:
docker run --rm --user "$(id -u):$(id -g)" -v "$(pwd):/pyball" lulivi/pyball-telegram --bootstrap
```

Esto crea, en el directorio actual:

```
config.toml     # tu configuración — edítalo a continuación
compose.yaml    # definición del servicio de docker compose, fijada a la imagen que generaste
.env            # UID/GID/PORT/TAG usados por compose.yaml
README.md       # un enlace corto de vuelta a esta guía
data/           # archivos de datos en JSON (ver docs/data-directory.es.md)
logs/           # logs de la aplicación
```

`--bootstrap` se niega a ejecutarse si `config.toml`, `compose.yaml` o `.env` ya existen
en el directorio destino, así que es seguro volver a ejecutarlo — no sobrescribirá tu
configuración.

## 3. Configura `config.toml`

Cualquier clave también se puede fijar con una variable de entorno,
`PYBALL_<SECCIÓN>_<CLAVE>` (ej. `PYBALL_CORE_LOCATION`, `PYBALL_TELEGRAM_BOT_TOKEN`) —
útil para mantener secretos fuera de `config.toml` o sobrescribir un valor por
despliegue sin editar el archivo.

### `[pyball.core]` — todas las topologías

| Clave | Descripción | Por defecto |
|---|---|---|
| `location` | Ubicación por defecto del partido | *(obligatorio)* |
| `name` | Nombre de la instancia mostrado en la interfaz | *(obligatorio)* |
| `default_week_day` | Día por defecto (`monday`–`sunday`) para nuevos partidos | `wednesday` |
| `default_hour` | Hora de inicio por defecto (`HH:MM`) | `20:00` |
| `meetup_capacity` | Jugadores con los que juega un partido nuevo; la capacidad de cada partido se cambia luego desde `/manage` | `10` |
| `display_date_format` | Formato de fecha usado en los mensajes | `%Y-%m-%d %H:%M` |
| `team_colors` | Dos o tres nombres de color: los dos primeros son los equipos del partido clásico, el tercero solo se usa en triangulares (se rellena solo si indicas dos) | `["blanco", "negro", "rojo"]` |
| `base_url` | URL pública usada para construir el enlace de `/match` | *(obligatorio)* |
| `api_port` | Puerto del servidor HTTP | `8000` |
| `locale` | Locale usado para ordenar los nombres de jugadores | `es_ES.UTF-8` |
| `data_dir` | Directorio para los archivos de datos JSON | `data` |
| `match_token` | Token de acceso solo para `/match` (opcional, ver [Tokens de acceso](#6-tokens-de-acceso)) | *(vacío)* |
| `manage_token` | Token de acceso para todo, incluyendo `/manage` (opcional) | *(vacío)* |
| `enable_web_signup` | Activa la página de alta por cuenta propia `/signup` | `false` |
| `signup_token` | Token de acceso solo para `/signup` (opcional; solo relevante si `enable_web_signup` está activo, inofensivo si se deja vacío) | *(vacío)* |
| `theme_color` | Color de tema/fondo de la PWA | `#0f172a` |
| `icons_dir` | Directorio de iconos PWA personalizados (opcional) | *(vacío)* |

Colores de equipo disponibles: `blanco` `negro` `rojo` `naranja` `amarillo` `verde`
`azul` `morado` `marron`.

### `[pyball.telegram]` y subsecciones — solo `pyball-telegram`

Estas claves se ignoran en `pyball` — ver
[la configuración de Telegram es solo para el bot](data-directory.es.md#la-configuración-de-telegram-es-solo-para-el-bot)
para saber por qué.

| Clave | Descripción | Requerido |
|---|---|---|
| `telegram.bot_token` | Token del bot desde [@BotFather](https://t.me/BotFather) | **Sí** |
| `telegram.admins_ids` | IDs de usuario de Telegram autorizados a ejecutar comandos de admin | **Sí** |
| `telegram.regulars.meetups.chat_id` | Chat para la convocatoria y el resultado corregido (negativo para grupos) | **Sí** |
| `telegram.regulars.meetups.message_thread_id` | Hilo de foro para esos mensajes (vacío = ninguno) | No |
| `telegram.regulars.stats.chat_id` | Chat para estadísticas post-partido y `/meetup_stats` (`0` / omitir desactiva su publicación) | No |
| `telegram.regulars.stats.message_thread_id` | Hilo de foro para las estadísticas (vacío = ninguno) | No |
| `telegram.substitutes.meetups.chat_id` | Chat para el mensaje de suplentes (negativo para grupos) | **Sí** |
| `telegram.substitutes.meetups.message_thread_id` | Hilo de foro para el mensaje de suplentes (vacío = ninguno) | No |
| `telegram.management.logging.chat_id` | Canal de log operacional (`0` / omitir para desactivar) | No |
| `telegram.management.logging.message_thread_id` | Hilo de foro para los registros de log (vacío = ninguno) | No |
| `telegram.management.activity.chat_id` | Chat del feed de actividad de la convocatoria — altas, bajas, creada/cerrada/cancelada (`0` / omitir para desactivar) | No |
| `telegram.management.activity.message_thread_id` | Hilo de foro para el feed de actividad (vacío = ninguno) | No |

Para encontrar un ID de chat: añade el bot al grupo, envía cualquier mensaje, y luego
consulta `https://api.telegram.org/bot<TOKEN>/getUpdates` buscando el campo `chat.id`.

Cada uno puede apuntar al mismo grupo/hilo o a uno distinto. Los overrides por
variable de entorno siguen `PYBALL_<RUTA>_<CLAVE>`, p. ej.
`PYBALL_TELEGRAM_MANAGEMENT_ACTIVITY_CHAT_ID`.

`deploy/deploy.sh` envía sus propias notificaciones de despliegue con el token del
bot, el chat y el tema del foro de los secretos de GitHub `DEPLOY_NOTIFY_TOKEN`,
`DEPLOY_NOTIFY_CHAT_ID` y `DEPLOY_NOTIFY_THREAD_ID` — apúntalos al mismo chat y tema
que `telegram.management.logging`. Sin `DEPLOY_NOTIFY_TOKEN`, los despliegues no
envían notificaciones.

### `[pyball.plugins.<nombre>]` — plugins opcionales

Una tabla por plugin, con su nombre. Las dos topologías los ejecutan (ver
[Plugins](#8-plugins)). Estas tablas no admiten variables de entorno.

| Clave | Descripción | Obligatorio |
|---|---|---|
| `command` | Programa y argumentos que arrancan el plugin, ejecutado desde el espacio de trabajo, p. ej. `["./plugins/example-plugin", "--verbose"]` | **Sí** |
| `scopes` | Lo que el plugin puede hacer con la API de plugins: cualquiera de `players:read`, `players:write`, `meetups:read` (incluye el flujo de eventos), `meetups:write` | No (ninguno) |

## 4. Arranca la aplicación

```bash
docker compose up -d
docker compose logs -f
```

Una vez en marcha, abre `http://<host>:<PORT>/manage` en un navegador (el puerto es el
que hayas puesto en `.env`).

## 5. `/manage` frente a `/match`

La interfaz web de PyBall son dos páginas:

- **`/manage`** — la página de administración. Pega una convocatoria, añade/quita
  jugadores, genera equipos (clásico o triangular), edita equipos manualmente,
  regenera, cierra una sesión triangular, y consulta/comparte el resumen del último
  partido terminado.
- **`/match`** — el marcador en directo. Muestra el partido pendiente actual, deja
  registrar goles/asistencias, y finalizar el partido. Pensado para dejarlo abierto en
  un móvil o tablet durante la sesión — carga automáticamente el partido activo en cada
  momento, sin configuración manual una vez superado el aviso de token (abajo).

Con `enable_web_signup = true` también existe `/signup`, una página de alta por cuenta
propia para jugadores — ver
[Alta por cuenta propia en `/signup`](workflow.es.md#alta-por-cuenta-propia-en-signup).

Ver [docs/workflow.es.md](workflow.es.md) para el flujo completo paso a paso.

## 6. Tokens de acceso

`match_token`, `signup_token` y `manage_token` protegen la aplicación cuando se expone
más allá de tu propia red privada (ej. a través de un proxy inverso en internet) — sin
ellos, `/manage`, `/match` y `/signup` quedan abiertos a cualquiera que llegue a la URL.
Si los tres se dejan vacíos, no se aplica ninguna autenticación (correcto para una red
privada en la que ya confías). Cómo expongas la aplicación públicamente (proxy inverso,
VPN, túnel, etc.) depende de ti — estos tokens funcionan igual en cualquier caso.

| Ruta | Token requerido |
|---|---|
| `/`, archivos estáticos, manifiestos PWA | Ninguno (siempre público) |
| `/match`, `GET /api/match/active`, `POST /api/match/finish` | `match_token` **o** `manage_token` |
| `/signup` y `/api/signup/*` (solo si `enable_web_signup` está activo) | `signup_token` **o** `manage_token` |
| `/api/v1/*` (la API de plugins) | `Authorization: Bearer` con el token propio de un plugin **o** `manage_token` — ver [Plugins](#8-plugins) |
| `/manage` y todo lo demás bajo `/api/*` | Solo `manage_token` |

Dale el `match_token` (solo marcador) a un dispositivo que solo deba ver `/match` (ej.
una tablet montada en el campo), el `signup_token` a los jugadores (si `/signup` está
activo), y el `manage_token` a los admins. Visitar una URL con `?token=<valor>` una vez valida el
token y guarda una cookie `HttpOnly` que dura un año — no hace falta volver a pasar el
token en ese mismo dispositivo/navegador.

`signup_token` solo protege la propia página `/signup`, como una contraseña compartida
con todo el que puede usarla; una vez dentro, cada jugador se identifica además con su
propio código personal de alta (ver
[Flujo de la aplicación](workflow.es.md#alta-por-cuenta-propia-en-signup)) — son dos
capas independientes, y ninguna sustituye a la otra.

## 7. Actualizar

```bash
docker compose pull
docker compose up -d
```

Fija una versión concreta en vez de seguir siempre `latest` poniendo `TAG=4.13.0` en
`.env`.

## 8. Plugins

Un plugin es un programa opcional y de larga duración, escrito en cualquier lenguaje, que
amplía PyBall sin tocar su código. Se ejecuta mientras PyBall esté en marcha, reaccionando
al flujo de eventos o con su propio calendario: una tarea que se ejecuta una vez y
termina va en cron. Decláralo en `config.toml` (ver
[`[pyball.plugins.<nombre>]`](#pyballpluginsnombre--plugins-opcionales)) y pon el
programa en la carpeta `plugins/` del espacio de trabajo, que el `compose.yaml` generado
monta en `/pyball/plugins`. Luego arranca PyBall como siempre: sigue siendo un solo
comando.

PyBall ejecuta cada plugin declarado como proceso hijo, desde el espacio de trabajo:

- **Arranque:** cuando el servidor web ya está listo, con tres variables de entorno:
  `PYBALL_API_URL` (la API de plugins, p. ej. `http://127.0.0.1:8000/api/v1`),
  `PYBALL_API_TOKEN` (el token propio del plugin, nuevo en cada arranque) y
  `PYBALL_PLUGIN_NAME`.
- **Salida:** lo que el plugin imprime va al log de PyBall, bajo
  `pyball.plugins.<nombre>`.
- **Caídas:** un plugin que termina se arranca otra vez tras 1 s, luego 2 s, 4 s, ...
  hasta 60 s; uno que llevaba un minuto en marcha vuelve tras 1 s. PyBall sigue
  funcionando.
- **Apagado:** PyBall envía `SIGTERM` a cada plugin y, 10 s después, `SIGKILL` a los que
  sigan en marcha.

### La API de plugins

Un plugin habla con PyBall solo a través de `PYBALL_API_URL`, enviando
`Authorization: Bearer $PYBALL_API_TOKEN`. Cada llamada es una acción lógica y registra
un evento. El contrato completo, con cada petición y respuesta, es el esquema OpenAPI de
`/api/v1/openapi.json`, navegable en `/api/v1/docs`.

| Llamada | Scope | Qué hace |
|---|---|---|
| `GET /players` | `players:read` | Todos los jugadores |
| `GET /meetups/active` | `meetups:read` | El partido activo, con su capacidad y su búsqueda de suplentes |
| `POST /meetups` | `meetups:write` | Crea un partido; `location` y `capacity` son opcionales |
| `DELETE /meetups/{id}` | `meetups:write` | Cancela el partido activo |
| `PUT` / `DELETE /meetups/{id}/players/{player_id}` | `meetups:write` | Apunta o quita a un jugador |
| `PUT /meetups/{id}/lineup` | `meetups:write` | Fija la convocatoria y, con `team_algorithm` (`balanceado` o `random`), hace los equipos |
| `PUT /meetups/{id}/capacity` | `meetups:write` | Cambia la capacidad |
| `POST` / `DELETE /meetups/{id}/substitute-search` | `meetups:write` | Abre o cierra la búsqueda de suplentes |
| `GET /events` | `meetups:read` | El flujo de eventos, abajo |

### El flujo de eventos

`GET /api/v1/events` es un flujo de
[server-sent events](https://html.spec.whatwg.org/multipage/server-sent-events.html).
Cada evento tiene un `id`, su tipo como `event`, y un `data` JSON con el partido tal como
quedó justo después (ver [`data/events.jsonl`](data-directory.es.md#dataeventsjsonl) para
los tipos y campos). Para no perderse nada, un plugin guarda el último `id` que procesó y
se reconecta con `Last-Event-ID: <id>` (o `?after=<id>`): recibe todos los eventos
posteriores, en orden y sin duplicados, y luego los nuevos según ocurren. `?after=0`
reproduce todo el registro; sin ninguno de los dos, el flujo empieza en el siguiente
evento. Un flujo sin actividad envía un comentario cada 15 s.

## Ejecutar en Windows (WSL2)

Las imágenes Docker de PyBall son contenedores Linux; en Windows, la forma más
simple de ejecutarlas es dentro de WSL2 (Subsistema de Windows para Linux), donde
el resto de esta guía se aplica sin cambios.

1. **Activa WSL2.** Abre PowerShell como Administrador y ejecuta:

   ```powershell
   wsl --install
   ```

   Esto instala WSL2 y una distribución Ubuntu por defecto. Reinicia si se te pide.

2. **Instala [Docker Desktop para Windows](https://www.docker.com/products/docker-desktop/).**
   Su instalador detecta WSL2 y activa la integración por defecto — no hace falta
   instalar Docker Engine a mano dentro de la distribución.

3. **Abre la app "Ubuntu"** desde el menú Inicio — es una terminal WSL2 normal.
   Docker Desktop comparte su daemon con ella, así que todos los comandos
   `docker`/`docker compose` de esta guía funcionan tal cual desde aquí, empezando
   en [el paso 2, "Genera un espacio de trabajo"](#2-genera-un-espacio-de-trabajo).

4. Si la aplicación necesita seguir accesible (p. ej. durante un partido),
   desactiva la suspensión de Windows durante ese tiempo: Configuración → Sistema →
   Pantalla y suspensión.

Consulta [docs/deployment.es.md](deployment.es.md) para exponer esta instancia
fuera de la red local del PC.

## Siguientes pasos

- [docs/workflow.es.md](workflow.es.md) — el ciclo de vida completo de un partido: crear
  el partido, generar equipos, los formatos clásico y triangular, seguir el marcador, y
  estadísticas.
- [docs/data-directory.es.md](data-directory.es.md) — qué hay dentro de `data/`, y el
  formato JSON de cada archivo.
- [docs/deployment.es.md](deployment.es.md) — cómo exponer tu instancia fuera de tu
  red local (¿sin VPS? mira la opción de ngrok puntual).
