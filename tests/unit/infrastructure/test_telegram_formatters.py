from datetime import datetime, time

import pytest

from pyball.domain.meetup.models import GoalEvent, Match, MatchResult, Meetup, Team
from pyball.domain.player.models import PlayerId
from pyball.infrastructure.telegram.formatters import (
    _escape_mdv2,
    escape_summary_for_telegram,
    format_display,
    format_main_message,
    format_subs_message,
    parse_display,
)


def test_format_main_message_header_emoji_no_result():
    """When there's no result, header should show 📅 Convocatoria."""
    meetup = Meetup.create(datetime(2024, 1, 15, 20, 0), "Parque Central")
    p1 = PlayerId.generate()
    meetup.add_player(p1)

    player_names = {str(p1.value): "Luis"}
    text = format_main_message(meetup, player_names)

    assert "📅 *Convocatoria:*" in text


def test_format_main_message_header_emoji_with_result():
    """When there's a result, the closed message delegates to the unified summary."""
    meetup = Meetup.create(datetime(2024, 1, 15, 20, 0), "Parque Central")
    p1 = PlayerId.generate()
    p2 = PlayerId.generate()
    meetup.add_player(p1)
    meetup.add_player(p2)
    team_a, team_b = Team.create("A", [p1]), Team.create("B", [p2])
    meetup.set_teams([team_a, team_b])
    meetup.add_match(
        Match(teams_playing=(team_a, team_b), result=MatchResult(score_a=1, score_b=0, events=()))
    )
    meetup.close()
    player_names = {str(p1.value): "Luis", str(p2.value): "Carlos"}
    text = format_main_message(meetup, player_names)

    assert "🎉 *Partido terminado:*" in text
    assert r"⚪ *Blanco \- 1*" in text
    assert r"⚫ *Negro \- 0*" in text


def test_format_main_message_location_emoji():
    """Location should have 📍 prefix."""
    meetup = Meetup.create(datetime(2024, 1, 15, 20, 0), "Parque Central")
    p1 = PlayerId.generate()
    meetup.add_player(p1)
    player_names = {str(p1.value): "Luis"}
    text = format_main_message(meetup, player_names)

    assert "📍 *Lugar:* Parque Central" in text


def test_format_main_message_before_teams():
    meetup = Meetup.create(datetime(2024, 1, 15, 20, 0), "Parque Central")
    p1 = PlayerId.generate()
    p2 = PlayerId.generate()
    meetup.add_player(p1)
    meetup.add_player(p2)

    player_names = {str(p1.value): "Luis", str(p2.value): "Carlos"}
    text = format_main_message(meetup, player_names)

    assert "📅 *Convocatoria:*" in text
    assert "2024-01-15 20:00" in text
    assert r"\- `Carlos`" in text
    assert r"\- `Luis`" in text


def test_format_subs_message_with_teams_shows_team_assignment():
    """When there's teams, show substitutes with their team color."""
    meetup = Meetup.create(datetime(2024, 1, 15, 20, 0), "Parque Central")
    p1 = PlayerId.generate()
    p2 = PlayerId.generate()
    p3 = PlayerId.generate()
    p4 = PlayerId.generate()
    meetup.add_player(p1)
    meetup.add_player(p2)
    meetup.add_player(p3)
    meetup.add_player(p4)
    meetup.set_teams([Team.create("A", [p1, p3]), Team.create("B", [p2, p4])])

    player_names = {
        str(p1.value): "Luis",
        str(p2.value): "Carlos",
        str(p3.value): "Pedro",
        str(p4.value): "Juan",
    }
    player_groups = {
        str(p1.value): "regular",
        str(p2.value): "regular",
        str(p3.value): "substitute",
        str(p4.value): "substitute",
    }
    text = format_subs_message(meetup, player_names, player_groups)

    assert "⚪" in text
    assert "⚫" in text
    assert "Pedro" in text
    assert "Juan" in text


