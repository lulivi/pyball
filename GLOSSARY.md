# Glossary

**Club** (_peña_): one football group with its own PyBall deployment, players and rules.

**Meetup** (_convocatoria_): one football session on a date and at a location, with the
players signed up for it and, once made, its teams.

**Capacity**: how many players a meetup plays with. A new meetup starts at the club's
default capacity and changes by hand, except that a substitute search falling back to the
default capacity returns to it.

**Substitute search**: the state of a meetup that is looking for players outside the
regulars until its roster reaches its capacity.

**Plugin**: an optional integration, in any language, that the core starts and supervises
and that works only through the plugin API and the event stream.

**Bundled plugin**: a plugin that lives in `plugins/` in this repository and ships inside
the PyBall images; it runs only once `config.toml` declares it.

**Siesta** (_siesta_): the fair way to decide who sits out when more players sign up
than a meetup can take: those who sat out the fewest times are left out first, ties are
drawn at random, and each player left out gets +1 on the siesta list.

**Event**: a record that something happened to a meetup, kept in order so a plugin can
resume from the last one it saw.

**Alert**: a warning or error about the PyBall deployment itself, including a plugin that
crashes, sent to the club's alert channel whether or not any plugin is running.
