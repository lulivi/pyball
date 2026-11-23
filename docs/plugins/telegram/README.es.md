# telegram

🇬🇧 [English](README.md) | 🇪🇸 Español

telegram es el bot de Telegram de PyBall: publica la convocatoria de cada partido en el
chat de titulares con los botones "✔ Unirse" / "✖ Salir", llama a los suplentes cuando
se abre una búsqueda de suplentes, mantiene los dos mensajes al día, publica el
resultado y las estadísticas tras cada partido y atiende los comandos de administración.
Es un [plugin incluido](../README.es.md#plugins-incluidos): viene en la imagen
de PyBall y funciona en cuanto lo declaras. Todo lo que hace se puede hacer también
desde `/manage` y `/match`.

## Qué publica

- **Convocatoria de titulares** — al crear un partido: su fecha, lugar y jugadores, con
  los botones para unirse o salir. Se edita con cada cambio: los equipos, el último
  marcador de cada equipo y, al cerrarse, el resumen del resultado que copia `/manage`.
  Los botones desaparecen en cuanto hay equipos.
- **Convocatoria de suplentes** — al abrirse una búsqueda de suplentes: los suplentes
  apuntados y los botones, mientras la búsqueda siga abierta.
- **Cancelación** — los mensajes de un partido cancelado se marcan con 🚫 *CANCELADO*.
- **Resultado corregido** — un resultado editado tras cerrar el partido se publica como
  un mensaje nuevo.
- **Estadísticas** — tras cada partido, y tras cada resultado corregido, la imagen de
  estadísticas de la temporada va al chat de estadísticas, si hay uno.

Los botones funcionan para los jugadores vinculados a su usuario de Telegram con
`/player_link`. Si el plugin está parado, se pone al día con lo que se perdió cuando
vuelve a arrancar; la primera vez que arranca solo actúa sobre lo que pase desde entonces.

## Comandos

Cada comando `player_` y `meetup_` responde también a un alias corto: `p_link`,
`m_show`, ...

| Comando | Quién | Qué hace |
|---|---|---|
| `/help` | Cualquiera | Lista los comandos |
| `/player_link <nombre>, <telegram_id>` | Administradores | Vincula un usuario de Telegram a un jugador, buscando el nombre de forma aproximada |
| `/player_unlink <nombre>` | Administradores | Quita el vínculo del jugador |
| `/meetup_show [fecha]` | Administradores | Vuelve a publicar la convocatoria, del partido activo o del de esa fecha (escrita con `display_date_format`) |
| `/meetup_stats temporada\|historico` | Administradores | Envía al chat la imagen de estadísticas de la temporada o de siempre |

## Activarlo

Añade su tabla a `config.toml` y reinicia PyBall:

```toml
[pyball.plugins.telegram]
command = ["telegram"]
scopes = ["players:read", "meetups:read", "meetups:write"]
bot_token = "123456789:ABCdefGHIjklMNOpqrsTUVwxyz"
admins_ids = [123456789]

[pyball.plugins.telegram.regulars.meetups]
chat_id = -1001234567890

[pyball.plugins.telegram.regulars.stats]
chat_id = -1001234567890
message_thread_id = 2

[pyball.plugins.telegram.substitutes.meetups]
chat_id = -1009876543210
```

| Clave | Descripción | Obligatoria |
|---|---|---|
| `command`, `scopes` | Como arriba: cómo lo arranca PyBall y qué puede hacer | **Sí** |
| `bot_token` | Token del bot de [@BotFather](https://t.me/BotFather) | **Sí** |
| `admins_ids` | IDs de usuario de Telegram que pueden usar los comandos de administración | **Sí** |
| `regulars.meetups.chat_id` | Chat de la convocatoria de titulares y de los resultados corregidos (negativo para grupos) | **Sí** |
| `regulars.meetups.message_thread_id` | Tema del foro para esos mensajes (vacío = ninguno) | No |
| `regulars.stats.chat_id` | Chat de las estadísticas tras cada partido (`0` o sin poner = no se publican) | No |
| `regulars.stats.message_thread_id` | Tema del foro para las estadísticas (vacío = ninguno) | No |
| `substitutes.meetups.chat_id` | Chat de la convocatoria de suplentes (negativo para grupos) | **Sí** |
| `substitutes.meetups.message_thread_id` | Tema del foro para la convocatoria de suplentes (vacío = ninguno) | No |

Para encontrar el ID de un chat: añade el bot al grupo, envía cualquier mensaje y mira
el campo `chat.id` en `https://api.telegram.org/bot<TOKEN>/getUpdates`. Cada chat puede
ser el mismo grupo u otro distinto. Estas claves no tienen variables de entorno. Las
fechas se escriben con el `display_date_format` del club y los nombres se ordenan según
su `locale`.

## Sus datos

En `data/plugins/telegram/`:

- `messages.json` — qué mensaje muestra cada partido en cada chat, para poder editarlo:
  `{"2026-04-15T20:00": {"regular": {"chat_id": -100..., "thread_id": null, "message_id": 4521}}}`.
  Las entradas de un partido se borran al cerrarse o cancelarse.
- `telegram-uuid.json` — los vínculos hechos con `/player_link`, de ID de usuario de
  Telegram a ID de jugador: `{"123456789": "11111111-..."}`.
- `last_event_id` — el último evento atendido, desde donde sigue tras reiniciarse.
