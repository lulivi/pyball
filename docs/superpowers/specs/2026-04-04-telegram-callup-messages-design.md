# Telegram Callup Messages Design

## Overview

Update PyBall v4 to send callup messages to two Telegram chats (regulars and substitutes), with inline buttons for players to join/leave, and edit the same message as players are added/removed or teams/results are modified.

## Section 1: Settings Updates

Add new config sections in `settings.py`:

```python
@dataclass
class TelegramChatSettings:
    chat_id: int = 0
    thread_id: str = ""  # Empty string = no thread

@dataclass 
class TelegramSettings:
    bot_token: str = ""
    admins_ids: tuple[int, ...] = ()
    regulars: TelegramChatSettings = field(default_factory=TelegramChatSettings)
    substitutes: TelegramChatSettings = field(default_factory=TelegramChatSettings)
```

Environment override pattern: `PYBALL_TELEGRAM_REGULARS_CHAT_ID`, `PYBALL_TELEGRAM_REGULARS_THREAD_ID`, `PYBALL_TELEGRAM_SUBSTITUTES_CHAT_ID`, `PYBALL_TELEGRAM_SUBSTITUTES_THREAD_ID`.

## Section 2: Architecture - DDD Approach

### Domain Layer (Pure)

`Meetup` remains unchanged - pure business entity:
- `id`, `date`, `location`, `regulars`, `substitutes`, `teams`

No Telegram knowledge whatsoever.

### Infrastructure Layer

**TelegramMessageStore** - Maps meetup date to message tracking:

```python
class TelegramMessageStore:
    """Maps meetup dates to Telegram message IDs."""
    
    def save_message(meetup_date, chat_type, chat_id, thread_id, message_id)
    def get_message(meetup_date, chat_type) -> MessageTracking | None
    def delete_message(meetup_date, chat_type)
```

Where `chat_type` is `"main"` or `"subs"`.

JSON structure in `data/bot/messages.json`:
```json
{
  "2024-01-15": {
    "main": {"chat_id": 123, "thread_id": "456", "message_id": 789},
    "subs": {"chat_id": 124, "thread_id": null, "message_id": 790}
  }
}
```

### Application Layer

Use cases remain unchanged - domain-focused.

### Bot Layer

- Formats messages for main/substitutes chats
- Uses `TelegramMessageStore` to track message IDs
- Handles callback queries
- Sends/edits messages via Telegram API

## Section 3: Message Formatting

### Main Chat Message Format

```
*Convocatoria* 01/Jan/2024 20:00
Lugar: *Park*

*Jugadores (5/10):*
1. Luis
2. Carlos
3. Juan
4. Pablo
5. Alejandro

*Equipos:*
Team A: Luis, Carlos
Team B: Juan, Pablo

*Resultado:*
Team A 3 - 2 Team B
```

Format varies based on state:
- Before teams created: Full player list (no teams section)
- After teams created: Show teams only (no player list)
- After results added: Show teams + results

### Substitutes Chat Message Format

```
*Convocatoria* 01/Jan/2024 20:00 - Suplentes

*Suplentes (2):*
1. Pedro
2. Miguel

*Plazas restantes:* 3
```

### Inline Buttons

**Main chat:**
- `callback_data: join:2026-04-03T20:00` - Join as regular
- `callback_data: leave:2026-04-03T20:00` - Leave the callup

**Substitutes chat:**
- `callback_data: join_sub:2026-04-03T20:00` - Join as substitute
- `callback_data: leave_sub:2026-04-03T20:00` - Leave the substitutes list

Button text: "✅ Unirse" / "❌ Salir"

**Date format in callback:** `YYYY-MM-DDTHH:MM` (ISO without timezone or seconds)

## Section 4: Bot Handlers

### New Commands

- `/callup <date> <time> [location]` - Create new meetup, sends message to regulars chat only
- `/search` - Send message to substitutes chat (when all regulars who can play have joined but spots still remain)
- `/join <date>` - Join as regular (alternative to button)
- `/leave <date>` - Leave the callup (alternative to button)

### Callback Query Handler

Handle button presses:
- Parse callback data: `action:join` or `action:leave`
- Extract meetup date from callback data
- Execute join/leave use case
- Edit both messages with updated content

### Send/Edit Logic

```python
def send_or_edit_message(chat_id, thread_id, message_id, text, keyboard):
    if message_id:
        # Edit existing message
        return bot.edit_message_text(...)
    else:
        # Send new message
        msg = bot.send_message(...)
        return msg.message_id
```

- If `thread_id` is empty, don't pass to API
- Always track returned `message_id` in meetup

## Section 5: Data Flow

1. Admin runs `/callup 2024-01-15 20:00 Park`
2. System creates meetup in database (domain)
3. System sends message to regulars chat → stores in `TelegramMessageStore`
4. Player clicks "Unirse" button
5. Callback handler receives action, extracts date
6. Use case adds player to meetup
7. System looks up message ID from `TelegramMessageStore`
8. System edits main message with updated player list
9. Repeat for leave, teams creation, results

**Substitutes message flow:**
1. Admin runs `/search` (when regulars full or spots remaining)
2. System sends message to substitutes chat → stores in `TelegramMessageStore`
3. Substitute clicks button (join_sub/leave_sub)
4. Callback handler updates substitutes list in meetup
5. System edits substitutes message only

## Section 6: Error Handling

- Invalid date format → Show usage instructions
- Meetup not found for date → Show error message
- Chat ID not configured → Raise config error at startup
- Message edit fails (e.g., too old) → Send new message, update ID

## Section 7: Testing Strategy

- Unit tests for message formatting (different states)
- Unit tests for callback data parsing
- Integration tests for send/edit flow (mocked Telegram API)
- Test date parsing in various formats
