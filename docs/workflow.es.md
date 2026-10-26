# Flujo de la aplicación

🇬🇧 [English](workflow.md) | 🇪🇸 Español

Este documento recorre la vida completa de un partido en PyBall: crearlo, generar
equipos, jugarlo, y cerrarlo — cubriendo los dos formatos de partido que soporta PyBall.
Todos los pasos se pueden hacer desde las páginas web `/manage` y `/match`; donde
también existe un comando de Telegram (solo si usas la topología `pyball-telegram`), se
indica junto al paso, y donde los jugadores pueden actuar por su cuenta desde `/signup`
(solo si `enable_web_signup` está activo en `config.toml`), también se indica.

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
  suplentes. Confirmar crea el partido con esa convocatoria — si hay un chat de
  Telegram de titulares configurado, el mensaje de convocatoria con botones
  "✔ Unirse" / "✖ Salir" se publica ahí automáticamente, para que los jugadores se
  apunten o se bajen ellos mismos tocando un botón. El chat de suplentes **no** se
  avisa en este momento — mira el [paso 2](#2-gestionar-la-convocatoria) para abrirlo a
  los suplentes cuando estés listo.

## 2. Gestionar la convocatoria

Antes de generar los equipos todavía puedes ajustar quién juega. En Telegram, los
titulares normalmente lo hacen ellos mismos con los botones "✔ Unirse" / "✖ Salir" del
paso 1.

- **`/manage`:** "✏️ Editar convocatoria" abre el mismo modo de edición que los equipos:
  quitar, reemplazar o buscar y añadir jugadores, y luego "💾 Guardar convocatoria".
- **Telegram:** un admin puede pulsar el botón "🔎 Buscar jugadores" del mensaje de
  convocatoria de titulares (o volver a tocarlo más tarde) para publicar un mensaje
  aparte en el chat de suplentes con sus propios botones "✔ Unirse" / "✖ Salir" — es un
  paso manual y deliberado, para que los titulares tengan prioridad unos días antes de
  buscar suplentes.

  Cada búsqueda tiene un objetivo: el siguiente escalón de **10 → 12 → 15** jugadores
  por encima de los apuntados (9 → 10, 10–11 → 12, 12–14 → 15; con 15 o más no hay
  nada que buscar). La búsqueda se cierra sola en cuanto se alcanza el objetivo —
  lo complete un titular o un suplente — y el mensaje de suplentes se edita a
  "✅ Completo" sin botones, así ningún suplente se cuela antes de que generes los
  equipos. Mientras busca, el objetivo solo baja: con 11 apuntados buscando 12, si
  alguien se desapunta se vuelve a 10 y la búsqueda queda completa. Los titulares
  pueden seguir apuntándose. ¿Hacen falta más después? Pulsa "Buscar" otra vez para
  abrir una búsqueda nueva.

## Alta por cuenta propia en `/signup`

Si `enable_web_signup` está activo en `config.toml`, los jugadores pueden apuntarse o
bajarse de un partido ellos mismos en `/signup`, sin pasar nunca por `/manage`. Cada
jugador se identifica con su propio código personal de 8 caracteres, que se muestra una
sola vez al crearlo en `/manage`, o se puede regenerar en cualquier momento con el botón
"Regenerar código" de su fila — ese mismo modal ofrece también "📤 Compartir" (donde el
navegador lo soporte) y "📋 Copiar mensaje", que juntan el código del jugador con la URL
de `/signup` (protegida por `signup_token`, ver
[Tokens de acceso](setup.es.md#6-tokens-de-acceso)) en un único mensaje listo para
enviar. La URL de `/signup` sola también se puede copiar desde "Convocatoria actual" con
"🔗 Copiar link apuntarse", visible hasta que empieza el partido — tanto mientras
todavía estás formando la convocatoria como después de generar los equipos.

- **Introducir el código:** la primera pantalla solo pide el código. Uno correcto
  saluda al jugador por su nombre y muestra el partido activo, si lo hay.
- **Apuntarse o bajarse:** mientras el alta sigue abierta (antes de generar los
  equipos — ver [paso 3](#3-generar-equipos)), un botón "Apuntarme" / "Salir" añade o
  quita al jugador de la convocatoria, igual que si lo hiciera un admin desde `/manage`.
- **Una vez hay equipos:** el botón de apuntarse/bajarse desaparece; el jugador ve todos
  los equipos, en modo solo lectura, la misma vista que ven todos desde `/manage` o
  `/match` — con su propio nombre resaltado para encontrarse de un vistazo.
- **Dispositivos compartidos:** "No soy yo" cierra la sesión del jugador actual (borra
  su cookie de identidad) sin tocar la cookie del `signup_token`, para que la siguiente
  persona pueda introducir su propio código en el mismo móvil o tablet.

`/signup` es pura conveniencia — un admin siempre puede añadir, quitar o reasignar a un
jugador desde `/manage` sin que nadie tenga que visitar `/signup`.

## 3. Generar equipos

Aquí es donde eliges el formato del partido:

- **`/manage`:** pulsa "⚽ Generar 2 equipos" para un partido clásico, o "⚽ Generar 3
  equipos" para un triangular. Los equipos se generan con un algoritmo equilibrado
  (ponderado por resultados recientes y estadísticas heredadas, si están configuradas) o
  de forma aleatoria. También puedes abrir "✏️ Editar convocatoria" después para mover,
  reemplazar, añadir o quitar jugadores de cualquier equipo manualmente (el mismo panel
  funciona con 2 o 3 equipos), intercambiar las plantillas de dos equipos con los botones
  "🔄", o cambiar la fecha y la ubicación del partido.

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
"✏️ Editar convocatoria".

Nada más existir los equipos, la convocatoria se cierra automáticamente: los
botones "✔ Unirse" / "✖ Salir" de Telegram desaparecen de los mensajes de titulares y
suplentes, y pulsar "🔎 Buscar jugadores" (o el comando `/meetup_search`) se rechaza —
ya nadie puede apuntarse ni bajarse una vez que hay equipos.

En cuanto hay equipos, "🔗 Copiar link partido" (copia de un toque la URL de `/match`,
con `match_token` incluido si está configurado) y, en un triangular, "🏁 Cerrar
triangular" están siempre disponibles. Regenerar equipos pide confirmación, igual que
"🗑 Cancelar partido" y "🗑️ Destruir equipos". En cuanto se registra el primer
resultado, regenerar, cancelar y destruir desaparecen del todo. "✏️ Editar convocatoria"
(reasignar jugadores entre los equipos ya generados, o cambiar la fecha y la ubicación)
sigue funcionando en todo momento.

¿Te lo has pensado mejor? "🗑️ Destruir equipos" descarta los equipos actuales
y vuelve a la vista de convocatoria, para que puedas
editarla y, en Telegram, volver a buscar suplentes. Está disponible hasta que se
registre el primer resultado — a partir de ahí, la única forma de deshacer la sesión
es corregir el resultado después (ver [paso 6](#6-ver-estadísticas)).

## 4. Seguir el partido

Abre `/match` en el dispositivo que vaya a llevar el marcador (móvil, tablet). Muestra
automáticamente el partido pendiente actual — sin configuración manual, sin código QR
que escanear.

- Toca a un jugador para registrar un gol, opcionalmente eligiendo una asistencia.
- Toca "Finalizar partido" cuando termine y escribe el marcador final.
- Si rotáis porteros por tiempo, la pestaña **Tiempo** lleva una cuenta atrás que se
  repite (6 minutos por defecto) y en cada intervalo suena un pitido largo y plano y
  parpadea — ponla en marcha al empezar el partido y cambia de portero en la siguiente
  parada cuando la oigas.
- Para que te avise antes de que se acabe la hora de pista reservada, activa el aviso
  en la misma pestaña **Tiempo** — suena N minutos antes de cada hora en punto (5 por
  defecto, ajustable entre 1 y 15) con un silbato de árbitro ("pi · pi · piiiii"), bien
  distinto del pitido de rotación; los dos pueden estar activos a la vez.

**En un partido clásico**, finalizar el único partido cierra el meetup
automáticamente — se publica un resumen (en Telegram, si está configurado) y el partido
pasa a la pestaña "Convocatorias" de `/manage`.

**En un triangular**, finalizar un partido no cierra el meetup — PyBall calcula el
siguiente emparejamiento según [las reglas](#las-reglas-del-triangular) y `/match`
muestra inmediatamente la siguiente ronda, lista para seguir marcando. Repite el paso 4
tantas rondas como dure la sesión.

## 5. Cerrar una sesión triangular

Como un triangular no tiene un número fijo de rondas, un admin lo cierra explícitamente
cuando se acaba el tiempo de la sesión:

- **`/manage`:** el botón "🏁 Cerrar triangular" aparece en la pestaña Convocatoria
  actual siempre que el partido activo sea un triangular (está oculto en los partidos
  clásicos, que no lo necesitan).

Cerrar publica un resumen que cubre todas las rondas jugadas en la sesión. Un partido
clásico nunca necesita esto — se cierra solo en cuanto termina su único partido.

## 6. Ver estadísticas

- **`/manage` → pestaña "Convocatorias":** una lista de todos los partidos cerrados, del
  más reciente al más antiguo. Toca uno para desplegar su resumen, listo para copiar o
  compartir como imagen, más un enlace para corregir un resultado si se introdujo mal.
  En un partido clásico, la convocatoria de cada equipo muestra los
  goles/asistencias/goles en propia de cada jugador, seguida de una lista cronológica
  de eventos bajo `*GOLES:*`. En un triangular, el resumen empieza con la convocatoria
  de cada equipo (con estadísticas de cada jugador en toda la sesión) y su récord de
  victorias/empates/derrotas (ej. `⚪ Blanco (1V 1E 0D)`), y luego cada ronda muestra
  solo su marcador y su propia lista de eventos. El mensaje de Telegram al terminar un
  partido usa este mismo formato.
- **Telegram:** `/meetup_stats [temporada|historico]` publica las estadísticas de
  temporada o históricas como imagen. La clasificación ordena por puntos; a igualdad de
  puntos, va primero quien haya jugado menos partidos.

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

- [docs/pages.es.md](pages.es.md) — un recorrido estructural por las pestañas y
  pantallas de cada página.
- [docs/setup.es.md](setup.es.md) — instalar, configurar y ejecutar PyBall.
- [docs/data-directory.es.md](data-directory.es.md) — dónde se guardan los partidos,
  jugadores y resultados en disco.
