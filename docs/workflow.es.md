# Flujo de la aplicación

🇬🇧 [English](workflow.md) | 🇪🇸 Español

Este documento recorre la vida completa de un partido en PyBall: crearlo, generar
equipos, jugarlo, y cerrarlo — cubriendo los dos formatos de partido que soporta PyBall.
Todos los pasos se pueden hacer desde las páginas web `/manage` y `/match`; donde
también existe un comando de Telegram (solo si usas la topología `pyball-telegram`), se
indica junto al paso.

## Los dos formatos de partido

Cada partido usa uno de dos formatos, decidido al generar los equipos:

- **Clásico (2 equipos):** un equipo juega contra otro en un único partido de ~1 hora.
  Es el formato tradicional — equipo A contra equipo B, un marcador final.
- **Triangular (3 equipos):** tres equipos comparten una sesión de partidos cortos
  repetidos con una regla automática de "el ganador se queda" (detalles en
  [Las reglas del triangular](#las-reglas-del-triangular) más abajo). PyBall calcula
  quién juega a continuación después de cada resultado — nadie tiene que aplicar las
  reglas a mano.

Nada más del flujo cambia según el formato — crear el partido, gestionar la
convocatoria, y ver estadísticas funciona igual en ambos casos.

## 1. Crear un partido

Un partido (meetup) es una sesión programada: una fecha, una hora, una ubicación, y una
convocatoria de jugadores.

- **`/manage`:** pega el texto de la convocatoria (una lista de titulares y suplentes,
  uno por línea) en la primera caja y pulsa "🔍 Reconocer jugadores". PyBall empareja
  cada nombre con tu base de datos de jugadores mediante coincidencia difusa, marca
  cualquier cosa ambigua o no reconocida para que la resuelvas, y te deja excluir
  suplentes. Confirmar crea el partido con esa convocatoria.
- **Telegram:** `/meetup_new <fecha> <hora>` crea un partido vacío para esa fecha;
  `/meetup_next` crea uno para la siguiente ocurrencia del día de la semana y hora por
  defecto configurados. Cualquiera de los dos comandos publica un mensaje de
  convocatoria en el chat de titulares (y otro aparte en el de suplentes) con botones
  "✔ Unirse" / "✖ Salir", para que los jugadores se apunten o se bajen ellos mismos
  tocando un botón — sin necesidad de añadirlos a mano. El mensaje de titulares también
  tiene botones "🔀 Crear 2 equipos" / "🔀 Crear 3 equipos" que van directo al
  [paso 3](#3-generar-equipos).

## 2. Gestionar la convocatoria

Antes de generar los equipos todavía puedes ajustar quién juega. En Telegram, los
jugadores normalmente lo hacen ellos mismos con los botones "✔ Unirse" / "✖ Salir" del
paso 1 — estos comandos son para que un admin ajuste la convocatoria directamente:

- **`/manage`:** la lista de convocados permite quitar un jugador o buscar y añadir otro.
- **Telegram:** `/meetup_add_player <fecha> <hora> <nombre>` y
  `/meetup_remove_player <fecha> <hora> <nombre>`.

## 3. Generar equipos

Aquí es donde eliges el formato del partido:

- **`/manage`:** pulsa "⚽ Generar 2 equipos" para un partido clásico, o "⚽ Generar 3
  equipos" para un triangular. Los equipos se generan con un algoritmo equilibrado
  (ponderado por resultados recientes y estadísticas heredadas, si están configuradas) o
  de forma aleatoria. También puedes abrir "✏️ Editar equipos" después para mover,
  reemplazar, añadir o quitar jugadores de cualquier equipo manualmente — el mismo panel
  funciona con 2 o 3 equipos.
- **Telegram:** `/meetup_create_teams <fecha> <hora> [algoritmo] [n_equipos]` — omite
  `n_equipos` para un partido clásico de 2 equipos, o pasa `3` para un triangular.
  `algoritmo` puede ser `balanceado` (por defecto), o
  `manual Nombre1,Nombre2;Nombre3,Nombre4` para asignar los equipos a mano desde
  Telegram.

En cuanto se asignan los equipos, el primer partido ya está listo para seguir — no hace
falta ningún paso extra de "arrancar".

Los porteros y las posiciones de campo (ver
[docs/data-directory.es.md](data-directory.es.md#dataplayersjson)) se gestionan
automáticamente en el algoritmo equilibrado: un jugador marcado como `portero` es
candidato a convertirse en el portero designado de su equipo para la sesión —
ponderado por un dato histórico de goles encajados, así que ningún equipo tiene uno
garantizado, pero los mejores porteros disponibles tienden a acabar en equipos
distintos. El resto de posiciones (`defensa`/`centrocampista`/`delantero`) se usan como
una señal más suave para evitar amontonar en un mismo equipo a todos los jugadores de
una misma posición. Siempre puedes ver o cambiar quién es el portero de un equipo desde
"✏️ Editar equipos".

## 4. Seguir el partido

Abre `/match` en el dispositivo que vaya a llevar el marcador (móvil, tablet). Muestra
automáticamente el partido pendiente actual — sin configuración manual, sin código QR
que escanear.

- Toca a un jugador para registrar un gol, opcionalmente eligiendo una asistencia.
- Toca "Finalizar partido" cuando termine y escribe el marcador final.

**En un partido clásico**, finalizar el único partido cierra el meetup
automáticamente — se publica un resumen (en Telegram, si está configurado) y el partido
pasa a la pestaña "Resumen" de `/manage`.

**En un triangular**, finalizar un partido no cierra el meetup — PyBall calcula el
siguiente emparejamiento según [las reglas](#las-reglas-del-triangular) y `/match`
muestra inmediatamente la siguiente ronda, lista para seguir marcando. Repite el paso 4
tantas rondas como dure la sesión.

## 5. Cerrar una sesión triangular

Como un triangular no tiene un número fijo de rondas, un admin lo cierra explícitamente
cuando se acaba el tiempo de la sesión:

- **`/manage`:** el botón "🏁 Cerrar triangular" aparece en la pestaña Equipos siempre
  que el partido activo sea un triangular (está oculto en los partidos clásicos, que no
  lo necesitan).
- **Telegram:** `/meetup_close_triangular <fecha> <hora>`.

Cerrar publica un resumen que cubre todas las rondas jugadas en la sesión. Un partido
clásico nunca necesita esto — se cierra solo en cuanto termina su único partido.

## 6. Ver estadísticas

- **`/manage` → pestaña "Resumen":** el resumen del último partido terminado, listo
  para copiar o compartir como imagen, más un enlace para corregir un resultado si se
  introdujo mal. En un partido clásico, la convocatoria de cada equipo muestra los
  goles/asistencias/goles en propia de cada jugador, seguida de una lista cronológica
  de eventos bajo `*GOLES:*`. En un triangular, el resumen empieza con la convocatoria
  de cada equipo (con estadísticas de cada jugador en toda la sesión) y su récord de
  victorias/empates/derrotas (ej. `⚪ Blanco (1V 1E 0D)`), y luego cada ronda muestra
  solo su marcador y su propia lista de eventos. El mensaje de Telegram al terminar un
  partido usa este mismo formato.
- **Telegram:** `/meetup_stats [temporada|historico]` publica las estadísticas de
  temporada o históricas como imagen.

## Las reglas del triangular

PyBall aplica estas reglas automáticamente después de cada resultado registrado — nunca
necesitas calcular a mano quién juega a continuación:

- Cada partido se cronometra y arbitra fuera de la app (normalmente 7 minutos) — PyBall
  solo registra un marcador final, no lleva una cuenta atrás en directo.
- El equipo que llegue primero a 2 goles gana inmediatamente, sea cual sea el marcador
  del rival (2 a 0 y 2 a 1 son ambos victorias inmediatas para el equipo que llegó
  primero a 2). Si no, gana quien vaya por delante cuando se pite el final.
- Un equipo puede jugar como máximo 3 partidos consecutivos antes de tener que
  descansar, incluso si acaba de ganar.
- **En una victoria:** el ganador se queda a jugar contra el equipo que esperaba — salvo
  que el ganador ya lleve 3 victorias seguidas, en cuyo caso el ganador descansa y el
  equipo que acaba de perder se queda a jugar contra el que esperaba.
- **En un empate:** descansa el equipo con más partidos consecutivos jugados; el otro se
  queda. Un empate en el primerísimo partido de la sesión (ambos equipos empatados) se
  decide con una elección aleatoria en su lugar.
- Quién descansa en el primerísimo partido de la sesión también se elige al azar.
- La sesión no tiene duración ni número de partidos fijo — dura hasta que un admin la
  cierra (ver [paso 5](#5-cerrar-una-sesión-triangular)).

## Documentación relacionada

- [docs/setup.es.md](setup.es.md) — instalar, configurar y ejecutar PyBall.
- [docs/data-directory.es.md](data-directory.es.md) — dónde se guardan los partidos,
  jugadores y resultados en disco.
