//! Spanish Telegram messages (HTML parse mode).

use chrono::{Datelike, NaiveDateTime};

/// A meetup as the messages show it: names, not ids.
pub struct MeetupView {
    pub date: String,
    pub location: String,
    pub players: Vec<String>,
    /// Each team's name and its players' names.
    pub teams: Option<Vec<(String, Vec<String>)>>,
}

/// One row of the siesta list as shown to the group.
pub struct SiestaRow {
    pub name: String,
    pub outs: u32,
}

pub struct DrawSummary<'a> {
    pub meetup: &'a MeetupView,
    pub signed_up: usize,
    pub left_out: Vec<String>,
    pub siesta: Vec<SiestaRow>,
}

pub fn draw_message(d: &DrawSummary) -> String {
    let mut s = header("🎲", "Sorteo", d.meetup);
    let out = d.left_out.len();
    if out == 0 {
        s += &format!("Apuntados: {} · ¡Juegan todos! 🎉\n", d.signed_up);
    } else {
        s += &format!(
            "Apuntados: {} · Juegan: {}\n",
            d.signed_up,
            d.signed_up - out
        );
    }
    if out > 0 {
        s += "\n😴 <b>Descansan esta semana</b>\n";
        s += &bullets(&d.left_out);
    }
    s += &lineup(d.meetup);
    s += &siesta_table(&d.siesta);
    s
}

pub fn not_full_message(meetup: &MeetupView, capacity: usize) -> String {
    let mut s = header("📣", "Convocatoria", meetup);
    s += &format!(
        "Apuntados: {}/{capacity}\nLa convocatoria no está llena, pasamos a buscar suplentes. 🔎\n",
        meetup.players.len()
    );
    s
}

pub fn reinstate_message(
    meetup: &MeetupView,
    player_in: &str,
    player_out: Option<&str>,
    siesta: &[SiestaRow],
) -> String {
    let mut s = header("🔄", "Cambio", meetup);
    match player_out {
        Some(out) => s += &format!("Se baja {}, entra <b>{}</b>.\n", esc(out), esc(player_in)),
        None => s += &format!("Entra <b>{}</b>.\n", esc(player_in)),
    }
    s += &format!(
        "{} recupera su descanso (no cuenta en la lista).\n",
        esc(player_in)
    );
    s += &lineup(meetup);
    s += &siesta_table(siesta);
    s
}

/// Plain-text version for the terminal (dry runs, no Telegram configured).
pub fn to_plain(html: &str) -> String {
    let mut out = String::with_capacity(html.len());
    let mut in_tag = false;
    for c in html.chars() {
        match c {
            '<' => in_tag = true,
            '>' => in_tag = false,
            _ if !in_tag => out.push(c),
            _ => {}
        }
    }
    out.replace("&lt;", "<")
        .replace("&gt;", ">")
        .replace("&amp;", "&")
}

fn header(emoji: &str, title: &str, meetup: &MeetupView) -> String {
    let mut s = format!(
        "{emoji} <b>{title} · {}</b>\n",
        esc(&spanish_date(&meetup.date))
    );
    if !meetup.location.is_empty() {
        s += &format!("📍 {}\n", esc(&meetup.location));
    }
    s
}

fn bullets(names: &[String]) -> String {
    names.iter().map(|n| format!("• {}\n", esc(n))).collect()
}

fn lineup(meetup: &MeetupView) -> String {
    match &meetup.teams {
        Some(teams) => {
            let mut s = String::from("\n⚽ <b>Equipos</b>\n");
            for (name, players) in teams {
                let names: Vec<String> = players.iter().map(|p| esc(p)).collect();
                s += &format!("👕 <b>{}</b>: {}\n", esc(name), names.join(", "));
            }
            s
        }
        None => format!("\n⚽ <b>Juegan</b>\n{}", bullets(&meetup.players)),
    }
}

fn siesta_table(rows: &[SiestaRow]) -> String {
    let mut rows: Vec<&SiestaRow> = rows.iter().filter(|r| r.outs > 0).collect();
    if rows.is_empty() {
        return String::new();
    }
    rows.sort_by(|a, b| {
        b.outs
            .cmp(&a.outs)
            .then_with(|| fold(&a.name).cmp(&fold(&b.name)))
    });
    let mut s = String::from("\n📋 <b>Lista de siesta</b> (veces que han descansado)\n");
    for r in rows {
        s += &format!("{} · {}\n", r.outs, esc(&r.name));
    }
    s
}

fn spanish_date(iso: &str) -> String {
    const DAYS: [&str; 7] = [
        "lunes",
        "martes",
        "miércoles",
        "jueves",
        "viernes",
        "sábado",
        "domingo",
    ];
    const MONTHS: [&str; 12] = [
        "enero",
        "febrero",
        "marzo",
        "abril",
        "mayo",
        "junio",
        "julio",
        "agosto",
        "septiembre",
        "octubre",
        "noviembre",
        "diciembre",
    ];
    let parsed = NaiveDateTime::parse_from_str(iso, "%Y-%m-%dT%H:%M:%S")
        .or_else(|_| NaiveDateTime::parse_from_str(iso, "%Y-%m-%dT%H:%M"));
    match parsed {
        Ok(dt) => format!(
            "{} {} de {}, {}",
            DAYS[dt.weekday().num_days_from_monday() as usize],
            dt.day(),
            MONTHS[dt.month0() as usize],
            dt.format("%H:%M")
        ),
        Err(_) => iso.to_string(),
    }
}

/// Lowercase without accents, for matching and sorting names.
pub fn fold(s: &str) -> String {
    s.trim()
        .to_lowercase()
        .chars()
        .map(|c| match c {
            'á' | 'à' | 'ä' => 'a',
            'é' | 'è' | 'ë' => 'e',
            'í' | 'ì' | 'ï' => 'i',
            'ó' | 'ò' | 'ö' => 'o',
            'ú' | 'ù' | 'ü' => 'u',
            other => other,
        })
        .collect()
}

fn esc(s: &str) -> String {
    s.replace('&', "&amp;")
        .replace('<', "&lt;")
        .replace('>', "&gt;")
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn formats_spanish_dates() {
        assert_eq!(
            spanish_date("2026-11-18T20:00:00"),
            "miércoles 18 de noviembre, 20:00"
        );
        assert_eq!(
            spanish_date("2028-02-29T21:30"),
            "martes 29 de febrero, 21:30"
        );
    }

    #[test]
    fn escapes_html_in_names() {
        assert_eq!(esc("Tom & <Jerry>"), "Tom &amp; &lt;Jerry&gt;");
        assert_eq!(to_plain("<b>A &amp; B</b>"), "A & B");
    }
}
