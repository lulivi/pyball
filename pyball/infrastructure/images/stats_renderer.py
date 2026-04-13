"""Statistics image renderer using matplotlib."""

from __future__ import annotations

import io

import matplotlib.pyplot as plt

from matplotlib.axes import Axes
from matplotlib.ticker import MaxNLocator

from pyball.application.meetup.compute_stats import (
    ChemistryPair,
    PlayerStats,
    StatsReport,
    StatsScopedReport,
)

plt.switch_backend("agg")

_TREND_SYMBOLS = {None: "★ ", "up": "▲ ", "down": "▼ ", "same": "─ "}
_COLOR_GOALS = "#e74c3c"
_COLOR_ASSISTS = "#3498db"
_COLOR_CHEMISTRY = "#2ecc71"
_COLOR_TABLE_HEADER = "#2c3e50"
_COLOR_TABLE_ROW_ODD = "#ecf0f1"
_COLOR_TABLE_ROW_EVEN = "#ffffff"


def _trend_prefix(rank_delta: int | None) -> str:
    """Return a unicode trend symbol based on rank_delta."""
    if rank_delta is None:
        return _TREND_SYMBOLS[None]
    if rank_delta > 0:
        return _TREND_SYMBOLS["up"]
    if rank_delta < 0:
        return _TREND_SYMBOLS["down"]
    return _TREND_SYMBOLS["same"]


def _labeled_name(player: PlayerStats) -> str:
    """Return the player name prefixed with its trend symbol."""
    return f"{_trend_prefix(player.rank_delta)}{player.player_name}"


class StatsImageRenderer:
    """Renders a StatsReport into two PNG images (season and all-time)."""

    def render(self, report: StatsReport) -> tuple[bytes, bytes]:
        """Generate PNG images for season and all-time scopes.

        Args:
            report: Fully computed StatsReport.

        Returns:
            Tuple of (season_png, all_time_png) as raw bytes.
        """
        return (
            self._render_scope(report.season, "Esta temporada"),
            self._render_scope(report.all_time, "Histórico"),
        )

    def _render_scope(self, scoped: StatsScopedReport, title: str) -> bytes:
        """Render a single scope into a PNG bytes object."""
        top_players = scoped.players[:10]
        top_chemistry = scoped.chemistry[:10]

        fig, axes = plt.subplots(3, 1, figsize=(8, 14))
        fig.suptitle(title, fontsize=16, fontweight="bold", y=0.98)

        self._render_goals_assists(axes[0], top_players)
        self._render_points_table(axes[1], top_players)
        self._render_chemistry(axes[2], top_chemistry)

        plt.tight_layout(rect=(0, 0, 1, 0.97))

        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=100, bbox_inches="tight")
        plt.close(fig)
        buf.seek(0)
        return buf.read()

    def _render_goals_assists(self, ax: Axes, players: list[PlayerStats]) -> None:
        """Render the goals & assists horizontal grouped bar chart."""
        ax.set_title("Goles y asistencias", fontweight="bold")

        if not players:
            ax.axis("off")
            ax.text(0.5, 0.5, "Sin datos", ha="center", va="center", transform=ax.transAxes)
            return

        sorted_players = sorted(players, key=lambda p: p.goals, reverse=True)
        names = [_labeled_name(p) for p in sorted_players]
        goals = [p.goals for p in sorted_players]
        assists = [p.assists for p in sorted_players]
        y = list(range(len(names)))

        ax.barh([i + 0.2 for i in y], goals, height=0.4, label="Goles", color=_COLOR_GOALS)
        ax.barh([i - 0.2 for i in y], assists, height=0.4, label="Asist.", color=_COLOR_ASSISTS)
        ax.set_yticks(y)
        ax.set_yticklabels(names, fontsize=9)
        ax.invert_yaxis()
        ax.legend(fontsize=8)
        ax.xaxis.set_major_locator(MaxNLocator(integer=True))

    def _render_points_table(self, ax: Axes, players: list[PlayerStats]) -> None:
        """Render the points ranking as a matplotlib table."""
        ax.set_title("Clasificación", fontweight="bold")
        ax.axis("off")

        if not players:
            ax.text(0.5, 0.5, "Sin datos", ha="center", va="center", transform=ax.transAxes)
            return

        col_labels = ["Jugador", "PJ", "G", "E", "P", "Pts"]
        table_data = [
            [
                _labeled_name(p),
                str(p.matches_played),
                str(p.wins),
                str(p.draws),
                str(p.losses),
                str(p.points),
            ]
            for p in players
        ]

        table = ax.table(
            cellText=table_data,
            colLabels=col_labels,
            loc="center",
            cellLoc="center",
        )
        table.auto_set_font_size(False)
        table.set_fontsize(9)
        table.scale(1, 1.4)

        for (row, col), cell in table.get_celld().items():
            if row == 0:
                cell.set_facecolor(_COLOR_TABLE_HEADER)
                cell.set_text_props(color="white", fontweight="bold")
            else:
                cell.set_facecolor(_COLOR_TABLE_ROW_ODD if row % 2 == 1 else _COLOR_TABLE_ROW_EVEN)
            if col == 0:
                cell.set_text_props(ha="left")

    def _render_chemistry(self, ax: Axes, chemistry: list[ChemistryPair]) -> None:
        """Render the top chemistry duos as a horizontal bar chart."""
        ax.set_title("Parejas más frecuentes", fontweight="bold")

        if not chemistry:
            ax.axis("off")
            ax.text(0.5, 0.5, "Sin datos", ha="center", va="center", transform=ax.transAxes)
            return

        labels = [f"{c.scorer_name} + {c.assistant_name}" for c in chemistry]
        counts = [c.count for c in chemistry]

        ax.barh(labels, counts, color=_COLOR_CHEMISTRY)
        ax.invert_yaxis()
        ax.xaxis.set_major_locator(MaxNLocator(integer=True))
        ax.tick_params(axis="y", labelsize=9)