def test_format_subs_message_with_result_simple():
    """When there's a result, show simple 'Partido terminado'."""
    meetup = Meetup.create(datetime(2024, 1, 15, 20, 0), "Parque Central")
    p1 = PlayerId.generate()
    meetup.add_player(p1)
    team_a, team_b = Team.create("A", [p1]), Team.create("B", [])
    meetup.set_teams([team_a, team_b])
    meetup.add_match(
        Match(teams_playing=(team_a, team_b), result=MatchResult(score_a=1, score_b=0, events=()))
    )
    meetup.close()

    player_names = {str(p1.value): "Luis"}
    player_groups = {str(p1.value): "regular"}
    text = format_subs_message(meetup, player_names, player_groups)

    assert "*Partido terminado*" in text
    assert "Suplentes" not in text


def test_format_subs_message():
    meetup = Meetup.create(datetime(2024, 1, 15, 20, 0), "Parque Central")
    p1 = PlayerId.generate()
    meetup.add_player(p1)

    player_names = {str(p1.value): "Pedro"}
    player_groups = {str(p1.value): "substitute"}
    text = format_subs_message(meetup, player_names, player_groups)

    assert "Suplentes" in text
    assert "Pedro" in text


def test_format_subs_message_header_matches_main_message_style():
    """Subs header uses the same 📅 Convocatoria style as titulares, no '- Suplentes'."""
    meetup = Meetup.create(datetime(2024, 1, 15, 20, 0), "Parque Central")
    p1 = PlayerId.generate()
    meetup.add_player(p1)

    player_names = {str(p1.value): "Pedro"}
    player_groups = {str(p1.value): "substitute"}
    text = format_subs_message(meetup, player_names, player_groups)

    assert "📅 *Convocatoria:*" in text
    assert "- Suplentes" not in text
    assert r"\- Suplentes" not in text


def test_format_subs_message_shows_location():
    """Subs header includes 📍 Lugar line when the meetup has a location."""
    meetup = Meetup.create(datetime(2024, 1, 15, 20, 0), "Parque Central")
    p1 = PlayerId.generate()
    meetup.add_player(p1)

    player_names = {str(p1.value): "Pedro"}
    player_groups = {str(p1.value): "substitute"}
    text = format_subs_message(meetup, player_names, player_groups)

    assert "📍 *Lugar:* Parque Central" in text


def test_format_main_message_all_unmasked():
    meetup = Meetup.create(datetime(2024, 3, 20, 20, 0), "Parque Central")
    p_regular = PlayerId.generate()
    p_substitute = PlayerId.generate()
    meetup.add_player(p_regular)
    meetup.add_player(p_substitute)

    player_names = {str(p_regular.value): "Mario", str(p_substitute.value): "Luigi"}

    text = format_main_message(meetup, player_names)

    assert "Mario" in text
    assert "Luigi" in text


def test_format_subs_message_masked_regulars():
    meetup = Meetup.create(datetime(2024, 3, 20, 20, 0), "Parque Central")
    p_regular = PlayerId.generate()
    p_substitute = PlayerId.generate()
    meetup.add_player(p_regular)
    meetup.add_player(p_substitute)

    player_names = {str(p_regular.value): "Mario", str(p_substitute.value): "Luigi"}
    player_groups = {str(p_regular.value): "regular", str(p_substitute.value): "substitute"}

    text = format_subs_message(meetup, player_names, player_groups)

    assert "Mario" not in text
    assert "Luigi" in text


def test_escape_mdv2_special_characters():
    assert _escape_mdv2("Hello (world)") == r"Hello \(world\)"
    assert _escape_mdv2("score: 1.0") == r"score: 1\.0"
    assert _escape_mdv2("player_name") == r"player\_name"


def test_escape_summary_for_telegram_preserves_bold_pairs():
    """Text between a pair of asterisks stays wrapped in real bold delimiters."""
    result = escape_summary_for_telegram("⚪ *Blanco - 2*")
    assert result == r"⚪ *Blanco \- 2*"


def test_escape_summary_for_telegram_escapes_special_characters():
    """Special MarkdownV2 characters outside bold spans are escaped."""
    result = escape_summary_for_telegram("Nacho (Luvo)\nscore: 1.0")
    assert result == "Nacho \\(Luvo\\)\nscore: 1\\.0"


