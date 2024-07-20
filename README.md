# PyBall Manager

PyBall consists in two main applications:

- Core
- Bot

The core holds the main functionality: manage players (create, delete, modify),
manage meetups (create, delete, add players, remove players, create matches).
The bot component serves as a wrapper of the core in Telegram.

## Usage

Run `make setup` to rename the [`sample.env`](./sample.env) file to `.env`. Then
fill it in with the proper values.

Now just run:

```bash
make up
```

## License

This project is released under [MIT](./LICENSE) license.
