# Guía de instalación

🇬🇧 [English](setup.md) | 🇪🇸 Español

Esta guía cubre instalar, configurar y ejecutar PyBall como usuario final. Si quieres
construir PyBall desde el código fuente o contribuir, mira en su lugar la
[sección de Desarrollo del README principal](../README.es.md#desarrollo).

## 1. Elige una topología

PyBall se distribuye como dos imágenes Docker, construidas desde el mismo código:

| Imagen | Qué ejecuta | ¿Necesita un bot de Telegram? |
|---|---|---|
| `lulivi/pyball-web` | Solo FastAPI — páginas web `/manage` y `/match` | No |
| `lulivi/pyball-telegram` | Bot de Telegram + FastAPI (mismas páginas web) | Sí |

Si tu grupo no usa Telegram, o prefieres gestionarlo todo desde el navegador, usa
`pyball-web`: todas las funciones — crear partidos, generar equipos (clásico o
triangular), seguir un partido, cerrar una sesión triangular, ver estadísticas — están
disponibles desde `/manage` y `/match`. Usa `pyball-telegram` si quieres que las
convocatorias se publiquen automáticamente en un grupo, comandos de admin desde
Telegram, y reacciones/notificaciones en el chat.

## 2. Genera un espacio de trabajo

Elige un directorio vacío para la configuración y los datos de esta instancia, y ejecuta:

```bash
mkdir pyball && cd pyball
docker run --rm --user "$(id -u):$(id -g)" -v "$(pwd):/pyball" lulivi/pyball-web --bootstrap
# o:
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

### `[pyball.core]` — ambas topologías

| Clave | Descripción | Por defecto |
|---|---|---|
| `location` | Ubicación por defecto del partido | *(obligatorio)* |
| `name` | Nombre de la instancia mostrado en la interfaz | *(obligatorio)* |
| `default_week_day` | Día por defecto (`monday`–`sunday`) para nuevos partidos | `wednesday` |
| `default_hour` | Hora de inicio por defecto (`HH:MM`) | `20:00` |
| `display_date_format` | Formato de fecha usado en los mensajes | `%Y-%m-%d %H:%M` |
| `team_colors` | Tres nombres de color: los dos primeros son los equipos del partido clásico, el tercero solo se usa en triangulares | `["blanco", "negro", "rojo"]` |
| `base_url` | URL pública usada para construir el enlace de `/match` | *(obligatorio)* |
| `api_port` | Puerto del servidor HTTP | `8000` |
| `locale` | Locale usado para ordenar los nombres de jugadores | `es_ES.UTF-8` |
| `data_dir` | Directorio para los archivos de datos JSON | `data` |
| `match_token` | Token de acceso solo para `/match` (opcional, ver [Tokens de acceso](#6-tokens-de-acceso)) | *(vacío)* |
| `manage_token` | Token de acceso para todo, incluyendo `/manage` (opcional) | *(vacío)* |
| `theme_color` | Color de tema/fondo de la PWA | `#0f172a` |
| `icons_dir` | Directorio de iconos PWA personalizados (opcional) | *(vacío)* |

Colores de equipo disponibles: `blanco` `negro` `rojo` `naranja` `amarillo` `verde`
`azul` `morado` `marron`.

### `[pyball.telegram]` y subsecciones — solo `pyball-telegram`

Estas claves se ignoran en `pyball-web` — ver
[la configuración de Telegram es solo para el bot](data-directory.es.md#la-configuración-de-telegram-es-solo-para-el-bot)
para saber por qué.

| Clave | Descripción |
|---|---|
| `telegram.bot_token` | Token del bot desde [@BotFather](https://t.me/BotFather) |
| `telegram.admins_ids` | IDs de usuario de Telegram autorizados a ejecutar comandos de admin |
| `telegram.regulars.chat_id` | ID del chat de grupo principal (número negativo para grupos) |
| `telegram.regulars.meetups_thread_id` | Hilo de foro para los mensajes de convocatoria (vacío para desactivar) |
| `telegram.regulars.stats_thread_id` | Hilo de foro para las estadísticas post-partido (vacío para desactivar) |
| `telegram.substitutes.chat_id` | ID del chat de grupo de suplentes (número negativo para grupos) |
| `telegram.management.chat_id` | ID del canal de log operacional (`0` para desactivar) |

Para encontrar un ID de chat: añade el bot al grupo, envía cualquier mensaje, y luego
consulta `https://api.telegram.org/bot<TOKEN>/getUpdates` buscando el campo `chat.id`.

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

Ver [docs/workflow.es.md](workflow.es.md) para el flujo completo paso a paso.

## 6. Tokens de acceso

`match_token` y `manage_token` protegen la aplicación cuando se expone fuera de tu
propia red (ej. vía [Tailscale Funnel](https://tailscale.com/kb/1223/funnel)) — sin
ellos, `/manage` y `/match` quedan abiertos a cualquiera que llegue a la URL. Si ambos
se dejan vacíos, no se aplica ninguna autenticación (correcto para una red privada en
la que ya confías).

| Ruta | Token requerido |
|---|---|
| `/`, archivos estáticos, manifiestos PWA | Ninguno (siempre público) |
| `/match`, `GET /api/match/active`, `POST /api/match/finish` | `match_token` **o** `manage_token` |
| `/manage` y todo lo demás bajo `/api/*` | Solo `manage_token` |

Dale el `match_token` (solo marcador) a un dispositivo que solo deba ver `/match` (ej.
una tablet montada en el campo), y el `manage_token` a los admins. Visitar una URL con
`?token=<valor>` una vez valida el token y guarda una cookie `HttpOnly` que dura un
año — no hace falta volver a pasar el token en ese mismo dispositivo/navegador.

## 7. Actualizar

```bash
docker compose pull
docker compose up -d
```

Fija una versión concreta en vez de seguir siempre `latest` poniendo `TAG=4.13.0` en
`.env`.

## Siguientes pasos

- [docs/workflow.es.md](workflow.es.md) — el ciclo de vida completo de un partido: crear
  el partido, generar equipos, los formatos clásico y triangular, seguir el marcador, y
  estadísticas.
- [docs/data-directory.es.md](data-directory.es.md) — qué hay dentro de `data/`, y el
  formato JSON de cada archivo.
