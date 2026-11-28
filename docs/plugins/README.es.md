# Plugins

🇬🇧 [English](README.md) | 🇪🇸 Español

Un plugin es un programa opcional y de larga duración, escrito en cualquier lenguaje, que
amplía PyBall sin tocar su código. Se ejecuta mientras PyBall esté en marcha, reaccionando
al flujo de eventos o con su propio calendario: una tarea que se ejecuta una vez y
termina va en cron.

Un plugin viene **incluido** en la imagen de PyBall o es un programa tuyo en la carpeta
`plugins/` del espacio de trabajo, que el `compose.yaml` generado monta en
`/pyball/plugins`. En los dos casos solo se ejecuta cuando `config.toml` lo declara (ver
[`[pyball.plugins.<nombre>]`](../setup.es.md#pyballpluginsnombre--plugins-opcionales)).
Luego arranca PyBall como siempre: sigue siendo un solo comando.

## Plugins incluidos

| Plugin | Qué hace | `command` |
|---|---|---|
| [activity](activity/README.es.md) | Publica en un chat de Telegram quién se apunta o se desapunta, y cada convocatoria creada, cerrada o cancelada | `["activity"]` |
| [siesta](siesta/README.es.md) | Decide de forma justa quién descansa cuando se apuntan más jugadores de los que caben en un partido, y hace los equipos | `["siesta", "run"]` |
| [telegram](telegram/README.es.md) | El bot de Telegram: convocatorias con botones para unirse o salir, la convocatoria de suplentes, resultados, estadísticas y comandos de administración | `["telegram"]` |

## Cómo ejecuta PyBall un plugin

PyBall ejecuta cada plugin declarado como proceso hijo, desde el espacio de trabajo:

- **Arranque:** cuando el servidor web ya está listo, con tres variables de entorno:
  `PYBALL_API_URL` (la API de plugins, p. ej. `http://127.0.0.1:8000/api/v1`),
  `PYBALL_API_TOKEN` (el token propio del plugin, nuevo en cada arranque) y
  `PYBALL_PLUGIN_NAME`.
- **Estado:** un plugin guarda lo que necesita recordar, como el último evento que
  procesó, en `data/plugins/<nombre>/`, y crea la carpeta él mismo. Esa carpeta está
  dentro del `data/` montado, así que sobrevive a los reinicios del contenedor y entra en
  tus copias de seguridad.
- **Salida:** lo que el plugin imprime va al log de PyBall, bajo
  `pyball.plugins.<nombre>`.
- **Caídas:** un plugin que termina se arranca otra vez tras 1 s, luego 2 s, 4 s, ...
  hasta 60 s; uno que llevaba un minuto en marcha vuelve tras 1 s. PyBall sigue
  funcionando.
- **Apagado:** PyBall envía `SIGTERM` a cada plugin y, 10 s después, `SIGKILL` a los que
  sigan en marcha.

## La API de plugins

Un plugin habla con PyBall solo a través de `PYBALL_API_URL`, enviando
`Authorization: Bearer $PYBALL_API_TOKEN`. Cada escritura es una acción lógica y registra
un evento. Cada equipo de un partido lleva el `color` y el `emoji` del club para su posición.
El contrato completo, con cada petición y respuesta y los datos de cada
evento, es el esquema OpenAPI de `/api/v1/openapi.json`, navegable en `/api/v1/docs`. El
mismo esquema está guardado en el repositorio como
[`plugins/openapi.json`](../../plugins/openapi.json), así un plugin puede generar un
cliente a partir de él o comprobar sus propios tipos sin un PyBall en marcha.

Una respuesta de error es un JSON con un texto `detail` que explica el motivo: `401` si
falta el token o es incorrecto, `403` si el token no tiene el permiso, `404` si el
partido no existe, `409` si el partido rechaza el cambio. Un `422` trae ese texto o,
cuando la petición no encaja con su esquema, la lista de campos erróneos de FastAPI.

| Llamada | Scope | Qué hace |
|---|---|---|
| `GET /settings` | cualquiera | El `display_date_format` y el `locale` del club |
| `GET /players` | `players:read` | Todos los jugadores |
| `GET /meetups/active` | `meetups:read` | El partido activo, con su capacidad y su búsqueda de suplentes |
| `GET /meetups?date=<fecha>` | `meetups:read` | El partido de esa fecha, como una lista de cero o uno |
| `GET /meetups/{id}/summary` | `meetups:read` | El resumen del resultado de un partido cerrado, el que copia `/manage` |
| `GET /stats.png?scope=season` | `meetups:read` | La imagen de estadísticas de la temporada, o de siempre con `scope=alltime` |
| `POST /meetups` | `meetups:write` | Crea un partido; `location` y `capacity` son opcionales |
| `DELETE /meetups/{id}` | `meetups:write` | Cancela el partido activo |
| `PUT` / `DELETE /meetups/{id}/players/{player_id}` | `meetups:write` | Apunta o quita a un jugador |
| `PUT /meetups/{id}/lineup` | `meetups:write` | Fija la convocatoria y, con `team_algorithm` (`balanceado` o `random`), hace los equipos |
| `PUT /meetups/{id}/capacity` | `meetups:write` | Cambia la capacidad |
| `POST` / `DELETE /meetups/{id}/substitute-search` | `meetups:write` | Abre o cierra la búsqueda de suplentes |
| `GET /events` | `meetups:read` | El flujo de eventos, abajo |

## El flujo de eventos

`GET /api/v1/events` es un flujo de
[server-sent events](https://html.spec.whatwg.org/multipage/server-sent-events.html).
Cada evento tiene un `id`, su tipo como `event`, y un `data` JSON con el partido tal como
quedó justo después (ver [`data/events.jsonl`](../data-directory.es.md#dataeventsjsonl)
para los tipos y campos). Para no perderse nada, un plugin guarda el último `id` que
procesó y se reconecta con `Last-Event-ID: <id>` (o `?after=<id>`): recibe todos los
eventos posteriores, en orden y sin duplicados, y luego los nuevos según ocurren.
`?after=0` reproduce todo el registro; sin ninguno de los dos, el flujo empieza en el
siguiente evento: llega todo evento escrito después del `200`. Un flujo sin actividad
envía un comentario cada 15 s.
