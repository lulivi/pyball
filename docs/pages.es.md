# Referencia de páginas

🇬🇧 [English](pages.md) | 🇪🇸 Español

Este documento es un recorrido estructural por las tres páginas web de PyBall — qué
pestañas o pantallas tiene cada una y qué muestra cada una. No repite el comportamiento
paso a paso, ya cubierto en [docs/workflow.es.md](workflow.es.md), ni cómo se protege
cada página, cubierto en
[la sección de tokens de acceso de docs/setup.es.md](setup.es.md#6-tokens-de-acceso) —
enlaza a ambos en su lugar.

## `/manage`

La página de administración. Tres pestañas:

### Jugadores

La base de datos de jugadores: buscar, añadir, editar o quitar un jugador, y — si
`enable_web_signup` está activo en `config.toml` — generar o regenerar el código
personal de alta de un jugador (ver
[Alta por cuenta propia en `/signup`](workflow.es.md#alta-por-cuenta-propia-en-signup)).

### Convocatoria actual

El partido activo, si existe: pegar y reconocer una convocatoria
([paso 1](workflow.es.md#1-crear-un-partido)), gestionar la convocatoria
([paso 2](workflow.es.md#2-gestionar-la-convocatoria)), generar o editar equipos
([paso 3](workflow.es.md#3-generar-equipos)), bloquear/destruir equipos, cancelar el
partido y — en un triangular — cerrar la sesión
([paso 5](workflow.es.md#5-cerrar-una-sesion-triangular)). Vacía si no hay ningún
partido activo.

### Convocatorias

Historial de todos los partidos cerrados, del más reciente al más antiguo, cada uno
desplegable en su resumen — ver [paso 6](workflow.es.md#6-ver-estadisticas).

## `/match`

La página de marcador, abierta en el dispositivo que lleva el partido en directo. El
marcador y la cuadrícula para marcar goles están siempre visibles arriba; debajo, dos
pestañas:

### Jugadores

La cuadrícula para marcar: toca a un jugador para registrar un gol, opcionalmente
eligiendo una asistencia — ver [paso 4](workflow.es.md#4-seguir-el-partido).

### Eventos y Resultados

El registro cronológico de eventos del partido actual (edita o borra aquí un gol ya
registrado), y la acción "Finalizar partido" para cerrar el partido con un marcador
final.

## `/signup`

La página de autoservicio para jugadores, accesible solo cuando `enable_web_signup`
está activo en `config.toml` — ver
[Alta por cuenta propia en `/signup`](workflow.es.md#alta-por-cuenta-propia-en-signup)
para el comportamiento completo. Dos estados en vez de pestañas:

### Introducir el código

La pantalla inicial: solo un campo para el código personal del jugador.

### Sesión iniciada

Una vez se introduce un código válido:
- la vista de convocatoria abierta, con un botón "Apuntarme" / "Salir", mientras el alta
  sigue abierta; o
- la vista de equipos en modo solo lectura, con el nombre propio del jugador resaltado,
  una vez existen los equipos.

"No soy yo" está siempre disponible para liberar el dispositivo para el siguiente
jugador, sin perder el token de acceso de la página.

## Documentación relacionada

- [docs/workflow.es.md](workflow.es.md) — el comportamiento paso a paso detrás de estas
  páginas.
- [docs/setup.es.md](setup.es.md) — tokens de acceso y cómo se protege cada página.
