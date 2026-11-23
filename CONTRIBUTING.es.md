# Contribuir a PyBall

🇬🇧 [English](CONTRIBUTING.md) | 🇪🇸 Español

Cómo construir PyBall desde el código fuente, ejecutar sus comprobaciones y conseguir que
se integre un cambio. Para ver cómo está organizado el código, consulta
[docs/development.es.md](docs/development.es.md).

## Preparación

Necesitas:

- Python >= 3.11
- [uv](https://docs.astral.sh/uv/) para gestión de dependencias
- [rustup](https://rustup.rs/), solo para trabajar en los plugins de Rust de `plugins/`

```bash
uv sync                         # instala PyBall y sus herramientas de desarrollo
```

## Ejecutar desde el código fuente

```bash
uv run pyball --bootstrap       # solo la primera vez, genera config.toml
uv run pyball                   # /manage + /match y los plugins declarados; añade
                                # /signup con enable_web_signup = true en config.toml

make up                         # construye la imagen y la ejecuta con Docker Compose
```

## Comprobaciones

La CI ejecuta las sesiones de lint y tests y las comprobaciones de los plugins en cada
pull request; ejecútalas antes de hacer push:

```bash
make test        # alias: make t — suite completa de tests con cobertura
make lint        # alias: make l — black, isort, pydocstyle, pycodestyle, mypy, pylint
make format      # alias: make f — formatea el código (black + isort)
make plugins-check  # formato, lint y tests de cada plugin de plugins/
make plugins-build  # compilación release de cada plugin, para desarrollo local

# Un solo archivo de tests, o cualquier opción de pytest
uvx nox -e test -- tests/unit/domain/test_meetup.py -k test_name -v
```

El lint exige líneas de 99 caracteres como máximo y una puntuación de pylint de 10.00/10.

## Ramas

El trabajo de una issue de GitHub va en `<tipo>/gh-<n>[-<slug>]`, donde `<tipo>` es
`feature`, `fix` o `docs` y `<n>` es el número de la issue (p. ej.
`feature/gh-4-github-conventions`).

## Mensajes de commit

Los commits siguen [Conventional Commits](https://www.conventionalcommits.org/es/v1.0.0/).
El scope opcional nombra el área afectada (p. ej. `match`, `telegram`, `bootstrap`). La
última línea del cuerpo referencia la issue o issues de GitHub a las que pertenece el
commit, separadas por comas si hay varias:

```
type(scope): <descripción>

[cuerpo opcional]

[footer(s) opcional(es)]
Refs: #<n>[, #<m>...]
```

El job `release` del workflow `ci` de GitHub Actions etiqueta `main` a partir de estos
tipos:

- `feat` → versión minor
- `fix`, `perf` → versión patch
- footer `BREAKING CHANGE:` o `!` tras el tipo/scope (p. ej. `feat(match)!:`) → versión major
- `build`, `chore`, `ci`, `docs`, `refactor`, `style`, `test` → sin versión

## Pull requests

Las pull requests se integran con squash: el título de la PR se convierte en el asunto del
commit en `main`, así que debe seguir el formato de commit de arriba, y los mensajes de
commit de la rama forman su cuerpo, con sus líneas `Refs:`. La descripción de la PR
incluye `Closes #<n>` por cada issue que resuelve, para que GitHub las cierre al
integrarla.
