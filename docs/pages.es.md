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
([paso 3](workflow.es.md#3-generar-equipos)), empezar el partido o destruir equipos,
cancelar el partido, copiar los enlaces de alta y de partido y — en un triangular —
cerrar la sesión ([paso 5](workflow.es.md#5-cerrar-una-sesión-triangular)). Vacía si no
hay ningún partido activo.

### Convocatorias

Historial de todos los partidos cerrados, del más reciente al más antiguo, cada uno
desplegable en su resumen — ver [paso 6](workflow.es.md#6-ver-estadísticas).

## `/match`

La página de marcador, abierta en el dispositivo que lleva el partido en directo. Bajo
la fecha del partido, tres pestañas:

### Tiempo

Una cuenta atrás para las peñas que rotan porteros por tiempo. Elige la duración del
turno (1–15 minutos, 6 por defecto) y toca "Iniciar cronómetro": cuenta atrás, suena y
la pantalla parpadea al llegar a cero, y vuelve a empezar sola para el siguiente turno —
sin tener que tocar nada entre rotaciones. El primer toque es además lo que habilita el
sonido en el móvil, y el cronómetro mantiene la pantalla encendida mientras corre. Es
local del dispositivo (no se comparte con otros `/match`) y sobrevive a recargar la
página. Se oculta al corregir un resultado pasado.
Mientras corre, una pequeña pastilla con la cuenta atrás aparece junto a la fecha del
partido en las otras pestañas — tócala para volver aquí. Al recargar la página el
navegador vuelve a bloquear el sonido; la pastilla muestra entonces 🔇 hasta que
cualquier toque lo reactiva.

### Jugadores

El marcador y la cuadrícula para marcar: toca a un jugador para registrar un gol,
opcionalmente eligiendo una asistencia — ver [paso 4](workflow.es.md#4-seguir-el-partido).

### Resultados

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
