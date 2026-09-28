# Directorio de datos

🇬🇧 [English](data-directory.md) | 🇪🇸 Español

Este documento describe la estructura del espacio de trabajo que crea `--bootstrap` y
el formato de los archivos JSON que PyBall lee y escribe. Útil si quieres hacer copia
de seguridad de tus datos, inspeccionarlos directamente, o migrarlos a otro sitio.

## Estructura del espacio de trabajo

Después de ejecutar `--bootstrap` (ver [docs/setup.es.md](setup.es.md)), tu directorio
de trabajo queda así:

```
pyball/
├── config.toml       # tu configuración
├── compose.yaml       # definición del servicio de docker compose
├── .env               # UID/GID/PORT/TAG
├── README.md          # enlace corto de vuelta a docs/setup.es.md
├── data/
│   ├── players.json   # todos los jugadores, independientemente del partido
│   ├── legacy_stats.json   # opcional — asistencias históricas de antes de usar PyBall
│   ├── meetups/
│   │   ├── 2026-04-15T20:00.json
│   │   ├── 2026-04-22T20:00.json
│   │   └── ...         # un archivo por partido, nombrado según su fecha/hora
│   ├── signup/
│   │   └── codes.json   # solo si enable_web_signup está activo — ver más abajo
│   └── bot/
│       └── messages.json   # solo pyball-telegram — ver más abajo
└── logs/
    └── ...             # archivos de log de la aplicación
```

Cada archivo es JSON plano, escrito con sangrado de 2 espacios, seguro de leer (o incluso
editar a mano, con cuidado) con cualquier editor de texto.

## `data/players.json`

Un único archivo compartido que lista a todos los jugadores creados alguna vez,
independientemente de cualquier partido:

```json
{
  "players": [
    { "id": "11111111-1111-4111-8111-111111111111", "name": "Juan Pérez", "group": "regular", "position": "defensa" },
    { "id": "22222222-2222-4222-8222-222222222222", "name": "Manu García", "group": "substitute", "position": null }
  ]
}
```

- `id` — un UUID, generado al crear el jugador.
- `name` — nombre visible, usado en todas partes (interfaz, mensajes de Telegram,
  coincidencia difusa de la convocatoria).
- `group` — `"regular"` o `"substitute"`, el grupo por defecto usado al parsear una
  convocatoria.
