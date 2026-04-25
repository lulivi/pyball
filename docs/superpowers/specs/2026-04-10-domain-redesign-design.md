# Domain & Bot Redesign Specification

## Overview

Redesign Player and Meetup domain models, application layer, and Telegram bot to:
- Add group (regular/substitute) to Player domain
- Simplify Meetup to single player list
- Identify by date and fuzzy name instead of internal UUIDs

## 1. Player Domain

### Attributes

| Field | Type | Description |
|-------|-----|-------------|
| id | PlayerId | UUID (existing) |
| name | str | Unique player name (existing) |
| group | str | `regular` or `substitute`, assigned at creation, can change over time |

### Validation

- `name`: must be unique, non-empty, stripped
- `group`: must be `regular` or `substitute`

### Methods

- `Player.create(name: str, group: str)` - create with group
- `Player.set_group(new_group: str)` - internal method for use case to call

### Use Cases

- `ChangePlayerGroup` - admin use case, calls `player.set_group()`

### Storage

No changes to repository interface.

## 2. Meetup Domain

### Attributes

| Field | Type | Description |
|-------|-----|-------------|
| id | MeetupId | UUID (existing) |
| date | datetime | Must be unique |
| location | str | Required, default from settings |
| players | list[PlayerId] | Single list of players |
| teams | list[Team] \| None | Teams (existing) |

### Validation

- `date`: must be unique across all meetups
- `location`: required, defaults from settings.pyball.location

### Methods

- `Meetup.create(date: datetime)` - create with date
- `Meetup.add_player(player_id: PlayerId)` - add to single list
- `Meetup.remove_player(player_id: PlayerId)` - remove from single list
- Remove `add_regular()`, `add_substitute()`

### Storage

No changes to repository interface.

## 3. Application Layer

### Use Cases

| Use Case | Description |
|---------|-------------|
| CreatePlayer | name + group, group required |
| ChangePlayerGroup | admin only, change player's group |
| RenamePlayer | existing |
| DeletePlayer | existing |
| CreateMeetup | date + location (defaults from settings), enforces uniqueness |
| AddPlayerToMeetup | add by player name (fuzzy) |
| RemovePlayerFromMeetup | remove by player name (fuzzy) |
| CreateTeams | existing |

### Fuzzy Name Matching

- Use `difflib.get_close_matches()` from standard library
- Match against all player names in repository
- Return match if similarity ratio >= 0.6
- Error if no match or multiple ambiguous matches

## 4. Bot Commands

### Identification

| Entity | Format | Example |
|--------|--------|---------|
| Meetup | `YYYY-MM-DD HH:MM` | `2024-03-20 20:00` |
| Player | Fuzzy name | `mar` matches "Mario" |

### Command Changes

| Command | Changes |
|---------|---------|
| /new_meetup | Use unique date |
| /add_player | Use fuzzy name + date |
| /remove_player | Use fuzzy name + date |
| /create_teams | Use date |
| /list_meetups | Show dates, no IDs |
| /show_meetup | Use date |
| /callup | Using settings defaults |
| /search | Use date |

### Admin Commands

| Command | Description |
|---------|-------------|
| /change_group | Change player group (admin only) |

Format: `/change_group <player_name> <regular|substitute>`

## 5. Telegram UI

### Regulars Chat Message

- Show all player names in meetup (unmasked)
- Join/leave buttons for each player (based on Telegram user)

### Substitutes Chat Message

- Show substitutes with names
- Show regulars as masked: `---------`
- Same button handler - adds/removes clicking user from meetup

### Button Handler

Single handler:
1. Get Telegram user ID from callback
2. Look up player via telegram_user → player mapping
3. Add/remove player from meetup's single player list
4. Refresh both messages with appropriate masking

## 6. Error Handling

| Error | Message |
|-------|---------|
| Duplicate meetup date | "Meetup already exists at this time" |
| No player match | "Player not found" |
| Multiple matches | "Multiple players match: ..." |

## 7. Testing

- Unit tests for domain models
- Unit tests for fuzzy matching
- Integration tests for bot commands

## 8. Migration

- Delete existing data (development only, no migration needed)