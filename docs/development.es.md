# Guía de desarrollo

🇬🇧 [English](development.md) | 🇪🇸 Español

Cómo está organizado el código de PyBall: sus capas, cómo arranca un proceso y las dos
topologías ejecutables. Para preparar un entorno de desarrollo, ejecutar las
comprobaciones y las convenciones de commits y pull requests, consulta
[CONTRIBUTING.es.md](../CONTRIBUTING.es.md).

## Capas

PyBall sigue una arquitectura limpia con límites de capa estrictos:

```
pyball/
├── domain/            # Modelos e interfaces de repositorio — no depende de otra capa
│   ├── player/
│   └── meetup/        #   Meetup, Match, Team, ... y las reglas de ronda del triangular
├── application/       # Casos de uso — un archivo por acción, con repositorios inyectados
│   ├── player/
│   └── meetup/        #   create_meetup, create_teams, finish_match, close_meetup, ...
├── infrastructure/    # Implementaciones concretas de las interfaces del dominio
│   ├── persistence/   #   Repositorios JSON
│   ├── images/        #   Renderizado de la imagen de estadísticas (WeasyPrint + Jinja2)
│   ├── signup/        #   Códigos personales de inscripción
│   ├── telegram/      #   Bot de Telegram, configuración, notificaciones
│   └── http/          #   App FastAPI, rutas, autenticación por token, páginas web estáticas
├── cmd/               # Un punto de entrada por topología — su Composition Root
└── settings.py        # AppSettings y el cargador de config.toml
```

- `domain/` no importa nada de las otras capas.
- `application/` contiene un caso de uso por archivo. Las piezas compartidas de la
  aplicación están en su nivel superior: `bootstrap.py`, el contenedor de dependencias, la
  interfaz `MatchNotifier` e `init_workspace.py` (el generador del espacio de trabajo de
  `--bootstrap`).
- `infrastructure/http/static/` y `static_signup/` son HTML y JavaScript sin más, sin
  paso de compilación.

Fuera de `pyball/`:

- `scripts/` — scripts de migración de datos puntuales y autocontenidos. `pyball/` no los
  importa; se ejecutan a mano cuando cambia el formato de un JSON guardado.
- `docs/` — documentación para el usuario, en inglés y español.

## Arranque

`bootstrap_core()` (en `application/bootstrap.py`) carga `AppSettings`, configura los
logs, fija el locale y construye el contenedor de dependencias. Cada `cmd/run_*.py` es el
Composition Root de su topología: llama a `bootstrap_core()`, carga la configuración
propia de la integración, conecta los componentes de infraestructura y gestiona el
apagado ordenado.

Los dos puntos de entrada aceptan también `--bootstrap`, que solo genera un espacio de
trabajo de despliegue (`config.toml`, `compose.yaml`, `.env`, ...) y termina. Nunca toca
una aplicación en marcha.

## Topologías

Un mismo código se ejecuta como dos topologías:

- **`pyball`** (`cmd/run_pyball.py`): solo FastAPI. Siempre sirve `/manage` y `/match`;
  `/signup` se activa con `enable_web_signup` en `config.toml`.
- **`pyball-telegram`** (`cmd/run_telegram.py`): el bot de Telegram más FastAPI sirviendo
  `/manage` y `/match` (sin `/signup`), ambos en el mismo bucle de eventos de asyncio.
  Solo esta topología necesita tener instalado `python-telegram-bot`.

Todas las funciones son accesibles solo con `/manage` y `/match`, en cualquiera de las dos
topologías. Telegram y `/signup` son capas de comodidad sobre los mismos casos de uso,
nunca un requisito: un administrador siempre puede añadir, quitar o mover a un jugador
entre equipos desde `/manage`, sin que ningún jugador visite `/signup` y sin ningún bot de
Telegram configurado.

## Formatos de partido

Un partido tiene 2 o 3 equipos. Con 2 equipos es un único partido clásico, que se cierra
con su propio resultado. Con 3 equipos es un triangular: el dominio calcula cada
siguiente emparejamiento según un reglamento fijo, y el partido sigue abierto entre
rondas hasta que se cierra explícitamente. Consulta [workflow.es.md](workflow.es.md) para
las reglas completas y el ciclo de vida.