def test_escape_summary_for_telegram_handles_multiple_bold_spans():
    """Multiple bold spans in the same text are all preserved correctly."""
    result = escape_summary_for_telegram("*RESULTADO:*\n\n⚪ *Blanco - 2*\nAna\n\n⚫ *Negro - 0*")
    assert result == "*RESULTADO:*\n\n⚪ *Blanco \\- 2*\nAna\n\n⚫ *Negro \\- 0*"


def test_format_main_message_team_emojis():
    """Teams should show the configured emojis."""
    meetup = Meetup.create(datetime(2024, 1, 15, 20, 0), "Parque Central")
    p1 = PlayerId.generate()
    p2 = PlayerId.generate()
    meetup.add_player(p1)
    meetup.add_player(p2)
    meetup.set_teams([Team.create("A", [p1]), Team.create("B", [p2])])

    player_names = {str(p1.value): "Luis", str(p2.value): "Carlos"}
    text = format_main_message(
        meetup, player_names, team_colors=("blanco", "negro"), team_emojis=("⚪", "⚫")
    )

    assert "⚪" in text
    assert "⚫" in text


def test_format_main_message_with_teams():
    meetup = Meetup.create(datetime(2024, 1, 15, 20, 0), "Parque Central")
    p1 = PlayerId.generate()
    p2 = PlayerId.generate()
    meetup.add_player(p1)
    meetup.add_player(p2)
    meetup.set_teams([Team.create("A", [p1]), Team.create("B", [p2])])

    player_names = {str(p1.value): "Luis", str(p2.value): "Carlos"}
    text = format_main_message(
        meetup, player_names, team_colors=("blanco", "negro"), team_emojis=("⚪", "⚫")
    )

    assert "*Equipos:*" in text
    assert "Blanco" in text
    assert "Negro" in text
    assert "⚪" in text
    assert "⚫" in text
    assert "Luis" in text or "Carlos" in text


def test_format_main_message_with_teams_shows_color_as_name():
    """format_main_message uses capitalized color name as team display name."""
    meetup = Meetup.create(datetime(2024, 1, 15, 20, 0), "Parque Central")
    p1 = PlayerId.generate()
    p2 = PlayerId.generate()
    meetup.add_player(p1)
    meetup.add_player(p2)
    meetup.set_teams([Team.create("A", [p1]), Team.create("B", [p2])])

    player_names = {str(p1.value): "Luis", str(p2.value): "Carlos"}
    text = format_main_message(
        meetup, player_names, team_colors=("amarillo", "negro"), team_emojis=("🟡", "⚫")
    )

    assert "Amarillo" in text
    assert "Negro" in text
    assert "*A:*" not in text
    assert "*B:*" not in text


def test_format_main_message_with_result_shows_events():
    """When there's a result, show the unified *GOLES:* section with timestamps."""
    meetup = Meetup.create(datetime(2026, 4, 12, 20, 0), "Campo Norte")
    p1 = PlayerId.generate()
    p2 = PlayerId.generate()
    team_a, team_b = Team.create("A", [p1]), Team.create("B", [p2])
    meetup.teams = [team_a, team_b]

    event1 = GoalEvent(
        scorer_id=p1,
        assistant_id=p2,
        team="A",
        timestamp=time(20, 10),
    )
    event2 = GoalEvent(
        scorer_id=p2,
        assistant_id=None,
        team="B",
        timestamp=time(20, 25),
    )
    meetup.add_match(
        Match(
            teams_playing=(team_a, team_b),
            result=MatchResult(score_a=1, score_b=1, events=(event1, event2)),
        )
    )
    meetup.close()

    player_names = {str(p1.value): "Dani", str(p2.value): "Rafa"}
    text = format_main_message(
        meetup, player_names, team_colors=("blanco", "negro"), team_emojis=("⚪", "⚫")
    )

    assert "*GOLES:*" in text
    assert r"  \- ⚽ 10' Dani \(asist\. Rafa\)" in text
    assert r"  \- ⚽ 25' Rafa" in text