- `position` — `"portero"`, `"defensa"`, `"centrocampista"`, `"delantero"`, o `null` si
  no se ha fijado. Una posición orientativa, no una asignación rígida — solo se usa como
  señal por el algoritmo de generación de equipos equilibrados (ver
  [docs/workflow.es.md](workflow.es.md#3-generar-equipos)).

## `data/meetups/<fecha>.json`

Un archivo por partido, nombrado según su fecha y hora en formato `YYYY-MM-DDTHH:MM`
(los dos puntos de la hora se mantienen tal cual, es un nombre de archivo, no una URL).
Su forma depende de si ya se han asignado equipos, y de si es un partido clásico o
triangular — pero siempre es el mismo esquema, solo con más campos rellenos a medida
que avanza el partido.

Un partido **triangular** (3 equipos) terminado, tras 3 rondas y cerrado:

```json
{
  "id": "a1b2c3d4-0000-4000-8000-000000000001",
  "date": "2026-07-08T20:00:00",
  "location": "Parque Central",
  "players": ["11111111-...", "22222222-...", "..."],
  "teams": [
    { "name": "A", "players": ["11111111-...", "22222222-...", "33333333-..."], "goalkeeper": "11111111-..." },
    { "name": "B", "players": ["44444444-...", "55555555-...", "66666666-..."], "goalkeeper": null },
    { "name": "C", "players": ["77777777-...", "88888888-...", "99999999-..."], "goalkeeper": null }
  ],
  "matches": [
    {
      "teams_playing": ["A", "B"],
      "result": {
        "score_a": 2,
        "score_b": 0,
        "events": [
          {
            "scorer_id": "11111111-...",
            "assistant_id": "22222222-...",
            "team": "A",
            "timestamp": "20:03:00",
            "is_own_goal": false
          }
        ]
      }
    },
    { "teams_playing": ["A", "C"], "result": { "score_a": 1, "score_b": 1, "events": [] } },
    { "teams_playing": ["C", "B"], "result": { "score_a": 2, "score_b": 1, "events": [] } }
  ],
  "closed": true
}
```

Notas de los campos:

- `players` — todos los convocados a este partido, hayan acabado o no en un equipo (un
  suplente que nunca se asignó a un equipo sigue apareciendo aquí).
- `teams` — `null` hasta que se generan los equipos. Una lista de 2 (clásico) o 3
  (triangular) equipos con nombre. Los nombres son siempre `"A"`, `"B"` y (en
  triangulares) `"C"` — son etiquetas posicionales, no los nombres de color visibles
  configurados en `team_colors`. El `goalkeeper` de cada equipo es el id de su portero
  designado para toda la sesión, o `null` si no se fijó ninguno — ver
  [docs/workflow.es.md](workflow.es.md#3-generar-equipos).
- `matches` — empieza como `[]`. Cada entrada es un partido jugado (o en curso) entre
  exactamente 2 de los equipos del meetup. `teams_playing` referencia los equipos por
  nombre, no por índice, así que reordenar `teams` nunca rompe las referencias de un
  partido. `result` es `null` mientras el partido sigue en curso (sin resultado
  registrado todavía); un meetup siempre tiene como mucho un partido con
  `result: null` a la vez — el que se muestra actualmente en `/match`.
  - Un partido **clásico** solo tiene nunca una entrada en `matches`.
  - Un partido **triangular** acumula una entrada por ronda jugada, en orden, y el par
    de equipos en `teams_playing` rota automáticamente según las reglas descritas en
    [docs/workflow.es.md](workflow.es.md#las-reglas-del-triangular).
- `events` — una entrada por gol, en el orden en que se marcaron. `team` es `"A"` o
  `"B"` **relativo al `teams_playing` de ese partido**, no a la lista `teams` general
  del meetup (esto importa en un triangular, donde un equipo que juega como lado "B" en
  una ronda puede jugar como "A" en la siguiente).
- `closed` — `true` cuando el meetup está completamente terminado. Un partido clásico se
  cierra solo en cuanto su único partido recibe un resultado; un triangular sigue
  abierto a través de varias rondas hasta que se cierra explícitamente (ver
  [docs/workflow.es.md](workflow.es.md#5-cerrar-una-sesión-triangular)).

## `data/legacy_stats.json` (opcional)

Solo hace falta si tu grupo llevaba las asistencias antes de adoptar PyBall y quiere que
ese histórico se sume a las estadísticas de temporada. Que no exista es perfectamente
correcto — PyBall lo trata igual que un archivo vacío:

```json
{
  "players": {
    "11111111-1111-4111-8111-111111111111": {
      "assists_by_match": [
        { "date": "2026-04-15T20:00:00", "count": 2 }
      ]
    }
  }
}
```

## El alta web es opcional mediante `enable_web_signup`

El directorio `data/signup/` de abajo solo existe cuando `enable_web_signup` está
activo (`true`) en `config.toml`. Si se deja en `false` (por defecto), o en
`pyball-telegram`, nada lo lee ni lo escribe.

### `data/signup/codes.json`

Una entrada por cada jugador al que se le ha dado un código personal de alta, indexada
por su id:

```json
{
  "11111111-1111-4111-8111-111111111111": {
    "salt": "3f9c2a1b8e7d4f605a3c9b8e1d7f6042",
    "hash": "8e1a9c3f7b2d6e405c1a8f9b3d7e6042c1a8f9b3d7e6042c1a8f9b3d7e60428e"
  }
}
```

- `salt` — bytes aleatorios propios de cada jugador (en hex), generados de nuevo cada
  vez que se fija un código.
- `hash` — el hash PBKDF2-HMAC-SHA256 del código con ese salt (200.000 iteraciones).

Los códigos nunca se guardan en texto plano, así que un código existente nunca se puede
recuperar de este archivo — solo regenerar (el botón "Regenerar código" de la fila de un
jugador en `/manage`, o automáticamente la primera vez que se crea un jugador con
`enable_web_signup` activo; ver [docs/workflow.es.md](workflow.es.md)). Este archivo se crea
automáticamente la primera vez que hace falta, y es seguro borrarlo: hacerlo simplemente
invalida el código de todos los jugadores, obligando a generarles uno nuevo a cada uno.

## La configuración de Telegram es solo para el bot

La sección `[pyball.telegram]` de `config.toml`, y el directorio `data/bot/` de más
abajo, solo existen para la topología `pyball-telegram`. Ejecutar `pyball` (con o sin
`enable_web_signup`) nunca lee ni escribe ninguno de los dos — ese despliegue no tiene
directorio `data/bot/` en absoluto.

### `data/bot/messages.json`

Rastrea qué mensaje de Telegram (en los chats de titulares/suplentes) corresponde a la
convocatoria de cada partido, para que PyBall pueda editarlo o borrarlo más tarde (ej.
cuando cambia la convocatoria, o cuando el partido se cierra):

```json
{
  "2026-04-15T20:00": {
    "regular": { "chat_id": -1000000000000, "thread_id": null, "message_id": 4821 },
    "substitute": {
      "chat_id": -1000000000001,
      "thread_id": null,
      "message_id": 512,
      "search_target": 12
    }
  }
}
```

La clave es la fecha/hora del partido (`YYYY-MM-DDTHH:MM`, coincidiendo con el nombre
del archivo del meetup sin la extensión `.json`). `thread_id` es `null` a menos que el
chat use temas de foro (ver `telegram.regulars.meetups.message_thread_id` en
[docs/setup.es.md](setup.es.md); la entrada `substitute` toma igualmente
`telegram.substitutes.meetups.message_thread_id`). `search_target` (solo en la entrada
`substitute`) es el tamaño de plantilla que busca una búsqueda de suplentes abierta;
`null` o su ausencia significa que la búsqueda está cerrada.

## Documentación relacionada

- [docs/setup.es.md](setup.es.md) — instalar, configurar y ejecutar PyBall.
- [docs/workflow.es.md](workflow.es.md) — el ciclo de vida del partido que registran
  estos archivos.
