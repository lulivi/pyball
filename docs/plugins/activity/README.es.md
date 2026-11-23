# activity

🇬🇧 [English](README.md) | 🇪🇸 Español

activity publica la actividad de las convocatorias en un chat de Telegram: quién se
apunta o se desapunta, y cada convocatoria que se crea, se cierra o se cancela. Es un
[plugin incluido](../README.es.md#plugins-incluidos): todas las imágenes de PyBall lo
traen, y se ejecuta cuando lo declaras, con o sin el bot de Telegram.

## Los mensajes

Un mensaje por evento:

| Evento | Mensaje |
|---|---|
| Un jugador se apunta | ✅ **Alta** — `Ana` se apunta como titular a la convocatoria del `2026-11-25 20:00`. |
| Un jugador se desapunta | ❌ **Baja** — `Ana` se desapunta como suplente de la convocatoria del `2026-11-25 20:00`. |
| Se crea una convocatoria | 🆕 **Convocatoria creada** — nueva convocatoria para el `2026-11-25 20:00`. |
| Se cierra una convocatoria | 🏁 **Convocatoria cerrada** — la convocatoria del `2026-11-25 20:00` ha finalizado. |
| Se cancela una convocatoria | 🚫 **Convocatoria cancelada** — se ha cancelado la convocatoria del `2026-11-25 20:00`. |

Cada mensaje se publica una vez y en orden. Si activity está parado, o no se puede llegar
a Telegram, publica lo que se perdió cuando vuelve a ejecutarse: un mensaje que falla
para el plugin, PyBall lo arranca de nuevo (ver
[Cómo ejecuta PyBall un plugin](../README.es.md#cómo-ejecuta-pyball-un-plugin)) y vuelve a
intentarlo desde ese mensaje. Cada uno de esos reinicios es también una
[alerta](../../setup.es.md#pyballalertstelegram--alertas-todas-las-topologías).

El primer arranque solo publica lo que pasa a partir de entonces, no las convocatorias
anteriores.

## Actívalo

Añade su tabla a `config.toml` y reinicia PyBall:

```toml
[pyball.plugins.activity]
command = ["activity"]
scopes = ["meetups:read"]

[pyball.plugins.activity.telegram]
bot_token = "123456789:ABCdefGHIjklMNOpqrsTUVwxyz"
chat_id = -1001234567890
```

| Clave | Descripción | Por defecto |
|---|---|---|
| `command`, `scopes` | Como arriba: cómo lo arranca PyBall y qué puede hacer | — |
| `telegram.bot_token` | Bot que publica la actividad; puede ser el mismo bot que el de PyBall | ninguno; obligatorio con un `chat_id` |
| `telegram.chat_id` | Chat de la actividad (negativo para grupos; `0` = ninguno) | ninguno |
| `telegram.message_thread_id` | Tema del foro para la actividad (`0` o vacío = el chat principal) | ninguno |
| `date_format` | Cómo se escribe la fecha de la convocatoria, con los códigos `%` de `display_date_format`; los nombres de día y mes (`%A`, `%B`, ...) salen en inglés | `%Y-%m-%d %H:%M` |

Sin `telegram.chat_id`, la actividad va al log de PyBall. Estas
claves no tienen variables de entorno.

## Sus datos

`data/plugins/activity/last_event_id` guarda el último evento que activity publicó, desde
donde sigue tras reiniciarse.
