# Telegram Message Formatting Design

**Goal:** Improve the messages sent to regulars and substitutes Telegram chats with better formatting, emojis, and additional information.

---

## 1. format_main_message (chat regulars)

### 1.1 Header emoji

- **Sin resultado (antes de equipos y con equipos):** 📅 antes de "Convocatoria"
- **Con resultado (partido terminado):** 🎉 antes de "Convocatoria"

```
📅 *Convocatoria:* `2026/04/21 20:00`
```

```
🎉 *Convocatoria:* `2026/04/21 20:00`
```

### 1.2 Ubicación

- 📍 antes de la ubicación

```
📍 *Lugar:* Campo de fútbol
```

### 1.3 Equipos

- ⚪ y ⚫ delante del nombre del equipo

```
⚪ *Claro (2-1):*
- Juan
- Pedro

⚫ *Oscuro (1-2):*
- Carlos
```

### 1.4 Eventos con resultado

- Cuando hay resultado: añadir sección de eventos debajo de equipos
- Formato: `⚽ 10' Mateo (Juan)` donde 10' es el minuto, Mateo es el goleador y (Juan) es el asistente (solo si existe)
- Los eventos se muestran en orden cronológico (sin ordenar por equipo)

```
⚽ *Goles:*
- ⚽ 10' Mateo (Juan)
- ⚽ 25' Carlos
- ⚽ 30' Pedro (Luis)
```

---

## 2. format_subs_message (chat substitutes)

### 2.1 Con equipos

- Mostrar cada suplente con su equipo

```
⚪ Equipo Claro: Juan, Pedro
⚫ Equipo Oscuro: Carlos, Luis
```

### 2.2 Con resultado

- Simple: "Partido terminado" (sin más información)

```
*Partido terminado*
```

---

## 3. Archivos a modificar

- `pyball/bot/formatters.py`: `format_main_message` y `format_subs_message`