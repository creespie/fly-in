"""Visualizzatore Pygame con animazione fluida per Fly-in."""
from __future__ import annotations

import colorsys
import math
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
        nb_drones: numero totale di droni.

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
                zone = parts[1]
                drawn[did] = DroneSnapshot(
                    drone_id=did, kind="zone", zone=zone
                )
                if zone == "goal":
                    arrived.add(did)
            else:
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
    """Visualizzatore grafico con animazione fluida."""

    NODE_RADIUS: int = 26
    DRONE_RADIUS: int = 9
    MIN_NODE_DISTANCE: int = 60  # pixel minimi tra i centri dei nodi

    def __init__(
        self,
        width: int = 1500,
        height: int = 1000,
        margin: int = 110,
    ) -> None:
        pygame.init()
        pygame.display.set_caption("Fly-in Drones")
        self.screen: pygame.Surface = pygame.display.set_mode((width, height))
        self.clock: pygame.time.Clock = pygame.time.Clock()
        self.font: pygame.font.Font = pygame.font.SysFont("Arial", 15)
        self.font_small: pygame.font.Font = pygame.font.SysFont("Arial", 12)
        self.font_bold: pygame.font.Font = pygame.font.SysFont(
            "Arial", 17, bold=True
        )
        self.width: int = width
        self.height: int = height
        self.margin: int = margin

        self.positions: dict[str, tuple[int, int]] = {}
        self._nodes: dict[str, Node] = {}
        self._connections: list[tuple[str, str]] = []
        self._drone_colors: dict[int, tuple[int, int, int]] = {}

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------

    def _compute_positions(self, nodes: dict[str, Node]) -> None:
        """Calcola le posizioni pixel dei nodi.

        Usa scaling indipendente sugli assi per massimizzare la distanza,
        poi applica un pass di push-apart per evitare sovrapposizioni.
        """
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

        # Layout iniziale: scaling indipendente per asse
        layout: dict[str, list[float]] = {}
        for name, node in nodes.items():
            px = self.margin + (node.coords[0] - min_x) / span_x * usable_w
            py = self.margin + (node.coords[1] - min_y) / span_y * usable_h
            layout[name] = [px, py]

        # Push-apart iterativo: nessun nodo più vicino di MIN_NODE_DISTANCE
        names = list(layout.keys())
        min_d = float(self.MIN_NODE_DISTANCE)
        for _ in range(80):
            moved = False
            for i in range(len(names)):
                for j in range(i + 1, len(names)):
                    n1, n2 = names[i], names[j]
                    p1, p2 = layout[n1], layout[n2]
                    dx = p2[0] - p1[0]
                    dy = p2[1] - p1[1]
                    d = math.hypot(dx, dy)
                    if d < 1e-3:
                        # Sovrapposti: separa lungo una direzione fissa
                        dx, dy, d = 1.0, 0.0, 1.0
                    if d < min_d:
                        push = (min_d - d) / 2.0
                        ux, uy = dx / d, dy / d
                        p1[0] -= ux * push
                        p1[1] -= uy * push
                        p2[0] += ux * push
                        p2[1] += uy * push
                        moved = True
            if not moved:
                break

        # Clamp dentro la finestra (rispettando il margine)
        r = self.NODE_RADIUS + 30
        for p in layout.values():
            p[0] = max(r, min(self.width - r, p[0]))
            p[1] = max(r, min(self.height - r, p[1]))

        self.positions = {
            name: (int(p[0]), int(p[1])) for name, p in layout.items()
        }

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
    # Colori per drone
    # ------------------------------------------------------------------

    def _drone_color(self, did: int) -> tuple[int, int, int]:
        cached = self._drone_colors.get(did)
        if cached is not None:
            return cached
        # Distribuzione aurea sull'hue per colori distinti
        h = (did * 0.618033988749895) % 1.0
        r, g, b = colorsys.hsv_to_rgb(h, 0.62, 0.98)
        color = (int(r * 255), int(g * 255), int(b * 255))
        self._drone_colors[did] = color
        return color

    # ------------------------------------------------------------------
    # Disegno rete
    # ------------------------------------------------------------------

    def _zone_color(self, node: Node) -> tuple[int, int, int]:
        if node.zone == ZoneType.BLOCKED:
            return (55, 55, 55)
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
            pygame.draw.line(self.screen, (175, 175, 175), p1, p2, 4)

        # Nodi
        for name, node in self._nodes.items():
            pos = self.positions.get(name)
            if pos is None:
                continue
            color = self._zone_color(node)

            # Alone esterno per zone speciali
            if node.zone == ZoneType.PRIORITY:
                pygame.draw.circle(
                    self.screen, (255, 220, 90), pos, self.NODE_RADIUS + 6
                )
            elif node.zone == ZoneType.RESTRICTED:
                pygame.draw.circle(
                    self.screen, (255, 120, 120), pos, self.NODE_RADIUS + 6
                )

            pygame.draw.circle(self.screen, color, pos, self.NODE_RADIUS)
            pygame.draw.circle(
                self.screen, (0, 0, 0), pos, self.NODE_RADIUS, 3
            )

            # Etichetta nome
            label = self.font.render(name, True, (20, 20, 20))
            label_rect = label.get_rect(
                center=(pos[0], pos[1] + self.NODE_RADIUS + 14)
            )
            bg = pygame.Surface(
                (label_rect.width + 8, label_rect.height + 4),
                pygame.SRCALPHA,
            )
            bg.fill((255, 255, 255, 215))
            self.screen.blit(bg, (label_rect.x - 4, label_rect.y - 2))
            self.screen.blit(label, label_rect)

            # Badge tipo
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

    # ------------------------------------------------------------------
    # Target per drone (calcolato per frame)
    # ------------------------------------------------------------------

    def _grid_offset(self, idx: int, total: int) -> tuple[float, float]:
        if total <= 1:
            return (0.0, 0.0)
        cols = min(total, 4)
        rows = (total + cols - 1) // cols
        spacing = 14.0
        row, col = divmod(idx, cols)
        x = (col - (cols - 1) / 2.0) * spacing
        y = (row - (rows - 1) / 2.0) * spacing
        return (x, y)

    def _target_positions(
        self, turn: dict[int, DroneSnapshot]
    ) -> dict[int, tuple[float, float]]:
        per_zone: dict[str, list[int]] = {}
        for did, snap in turn.items():
            if snap.kind == "zone" and snap.zone:
                per_zone.setdefault(snap.zone, []).append(did)

        targets: dict[int, tuple[float, float]] = {}
        for did, snap in turn.items():
            if snap.kind == "zone" and snap.zone:
                base = self.positions.get(snap.zone)
                if base is None:
                    continue
                group = per_zone[snap.zone]
                idx = group.index(did)
                ox, oy = self._grid_offset(idx, len(group))
                targets[did] = (base[0] + ox, base[1] + oy)
            elif snap.kind == "connection" and snap.connection:
                a, b = snap.connection
                p1 = self.positions.get(a)
                p2 = self.positions.get(b)
                if p1 is None or p2 is None:
                    continue
                t = snap.progress
                targets[did] = (
                    p1[0] + (p2[0] - p1[0]) * t,
                    p1[1] + (p2[1] - p1[1]) * t,
                )
        return targets

    def draw_drones(
        self, positions: dict[int, tuple[float, float]]
    ) -> None:
        for did in sorted(positions):
            x, y = positions[did]
            pos = (int(x), int(y))
            color = self._drone_color(did)

            # Alone
            glow = pygame.Surface((40, 40), pygame.SRCALPHA)
            pygame.draw.circle(glow, (*color, 70), (20, 20), 18)
            self.screen.blit(glow, (pos[0] - 20, pos[1] - 20))

            pygame.draw.circle(self.screen, color, pos, self.DRONE_RADIUS)
            pygame.draw.circle(
                self.screen, (0, 0, 0), pos, self.DRONE_RADIUS, 2
            )
            tag = self.font_small.render(f"D{did}", True, (0, 0, 0))
            self.screen.blit(
                tag,
                (
                    pos[0] - tag.get_width() // 2,
                    pos[1] - self.DRONE_RADIUS - 16,
                ),
            )

    # ------------------------------------------------------------------
    # Loop principale con animazione
    # ------------------------------------------------------------------

    def run_replay(
        self,
        turns: list[dict[int, DroneSnapshot]],
        nodes: dict[str, Node],
        turn_delay_ms: int = 600,
    ) -> None:
        """Replay animato della simulazione.

        Args:
            turns: snapshot per turno.
            nodes: mappa dei nodi (``Node.nodes``).
            turn_delay_ms: millisecondi tra un turno e il successivo.
        """
        if not turns:
            return

        self._nodes = nodes
        self._compute_positions(nodes)
        self._collect_connections(nodes)

        # Stato animazione: posizione corrente (float) di ogni drone
        anim: dict[int, list[float]] = {}
        for did in range(1, 10000):
            snap = turns[0].get(did)
            if snap is None:
                continue
            tx, ty = self._target_positions({did: snap}).get(did, (0, 0))
            anim[did] = [float(tx), float(ty)]

        running = True
        idx = 0
        acc = 0
        paused = False

        # Smoothing: alpha = 1 - exp(-dt / tau), con tau in secondi
        tau = max(turn_delay_ms / 1000.0 / 3.0, 0.05)

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
                            # reset posizioni
                            for did in list(anim.keys()):
                                snap = turns[0].get(did)
                                if snap is None:
                                    continue
                                tgt = self._target_positions({did: snap})
                                if did in tgt:
                                    anim[did] = [
                                        float(tgt[did][0]),
                                        float(tgt[did][1]),
                                    ]
                        elif event.key == pygame.K_SPACE:
                            paused = not paused

                if not paused:
                    acc += dt
                    if acc >= turn_delay_ms and idx < len(turns) - 1:
                        idx += 1
                        acc = 0

                # Inizializza nuovi droni che compaiono (raro)
                for did in turns[idx]:
                    if did not in anim:
                        tgt = self._target_positions(turns[idx]).get(did)
                        if tgt is not None:
                            anim[did] = [float(tgt[0]), float(tgt[1])]

                # Calcola target per il turno corrente
                targets = self._target_positions(turns[idx])

                # Smoothing esponenziale frame-rate independent
                alpha = 1.0 - math.exp(-dt / 1000.0 / tau)
                for did, (tx, ty) in targets.items():
                    if did not in anim:
                        anim[did] = [float(tx), float(ty)]
                        continue
                    cur = anim[did]
                    cur[0] += (tx - cur[0]) * alpha
                    cur[1] += (ty - cur[1]) * alpha

                # Render
                self.screen.fill((245, 245, 245))
                self.draw_network()

                rendered = {did: (p[0], p[1]) for did, p in anim.items()
                            if did in targets}
                self.draw_drones(rendered)

                hud = f"Turn {idx + 1}/{len(turns)}"
                if paused:
                    hud += "  [PAUSED]"
                hud += "   |   <- -> step, SPACE pause, R reset, ESC exit"
                text = self.font.render(hud, True, (20, 20, 20))
                self.screen.blit(text, (12, 10))

                pygame.display.flip()
        finally:
            pygame.quit()