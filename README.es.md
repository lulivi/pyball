# PyBall

🇬🇧 [English](README.md) | 🇪🇸 Español

Gestor autoalojado de partidos de fútbol: organiza partidos recurrentes, genera equipos
equilibrados, registra resultados y consulta estadísticas de temporada — desde el
navegador del móvil, opcionalmente junto a un bot de Telegram.

## Ejecutar PyBall

La mayoría de gente solo quiere ejecutar la app. Lo único que necesitas es Docker.

```bash
mkdir pyball && cd pyball
docker run --rm --user "$(id -u):$(id -g)" -v "$(pwd):/pyball" lulivi/pyball --bootstrap
# o, para la página de alta por cuenta propia /signup:
docker run --rm --user "$(id -u):$(id -g)" -v "$(pwd):/pyball" lulivi/pyball-web --bootstrap
# o, para Telegram:
docker run --rm --user "$(id -u):$(id -g)" -v "$(pwd):/pyball" lulivi/pyball-telegram --bootstrap

# edita config.toml con tus valores y luego:
docker compose up -d
```

`--bootstrap` genera `config.toml`, `compose.yaml`, `.env` y los directorios
`data/`/`logs/` en la carpeta actual — consulta **[docs/setup.es.md](docs/setup.es.md)**
para la guía completa: elegir topología, configurar `config.toml`, para qué sirven
`/manage` y `/match`, y los tokens de acceso.

- **[docs/setup.es.md](docs/setup.es.md)** — instalar, configurar y ejecutar PyBall.
- **[docs/workflow.es.md](docs/workflow.es.md)** — cómo va un partido desde que se crea
  hasta las estadísticas finales, incluyendo los formatos clásico (2 equipos) y
  triangular (3 equipos).
- **[docs/data-directory.es.md](docs/data-directory.es.md)** — la estructura de
  directorios que crea PyBall y el formato de sus archivos JSON.

## Desarrollo

Construir PyBall desde el código fuente, ejecutar su suite de tests, o contribuir,
requiere más que Docker.

### Requisitos

- Python >= 3.11
- [uv](https://docs.astral.sh/uv/) para gestión de dependencias
- [nox](https://nox.thea.codes/en/stable/) para automatización

### Instalar

```bash
uv sync --all-extras
```

### Ejecutar desde el código fuente

```bash
uv run pyball --bootstrap       # solo la primera vez, genera config.toml
uv run pyball                   # /manage + /match, sin Telegram, sin /signup

uv run pyball-web --bootstrap
uv run pyball-web               # /manage + /match + /signup, sin Telegram

uv run pyball-telegram --bootstrap
uv run pyball-telegram          # /manage + /match + bot de Telegram
```

### Comprobaciones

```bash
make format      # Formatea el código (black + isort)
make lint        # Ejecuta todas las comprobaciones de lint
make test        # Ejecuta los tests con cobertura
```

### Bucle local con Docker

```bash
make up           # construye la imagen desde el código fuente y la ejecuta con Docker Compose
```

## Arquitectura

Arquitectura limpia con límites de capa estrictos:

- **domain/** — Modelos principales e interfaces de repositorio
- **application/** — Casos de uso con interfaces de repositorio inyectadas
- **infrastructure/** — Implementaciones concretas (persistencia JSON, Telegram, renderizado HTML)

## Licencia

MIT
