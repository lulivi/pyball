# siesta

🇬🇧 [English](README.md) | 🇪🇸 Español

siesta decide, de forma justa, quién descansa cuando se apuntan más jugadores de los que
caben en un partido, y hace los equipos. Es un [plugin incluido](../README.es.md#plugins-incluidos):
todas las imágenes de PyBall lo traen y se ejecuta en cuanto lo declaras.

## La regla

Los jugadores se ordenan por cuántas veces han descansado ya, de menos a más, con un
orden aleatorio entre iguales. Los primeros que hagan falta descansan y suman +1 en la
lista de siesta.

Así, un fijo que ya descansó queda protegido hasta que todos los demás apuntados esa
semana hayan descansado las mismas veces. Cuando todos están igualados es un sorteo
aleatorio, pero los contadores nunca se reinician. Un fijo nuevo en la lista empieza en
el contador más bajo del momento, para que no descanse semana tras semana hasta
alcanzar a los demás. La lista solo muestra a los jugadores `regular`.

## El sorteo semanal

A la hora programada (lunes a las 10:00, Europe/Madrid, por defecto) siesta sortea sobre
el partido activo, según su capacidad:

- **Más apuntados que la capacidad:** el exceso descansa según la regla, y el resto
  tiene sus equipos.
- **Justo la capacidad:** nadie descansa; se hacen los equipos (los hechos a mano se
  mantienen).
- **Menos que la capacidad:** siesta abre la búsqueda de suplentes. Cuando la búsqueda
  se cierra con la convocatoria llena, siesta hace los equipos; nadie tiene que ejecutar
  nada.

Cada sorteo se publica en Telegram: quién descansa, los equipos y la lista de siesta.

Un partido se sortea como mucho una vez. Si PyBall o siesta estaban parados a la hora
programada, el sorteo se hace cuando siesta vuelve a arrancar; nunca se hace dos veces.
En el primer arranque siesta solo recuerda la última hora programada, así que
instalarlo nunca sortea en el momento: para eso está `siesta draw`. Un partido creado
después de la hora programada espera a la siguiente.

## Actívalo

Añade su tabla a `config.toml` y reinicia PyBall:

```toml
[pyball.plugins.siesta]
command = ["siesta", "run"]
scopes = ["players:read", "meetups:read", "meetups:write"]
telegram_bot_token = "123456789:ABCdefGHIjklMNOpqrsTUVwxyz"
telegram_chat_id = -1001234567890
```

| Clave | Descripción | Por defecto |
|---|---|---|
| `command`, `scopes` | Como arriba: cómo lo arranca PyBall y qué puede hacer | — |
| `weekday` | Día del sorteo, en inglés: `monday` ... `sunday` | `monday` |
| `time` | Hora del sorteo, `HH:MM` | `10:00` |
| `timezone` | Zona horaria de `weekday` y `time`, un nombre IANA | `Europe/Madrid` |
| `team_algorithm` | Cómo se hacen los equipos: `balanceado` o `random` | `balanceado` |
| `telegram_bot_token` | Bot que publica el sorteo; puede ser el mismo bot que el de PyBall | ninguno |
| `telegram_chat_id` | Chat del sorteo (negativo para grupos) | ninguno |
| `telegram_message_thread_id` | Tema del foro para el sorteo (`0` o vacío = el chat principal) | ninguno |

Sin `telegram_bot_token` y `telegram_chat_id`, el mensaje va al log de PyBall. Estas
claves no admiten variables de entorno.

## Comandos

Además de `run`, que arranca PyBall, siesta tiene comandos para ejecutar a mano dentro
del contenedor, desde el espacio de trabajo. Hablan con la API de plugins con el
`manage_token`:

```bash
docker compose exec -e PYBALL_API_TOKEN=<manage_token> pyball siesta status
```

(El servicio se llama `bot` en un espacio de trabajo de `pyball-telegram`.)

| Comando | Qué hace |
|---|---|
| `status` | Muestra la lista de siesta y el último sorteo. |
| `draw [--dry-run]` | Sortea ahora sobre el partido activo. `--dry-run` muestra el mensaje y no cambia nada. |
| `reinstate <jugador> --instead-of <quién>` | Alguien se baja: `<quién>` sale del partido y `<jugador>`, que se había quedado fuera, ocupa su sitio y recupera su +1. Se rehacen los equipos y se avisa al grupo. Omite `--instead-of` si el que se baja ya no está. |
| `set <jugador> <n>` | Fija a mano el contador de un fijo. |

Los nombres se reconocen sin importar mayúsculas ni tildes, y basta con un comienzo de
nombre que no se repita (`reinstate ivan --instead-of jose m`).

## Sus datos

siesta guarda su lista en `data/plugins/siesta/state.json`: el contador de cada fijo,
todos los sorteos y por dónde iba en el calendario y en el flujo de eventos. Solo guarda
IDs de jugadores y partidos; los nombres vienen siempre de PyBall, así que renombrar a
un jugador no cambia nada.
