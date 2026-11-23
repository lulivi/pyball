# PyBall

🇬🇧 English | 🇪🇸 [Español](README.es.md)

Self-hosted football (soccer) meetup manager: track recurring matches, build balanced
teams, record results, and see season stats — from a phone browser, optionally paired
with a Telegram bot.

## Running PyBall

Most people just want to run the app. All you need is Docker.

```bash
mkdir pyball && cd pyball
docker run --rm --user "$(id -u):$(id -g)" -v "$(pwd):/pyball" lulivi/pyball --bootstrap

# edit config.toml with your settings, then:
docker compose up -d
```

`--bootstrap` generates `config.toml`, `compose.yaml`, `.env`, and the `data/`, `logs/`
and `plugins/` directories in the current folder — see **[docs/setup.md](docs/setup.md)** for the full
walkthrough: configuring `config.toml`, what `/manage` and `/match` are for, access
tokens, and plugins, the Telegram bot among them.

- **[docs/setup.md](docs/setup.md)** — install, configure, and run PyBall.
- **[docs/workflow.md](docs/workflow.md)** — how a meetup goes from creation to
  finished stats, including the classic (2-team) and triangular (3-team) match formats.
- **[docs/pages.md](docs/pages.md)** — a structural tour of `/manage`, `/match`, and
  `/signup`: their tabs, screens, and what each one shows.
- **[docs/plugins/README.md](docs/plugins/README.md)** — optional plugins: the bundled
  ones, such as the fair sit-out draw, and how to write your own.
- **[docs/data-directory.md](docs/data-directory.md)** — the directory structure PyBall
  creates and the JSON file formats it uses.
- **[docs/deployment.md](docs/deployment.md)** — reaching your instance from outside
  your local network (no VPS? see the on-demand ngrok option).

## Development

To build PyBall from source, run its checks or contribute, see
**[CONTRIBUTING.md](CONTRIBUTING.md)**. For how the code is organised, see
**[docs/development.md](docs/development.md)**.

## License

MIT
