"""Simple Dijkstra pathfinding on top of the parser's Graph/Node classes."""

from __future__ import annotations

import heapq
from typing import Optional

from map_creator import Node, ZoneType


class Path:
    """A concrete route from a start node to an end node."""

    def __init__(self, nodes: list[Node], cost: int) -> None:
        """Store the ordered list of nodes and the total turn cost.

        Args:
            nodes: Ordered list of nodes from start to end (inclusive).
            cost: Total movement cost in turns to traverse this path.
        """
        self.nodes = nodes
        self.cost = cost

    @property
    def names(self) -> list[str]:
        """Return the path as an ordered list of zone names."""
        return [node.name for node in self.nodes]

    def __repr__(self) -> str:
        """Return a debug-friendly representation of the path."""
        return f"Path({'->'.join(self.names)}, cost={self.cost})"


class PathFinder:
    """Computes shortest paths on a Graph using Dijkstra's algorithm."""

    def shortest_path(self, start: Node, end: Node) -> Optional[Path]:
        """Compute the cheapest path from start to end.

        Blocked zones are never entered. The cost of entering a zone is
        given by its ``move_cost`` (1 for normal/priority, 2 for
        restricted). The start zone itself has no entry cost.

        Args:
            start: The node to start from.
            end: The node to reach.

        Returns:
            A Path instance if a route exists, otherwise None.
        """
        distances: dict[str, int] = {start.name: 0}
        previous: dict[str, Node] = {}
        visited: set[str] = set()

        # Min-heap of (distance, tie_breaker, node). The tie_breaker avoids
        # comparing Node objects directly when distances are equal.
        heap: list[tuple[int, int, Node]] = [(0, 0, start)]
        counter = 1

        while heap:
            dist_u, _, u = heapq.heappop(heap)

            if u.name in visited:
                continue
            visited.add(u.name)

            if u.name == end.name:
                break

            for v in u.neighbors():
                if v.zone == ZoneType.BLOCKED or v.name in visited:
                    continue

                new_dist = dist_u + v.move_cost
                if new_dist < distances.get(v.name, float("inf")):
                    distances[v.name] = new_dist
                    previous[v.name] = u
                    heapq.heappush(heap, (new_dist, counter, v))
                    counter += 1

        if end.name not in distances:
            return None

        return Path(self._rebuild(start, end, previous), distances[end.name])

    @staticmethod
    def _rebuild(start: Node, end: Node, previous: dict[str, Node]) -> list[Node]:
        """Walk the predecessor map backward to reconstruct the path.

        Args:
            start: The origin node.
            end: The destination node.
            previous: Map from a node's name to its predecessor on the
                cheapest known path.

        Returns:
            The ordered list of nodes from start to end.
        """
        path: list[Node] = [end]
        current = end
        while current.name != start.name:
            current = previous[current.name]
            path.append(current)
        path.reverse()
        return path