def test_format_main_message_with_result_shows_score():
    """When meetup has a result, format_main_message shows score next to team name."""
    meetup = Meetup.create(datetime(2026, 4, 12, 20, 0), "Campo Norte")
    p1 = PlayerId.generate()
    p2 = PlayerId.generate()
    team_a, team_b = Team.create("A", [p1]), Team.create("B", [p2])
    meetup.teams = [team_a, team_b]
    event = GoalEvent(scorer_id=p1, assistant_id=None, team="A", timestamp=time(20, 15))
    meetup.add_match(
        Match(
            teams_playing=(team_a, team_b),
            result=MatchResult(score_a=3, score_b=1, events=(event,)),
        )
    )
    meetup.close()

    player_names = {str(p1.value): "Dani", str(p2.value): "Rafa"}
    text = format_main_message(
        meetup, player_names, team_colors=("blanco", "negro"), team_emojis=("⚪", "⚫")
    )

    assert "Blanco" in text and "3" in text
    assert "Negro" in text and "1" in text
    assert "Dani" in text
    assert "Rafa" in text


def test_format_subs_message_with_result_shows_score():
    """When meetup has a result, format_subs_message shows simple terminated message."""
    meetup = Meetup.create(datetime(2026, 4, 12, 20, 0), "Campo Norte")
    p1 = PlayerId.generate()
    p2 = PlayerId.generate()
    team_a, team_b = Team.create("A", [p1]), Team.create("B", [p2])
    meetup.teams = [team_a, team_b]
    meetup.add_match(
        Match(teams_playing=(team_a, team_b), result=MatchResult(score_a=2, score_b=0, events=()))
    )
    meetup.close()

    player_names = {str(p1.value): "Dani", str(p2.value): "Rafa"}
    player_groups = {str(p1.value): "regular", str(p2.value): "regular"}
    text = format_subs_message(meetup, player_names, player_groups)

    assert "*Partido terminado*" in text


def test_format_main_message_shows_latest_match_score_for_triangular():
    """For a triangular, each team's score line reflects its most recent match, if any."""
    meetup = Meetup.create(datetime(2026, 5, 1, 20, 0), "Campo")
    p1, p2, p3 = PlayerId.generate(), PlayerId.generate(), PlayerId.generate()
    team_a, team_b, team_c = (
        Team.create("A", [p1]),
        Team.create("B", [p2]),
        Team.create("C", [p3]),
    )
    meetup.teams = [team_a, team_b, team_c]
    meetup.add_match(Match(teams_playing=(team_a, team_b), result=MatchResult(2, 0, ())))
    meetup.add_match(Match(teams_playing=(team_a, team_c)))  # pending

    text = format_main_message(
        meetup, {}, team_colors=("blanco", "negro", "rojo"), team_emojis=("⚪", "⚫", "🔴")
    )

    assert "Blanco" in text and "Negro" in text and "Rojo" in text
    assert r"\(2\)" in text  # team A's latest score
    assert r"\(0\)" in text  # team B's latest score


def test_format_display_default_fmt():
    """format_display formats with the default format."""
    dt = datetime(2026, 4, 15, 20, 0)
    assert format_display(dt) == "2026-04-15 20:00"


def test_format_display_custom_fmt():
    """format_display respects a custom fmt argument."""
    dt = datetime(2026, 4, 15, 20, 0)
    assert format_display(dt, "%d/%m/%Y %H:%M") == "15/04/2026 20:00"


def test_parse_display_default_fmt():
    """parse_display parses with the default format."""
    result = parse_display("2026-04-15 20:00")
    assert result == datetime(2026, 4, 15, 20, 0)


def test_parse_display_custom_fmt():
    """parse_display respects a custom fmt argument."""
    result = parse_display("15/04/2026 20:00", "%d/%m/%Y %H:%M")
    assert result == datetime(2026, 4, 15, 20, 0)


def test_parse_display_invalid_raises():
    """parse_display raises ValueError on bad input."""
    with pytest.raises(ValueError):
        parse_display("not-a-date")
