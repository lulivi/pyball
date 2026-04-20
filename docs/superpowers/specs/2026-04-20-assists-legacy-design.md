# Diseño: Asistencias Legacy

## Problema

El script de migración `scripts/migrate_legacy_sqlite_to_json.py` migra datos históricos de SQLite a JSON, pero las asistencias se migran como `assistant_id: None` porque el schema legacy solo almacena counts agregados por jugador, no la asistencia específica para cada gol.

Esto afecta:
1. **Balanceo de equipos**: Los jugadores con muchas asistencias históricas no se benefician al crear equipos equilibrados.
2. **Estadísticas**: Las estadísticas históricas muestran 0 asistencias para jugadores que tuvieron muchas en la era legacy.

## Solución

Separar los datos agregados legacy del modelo DDD, manteniéndolos como referencia externa.

### 1. Archivo de estadísticas legacy

**Ubicación**: `data/legacy_stats.json`

**Estructura**:
```json
{
  "players": {
    "<player_uuid>": {
      "goals": 25,
      "assists": 12,
      "matches": 30
    }
  }
}
```

**Generación**: El script de migración ya lee `goals` y `assists` de `match_statistic`. Solo hay que escribir este archivo adicional.

### 2. Carga de estadísticas legacy

**Nueva clase**: `pyball.infrastructure.persistence.legacy_stats.LegacyStats`

```python
class LegacyStats:
    def __init__(self, data: dict[str, dict[str, int]]): ...
    def get(self, player_id: str) -> dict[str, int]: ...  # {goals, assists, matches}
    def get_assists(self, player_id: str) -> int: ...
    def get_goals(self, player_id: str) -> int: ...
    def get_matches(self, player_id: str) -> int: ...
    def all_players(self) -> list[str]: ...
```

**Carga**: Se carga una vez al iniciar la aplicación via `Container`.

### 3. Integración en balance.py

En `_player_stats()`:

```python
def _player_stats(
    player_id: PlayerId,
    meetups: list[Meetup],
    legacy_stats: LegacyStats | None = None,  # nuevo parámetro
) -> tuple[int, float, float, float]:
    # ... lógica existente ...
    for event in meetup.result.events:
        if event.scorer_id == player_id:
            goals += 1
        if event.assistant_id == player_id:
            assists += 1

    # Añadir assists legacy
    if legacy_stats and mp > 0:
        legacy = legacy_stats.get(player_id)
        assists += legacy["assists"]
```

Actualizar `_player_role()` igual.

### 4. Integración en compute_stats.py

En `_compute_player_stats()` (línea ~150), añadir parámetro `legacy_stats: LegacyStats | None` y сумar assists legacy.

### 5. Actualización del Container

En `pyball/application/container.py`:

1. Añadir `legacy_stats: LegacyStats` como dependencia.
2. Cargar desde `data/legacy_stats.json` si existe (si no existe, `LegacyStats({})`).

### 6. Script de migración

Modificar `scripts/migrate_legacy_sqlite_to_json.py`:

- Ya lee `goals` y `assists` de `match_statistic` (línea 88).
- Añadir función que aggregate por jugador y escriba `legacy_stats.json` en `data/`.

## Datos de prueba

El test existente `tests/unit/application/test_balance.py` usa `GoalEvent` sin `assistant_id`. Los tests deben seguir pasando — la lógica solo añade assists cuando `legacy_stats` tiene datos.

## Notas

- Los datos legacy son **solo lectura** — no se modifican nunca.
- Si un jugador tiene stats tanto en meetups como en legacy, se сумan.
- Si no existe `legacy_stats.json`, el sistema funciona igual (compatibilidad hacia atrás).
