# Referencia de páginas

🇬🇧 [English](pages.md) | 🇪🇸 Español

Este documento es un recorrido estructural por las dos páginas web de PyBall — qué
pestañas o pantallas tiene cada una y qué muestra cada una. No repite el comportamiento
paso a paso, ya cubierto en [docs/workflow.es.md](workflow.es.md), ni cómo se protege
cada página, cubierto en
[la sección de tokens de acceso de docs/setup.es.md](setup.es.md#6-tokens-de-acceso) —
enlaza a ambos en su lugar.

## `/manage`

La página de administración. Tres pestañas:

### Jugadores

La base de datos de jugadores: buscar, añadir, editar o quitar un jugador.

### Convocatoria actual

El partido activo, si existe: pegar y reconocer una convocatoria
([paso 1](workflow.es.md#1-crear-un-partido)), gestionar la convocatoria
([paso 2](workflow.es.md#2-gestionar-la-convocatoria)), incluidas su capacidad y la
búsqueda de suplentes, generar o editar equipos
([paso 3](workflow.es.md#3-generar-equipos)), destruir equipos,
cancelar el partido, copiar el enlace del partido y — en un triangular —
cerrar la sesión ([paso 5](workflow.es.md#5-cerrar-una-sesión-triangular)). Vacía si no
hay ningún partido activo.

### Convocatorias

Historial de todos los partidos cerrados, del más reciente al más antiguo, cada uno
desplegable en su resumen — ver [paso 6](workflow.es.md#6-ver-estadísticas).

## `/match`

La página de marcador, abierta en el dispositivo que lleva el partido en directo.

Tras 20 segundos sin tocarla, la página pasa a una pantalla de reposo: el minuto actual
de la hora en grande (p. ej. `47'`), la cuenta atrás hasta el siguiente cambio de
portero si el cronómetro está en marcha, y el marcador con el color de cada equipo.
Toca en cualquier sitio para volver. Nunca aparece al corregir un resultado pasado.

Bajo la fecha del partido, tres pestañas:

### Tiempo

Una cuenta atrás para las peñas que rotan porteros por tiempo. Elige la duración del
turno (1–15 minutos, 6 por defecto) y toca "Iniciar cronómetro": cuenta atrás, suena y
la pantalla parpadea al llegar a cero, y vuelve a empezar sola para el siguiente turno —
sin tener que tocar nada entre rotaciones. Un pequeño botón 🔊 junto a
"Iniciar cronómetro" y "Activar aviso" reproduce el sonido de cada aviso para
comprobar el volumen antes de empezar; desaparece una vez activados. El primer toque es
además lo que habilita el sonido en el móvil, y el cronómetro mantiene la pantalla
encendida mientras corre. Es local del dispositivo (no se comparte con otros `/match`)
y sobrevive a recargar la página. Se oculta al corregir un resultado pasado. Mientras
corre, una pequeña pastilla con la cuenta atrás aparece junto a la fecha del partido en
las otras pestañas — tócala para volver aquí. Al recargar la página el navegador
vuelve a bloquear el sonido; la pastilla muestra entonces 🔇 hasta que cualquier toque
lo reactiva.

### Jugadores

El marcador y la cuadrícula para marcar: toca a un jugador para registrar un gol,
opcionalmente eligiendo una asistencia — ver [paso 4](workflow.es.md#4-seguir-el-partido).

### Resultados

El registro cronológico de eventos del partido actual (edita o borra aquí un gol ya
registrado), y la acción "Finalizar partido" para cerrar el partido con un marcador
final.

## Documentación relacionada

- [docs/workflow.es.md](workflow.es.md) — el comportamiento paso a paso detrás de estas
  páginas.
- [docs/setup.es.md](setup.es.md) — tokens de acceso y cómo se protege cada página.
