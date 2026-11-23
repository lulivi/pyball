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
│   ├── plugins/       #   API de plugins (/api/v1), registro de eventos, credenciales, supervisor
│   ├── alerts.py      #   Avisos y errores del núcleo enviados al chat de alertas
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

- `docs/` — documentación para el usuario, en inglés y español.
- `plugins/` — los plugins incluidos, una carpeta cada uno (ver [Plugins incluidos](#plugins-incluidos)).
- `clients/` — los clientes de la API de plugins que comparten los plugins incluidos, uno por
  lenguaje; ninguno es un plugin.

## Arranque

`bootstrap_core()` (en `application/bootstrap.py`) carga `AppSettings`, configura los
logs, fija el locale y construye el contenedor de dependencias. Cada `cmd/run_*.py` es el
Composition Root de su topología: llama a `bootstrap_core()`, carga la configuración
propia de la integración, conecta los componentes de infraestructura y gestiona el
apagado ordenado: los plugins arrancan cuando el servidor HTTP ya acepta conexiones, y se
paran primero, antes de cerrar los flujos de eventos y salir del servidor.

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

## Plugins

Un plugin es un programa aparte, en cualquier lenguaje, declarado en
`[pyball.plugins.<nombre>]`. Las dos topologías alojan los plugins igual:

- `PluginSupervisor` ejecuta cada uno como proceso hijo, lo reinicia con espera
  creciente cuando termina y lo para al apagar.
- `PluginCredentials` da a cada plugin un token bearer aleatorio en cada arranque,
  limitado a los permisos (scopes) que declara.
- `create_plugin_api()` sirve el contrato en `/api/v1`, una subaplicación FastAPI con su
  propio esquema OpenAPI. Sus rutas devuelven los modelos de `plugins/schemas.py`,
  separados de los presenters que usa `/manage`, así cada uno puede cambiar por su lado.
- `EventLogNotifier` escribe cada evento de `MatchNotifier` en `data/events.jsonl`, y
  `GET /api/v1/events` sirve ese registro como server-sent events. `pyball-telegram` lo
  pone delante del notificador de Telegram con `CompositeMatchNotifier`, así un fallo de
  Telegram nunca pierde un evento.

`plugins/schemas.py` y las rutas de `/api/v1` son el contrato de plugins, guardado en el
repositorio como `plugins/openapi.json`. Un cambio en cualquiera de ellos ejecuta
`make openapi` para regenerar ese fichero y actualiza los plugins que lo usan y
`docs/plugins/README.es.md`, todo en el mismo cambio; un test unitario falla mientras el
fichero guardado difiera de lo que sirve `create_plugin_api()`.

### Plugins incluidos

Un plugin incluido vive en `plugins/<nombre>/` en la raíz del repositorio, en cualquier
lenguaje, y usa solo la API de plugins, como cualquier otro plugin. Cada uno:

- tiene un `Makefile` con un objetivo `check` (su comprobación de formato, lint y tests,
  que falla ante cualquier error) y un objetivo `build` (una compilación release, para
  desarrollo local). Los `make plugins-check` y `make plugins-build` de la raíz los
  ejecutan para cada plugin, y el job `plugins` de la CI ejecuta `make plugins-check` en
  la imagen de CI, que lleva la herramienta de cada plugin;
- tiene su propia etapa en `docker/Dockerfile`, que lo instala en las dos imágenes fuera
  de `/pyball/plugins`, la carpeta que monta encima el espacio de trabajo: un binario va
  a `/usr/local/bin/<nombre>`, así `command = ["<nombre>", ...]` lo encuentra;
- comprueba, en su objetivo `check`, cada llamada que hace contra
  `plugins/openapi.json`: cada ruta que llama, los campos que lee con sus tipos y los
  cuerpos que envía;
- se documenta en `docs/plugins/<nombre>/README.es.md` (EN/ES) y aparece en
  `docs/plugins/README.es.md`.

`siesta` y `activity` están escritos en Rust: cada `rust-toolchain.toml` fija la misma
versión de Rust, y `docker/Dockerfile.ci` y sus etapas de `docker/Dockerfile` la usan también.

Un plugin en Rust habla con PyBall a través de `clients/pyball-client-rs`, una dependencia por
ruta: el cliente de la API de plugins y su flujo de eventos, la tabla `endpoints!` por la
que pasa cada llamada, la comprobación de esas llamadas contra `plugins/openapi.json`, y
el entorno, la tabla de `config.toml` y la carpeta `data/plugins/<nombre>/` de un plugin.
Cada plugin define sus propios tipos, solo con los campos que lee. `clients/pyball-client-rs`
tiene los mismos objetivos `check` y `build` y la misma versión de Rust, y la etapa de
`docker/Dockerfile` de cada plugin que lo usa también lo copia.

Un plugin en Python habla con PyBall a través de `clients/pyball-client-py`, una
dependencia por ruta de uv con las mismas piezas: un `Api` asíncrono sobre httpx y su flujo
de eventos, los `Endpoint` por los que pasa cada llamada, `contract.check_endpoints` contra
`plugins/openapi.json`, y las utilidades de `pyball_client.plugin`. Cada plugin define sus
propios modelos de pydantic, solo con los campos que lee. Su objetivo `check` ejecuta
black, isort, mypy, pylint y pytest.

## Formatos de partido

Un partido tiene 2 o 3 equipos. Con 2 equipos es un único partido clásico, que se cierra
con su propio resultado. Con 3 equipos es un triangular: el dominio calcula cada
siguiente emparejamiento según un reglamento fijo, y el partido sigue abierto entre
rondas hasta que se cierra explícitamente. Consulta [workflow.es.md](workflow.es.md) para
las reglas completas y el ciclo de vida.
