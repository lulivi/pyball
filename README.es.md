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

# edita config.toml con tus valores y luego:
docker compose up -d
```

`--bootstrap` genera `config.toml`, `compose.yaml`, `.env` y los directorios
`data/`, `logs/` y `plugins/` en la carpeta actual — consulta
**[docs/setup.es.md](docs/setup.es.md)** para la guía completa: configurar
`config.toml`, para qué sirven `/manage` y `/match`, los tokens de acceso y los plugins,
entre ellos el bot de Telegram.

- **[docs/setup.es.md](docs/setup.es.md)** — instalar, configurar y ejecutar PyBall.
- **[docs/workflow.es.md](docs/workflow.es.md)** — cómo va un partido desde que se crea
  hasta las estadísticas finales, incluyendo los formatos clásico (2 equipos) y
  triangular (3 equipos).
- **[docs/pages.es.md](docs/pages.es.md)** — un recorrido estructural por `/manage`,
  `/match` y `/signup`: sus pestañas, pantallas, y qué muestra cada una.
- **[docs/plugins/README.es.md](docs/plugins/README.es.md)** — plugins opcionales: los
  incluidos, como el sorteo justo de quién descansa, y cómo escribir los tuyos.
- **[docs/data-directory.es.md](docs/data-directory.es.md)** — la estructura de
  directorios que crea PyBall y el formato de sus archivos JSON.
- **[docs/deployment.es.md](docs/deployment.es.md)** — cómo exponer tu instancia
  fuera de tu red local (¿sin VPS? mira la opción de ngrok puntual).

## Desarrollo

Para construir PyBall desde el código fuente, ejecutar sus comprobaciones o contribuir,
consulta **[CONTRIBUTING.es.md](CONTRIBUTING.es.md)**. Para ver cómo está organizado el
código, consulta **[docs/development.es.md](docs/development.es.md)**.

## Licencia

MIT
