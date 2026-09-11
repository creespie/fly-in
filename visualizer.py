"""Visualizzatore Pygame per la simulazione Fly-in.

Trasforma l'output testuale (vedi ``drones.generate_lines``) in
una serie di turni visualizzabili.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Optional

import pygame

from map_creator import Node, ZoneType


# ---------------------------------------------------------------------------
# Snapshot di un drone in un singolo turno
# ---------------------------------------------------------------------------

@dataclass
class DroneSnapshot:
    """Posizione di un drone in un turno di simulazione."""

    drone_id: int
    kind: Literal["zone", "connection"]
    zone: Optional[str] = None
    connection: Optional[tuple[str, str]] = None
    progress: float = 1.0


# ---------------------------------------------------------------------------
# Parser: righe di output -> turni di snapshot
# ---------------------------------------------------------------------------

def parse_output_lines(
    lines: list[str],
    start_hub: str,
    nb_drones: int,
) -> list[dict[int, DroneSnapshot]]:
    """Converte le righe di output in snapshot per turno.

    Args:
        lines: righe prodotte da ``drones.generate_lines``.
        start_hub: nome interno dello start hub (default ``"start_hub"``).
        nb_drones: numero totale di droni, per inizializzarli tutti
            nello start hub prima che si muovano.

    Returns:
        Lista di dict ``{drone_id: DroneSnapshot}``, uno per turno.
    """
    drawn: dict[int, DroneSnapshot] = {
        i: DroneSnapshot(drone_id=i, kind="zone", zone=start_hub)
        for i in range(1, nb_drones + 1)
    }
    arrived: set[int] = set()
    turns: list[dict[int, DroneSnapshot]] = []

    for line in lines:
        seen_this_turn: set[int] = set()

        for token in line.split():
            parts = token.split("-")
            did = int(parts[0][1:])
            seen_this_turn.add(did)

            if len(parts) == 2:
                # "D1-zone"
                zone = parts[1]
                drawn[did] = DroneSnapshot(
                    drone_id=did, kind="zone", zone=zone
                )
                if zone == "goal":
                    arrived.add(did)
            else:
                # "D1-a-b" -> transito sulla connessione a-b
                a, b = parts[1], parts[2]
                prev = drawn.get(did)
                from_zone = (
                    prev.zone
                    if prev and prev.kind == "zone" and prev.zone
                    else a
                )
                to_zone = b if from_zone == a else a
                drawn[did] = DroneSnapshot(
                    drone_id=did,
                    kind="connection",
                    connection=(from_zone, to_zone),
                )

        turn_snap: dict[int, DroneSnapshot] = {}
        for did, snap in drawn.items():
            if did in arrived and did not in seen_this_turn:
                continue
            turn_snap[did] = snap
        turns.append(turn_snap)

    return turns


# ---------------------------------------------------------------------------
# Colori
# ---------------------------------------------------------------------------

COLOR_MAP: dict[str, tuple[int, int, int]] = {
    "red": (220, 60, 60),
    "green": (60, 180, 75),
    "blue": (60, 90, 220),
    "yellow": (240, 220, 60),
    "gray": (140, 140, 140),
    "grey": (140, 140, 140),
    "white": (230, 230, 230),
    "black": (40, 40, 40),
    "orange": (240, 140, 40),
    "purple": (160, 60, 200),
    "cyan": (60, 200, 200),
    "magenta": (220, 60, 200),
    "pink": (240, 130, 180),
}


# ---------------------------------------------------------------------------
# Visualizer
# ---------------------------------------------------------------------------

class PygameVisualizer:
    """Visualizzatore grafico basato su Pygame."""

    NODE_RADIUS: int = 26
    DRONE_RADIUS: int = 7

    def __init__(
        self,
        width: int = 1200,
        height: int = 800,
        margin: int = 90,
    ) -> None:
        pygame.init()
        pygame.display.set_caption("Fly-in Drones")
        self.screen: pygame.Surface = pygame.display.set_mode((width, height))
        self.clock: pygame.time.Clock = pygame.time.Clock()
        self.font: pygame.font.Font = pygame.font.SysFont("Arial", 14)
        self.font_small: pygame.font.Font = pygame.font.SysFont("Arial", 11)
        self.font_bold: pygame.font.Font = pygame.font.SysFont(
            "Arial", 15, bold=True
        )
        self.width: int = width
        self.height: int = height
        self.margin: int = margin

        self.positions: dict[str, tuple[int, int]] = {}
        self._nodes: dict[str, Node] = {}
        self._connections: list[tuple[str, str]] = []

    # ------------------------------------------------------------------
    # Setup
    # ------------------------------------------------------------------

    def _compute_positions(self, nodes: dict[str, Node]) -> None:
        if not nodes:
            self.positions = {}
            return
        xs = [n.coords[0] for n in nodes.values()]
        ys = [n.coords[1] for n in nodes.values()]
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)
        span_x = max(max_x - min_x, 1)
        span_y = max(max_y - min_y, 1)
        usable_w = self.width - 2 * self.margin
        usable_h = self.height - 2 * self.margin

        self.positions = {}
        for name, node in nodes.items():
            px = self.margin + int((node.coords[0] - min_x) / span_x * usable_w)
            py = self.margin + int((node.coords[1] - min_y) / span_y * usable_h)
            self.positions[name] = (px, py)

    def _collect_connections(self, nodes: dict[str, Node]) -> None:
        seen: set[frozenset[str]] = set()
        self._connections = []
        for node in nodes.values():
            for other_name in node.contacts:
                key = frozenset({node.name, other_name})
                if key in seen:
                    continue
                seen.add(key)
                self._connections.append((node.name, other_name))

    # ------------------------------------------------------------------
    # Disegno
    # ------------------------------------------------------------------

    def _zone_color(self, node: Node) -> tuple[int, int, int]:
        if node.zone == ZoneType.BLOCKED:
            return (50, 50, 50)
        if node.name == "start_hub":
            return (60, 180, 75)
        if node.name == "goal":
            return (220, 60, 60)
        key = (node.color or "white").lower()
        return COLOR_MAP.get(key, (170, 170, 170))

    def draw_network(self) -> None:
        # Connessioni
        for a, b in self._connections:
            p1 = self.positions.get(a)
            p2 = self.positions.get(b)
            if p1 is None or p2 is None:
                continue
            pygame.draw.line(self.screen, (170, 170, 170), p1, p2, 3)

        # Nodi
        for name, node in self._nodes.items():
            pos = self.positions.get(name)
            if pos is None:
                continue
            color = self._zone_color(node)
            pygame.draw.circle(self.screen, color, pos, self.NODE_RADIUS)

            border: tuple[int, int, int] = (0, 0, 0)
            if node.zone == ZoneType.PRIORITY:
                border = (255, 200, 0)
            pygame.draw.circle(self.screen, border, pos, self.NODE_RADIUS, 3)

            # Etichetta nome
            label = self.font.render(name, True, (20, 20, 20))
            label_rect = label.get_rect(
                center=(pos[0], pos[1] + self.NODE_RADIUS + 12)
            )
            bg = pygame.Surface(
                (label_rect.width + 6, label_rect.height + 2),
                pygame.SRCALPHA,
            )
            bg.fill((255, 255, 255, 200))
            self.screen.blit(bg, (label_rect.x - 3, label_rect.y - 1))
            self.screen.blit(label, label_rect)

            # Badge tipo zona
            badge_text = ""
            badge_color: tuple[int, int, int] = (0, 0, 0)
            if node.zone == ZoneType.RESTRICTED:
                badge_text = "R"
                badge_color = (255, 255, 255)
            elif node.zone == ZoneType.PRIORITY:
                badge_text = "P"
                badge_color = (0, 0, 0)
            elif node.zone == ZoneType.BLOCKED:
                badge_text = "X"
                badge_color = (255, 255, 255)

            if badge_text:
                badge = self.font_bold.render(badge_text, True, badge_color)
                self.screen.blit(
                    badge,
                    (
                        pos[0] - badge.get_width() // 2,
                        pos[1] - badge.get_height() // 2,
                    ),
                )

    def _grid_offset(self, idx: int, total: int) -> tuple[int, int]:
        if total <= 1:
            return (0, 0)
        cols = min(total, 4)
        rows = (total + cols - 1) // cols
        spacing = 12
        row, col = divmod(idx, cols)
        x = int((col - (cols - 1) / 2) * spacing)
        y = int((row - (rows - 1) / 2) * spacing)
        return (x, y)

    def draw_drones(self, turn: dict[int, DroneSnapshot]) -> None:
        per_zone: dict[str, list[int]] = {}
        for did, snap in turn.items():
            if snap.kind == "zone" and snap.zone:
                per_zone.setdefault(snap.zone, []).append(did)

        for did, snap in sorted(turn.items()):
            pos: Optional[tuple[int, int]] = None
            color: tuple[int, int, int] = (255, 255, 255)

            if snap.kind == "zone" and snap.zone:
                base = self.positions.get(snap.zone)
                if base is None:
                    continue
                group = per_zone[snap.zone]
                idx = group.index(did)
                off = self._grid_offset(idx, len(group))
                pos = (base[0] + off[0], base[1] + off[1])
            elif snap.kind == "connection" and snap.connection:
                a, b = snap.connection
                p1 = self.positions.get(a)
                p2 = self.positions.get(b)
                if p1 is None or p2 is None:
                    continue
                t = snap.progress
                pos = (
                    int(p1[0] + (p2[0] - p1[0]) * t),
                    int(p1[1] + (p2[1] - p1[1]) * t),
                )
                color = (255, 165, 0)

            if pos is None:
                continue

            pygame.draw.circle(self.screen, color, pos, self.DRONE_RADIUS)
            pygame.draw.circle(
                self.screen, (0, 0, 0), pos, self.DRONE_RADIUS, 2
            )
            tag = self.font_small.render(f"D{did}", True, (0, 0, 0))
            self.screen.blit(
                tag,
                (
                    pos[0] - tag.get_width() // 2,
                    pos[1] - self.DRONE_RADIUS - 14,
                ),
            )

    # ------------------------------------------------------------------
    # Loop principale
    # ------------------------------------------------------------------

    def run_replay(
        self,
        turns: list[dict[int, DroneSnapshot]],
        nodes: dict[str, Node],
        turn_delay_ms: int = 500,
    ) -> None:
        """Avvia il replay grafico della simulazione.

        Args:
            turns: snapshot per turno, come da ``parse_output_lines``.
            nodes: mappa dei nodi del grafo (``Node.nodes``).
            turn_delay_ms: millisecondi tra un turno e il successivo.
        """
        if not turns:
            return

        self._nodes = nodes
        self._compute_positions(nodes)
        self._collect_connections(nodes)

        running = True
        idx = 0
        acc = 0
        paused = False

        try:
            while running:
                dt = self.clock.tick(60)
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        running = False
                    elif event.type == pygame.KEYDOWN:
                        if event.key == pygame.K_ESCAPE:
                            running = False
                        elif event.key == pygame.K_RIGHT:
                            idx = min(idx + 1, len(turns) - 1)
                            acc = 0
                        elif event.key == pygame.K_LEFT:
                            idx = max(idx - 1, 0)
                            acc = 0
                        elif event.key == pygame.K_r:
                            idx = 0
                            acc = 0
                        elif event.key == pygame.K_SPACE:
                            paused = not paused

                if not paused:
                    acc += dt
                    if acc >= turn_delay_ms and idx < len(turns) - 1:
                        idx += 1
                        acc = 0

                self.screen.fill((245, 245, 245))
                self.draw_network()
                self.draw_drones(turns[idx])

                hud = f"Turn {idx + 1}/{len(turns)}"
                if paused:
                    hud += "  [PAUSED]"
                hud += "   |   <- -> step, SPACE pause, R reset, ESC exit"
                text = self.font.render(hud, True, (20, 20, 20))
                self.screen.blit(text, (12, 10))

                pygame.display.flip()
        finally:
            pygame.quit()