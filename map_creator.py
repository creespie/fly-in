"""Parser for the Fly-in drone routing map format.

Defines the core domain objects (Node, Connection, Graph) and the
line-by-line parsing logic that turns a map file into a Graph instance.
"""

from __future__ import annotations

from enum import Enum
from typing import Optional


class ZoneType(Enum):
    """The type of a zone, which determines movement cost and access."""

    NORMAL = "normal"
    BLOCKED = "blocked"
    RESTRICTED = "restricted"
    PRIORITY = "priority"


class ParsingError(Exception):
    """Raised when a map file line is malformed or violates the format spec."""

    def __init__(self, line_number: int, message: str) -> None:
        """Store the offending line number and a human-readable reason.

        Args:
            line_number: 1-indexed line number where the error occurred.
            message: Description of what went wrong.
        """
        self.line_number = line_number
        self.message = message
        super().__init__(f"Line {line_number}: {message}")


class Connection:
    """A bidirectional link between two nodes with a traversal capacity."""

    def __init__(self, node_a: "Node", node_b: "Node", max_link_capacity: int = 1) -> None:
        """Initialize a connection between two nodes.

        Args:
            node_a: One endpoint of the connection.
            node_b: The other endpoint of the connection.
            max_link_capacity: Maximum drones allowed to traverse simultaneously.
        """
        self.node_a = node_a
        self.node_b = node_b
        self.max_link_capacity = max_link_capacity

    def other(self, node: "Node") -> "Node":
        """Return the endpoint opposite to the given node.

        Args:
            node: One of the two endpoints.

        Returns:
            The node at the other end of this connection.
        """
        return self.node_b if node is self.node_a else self.node_a


class Node:
    """A single zone in the drone network."""

    #: Movement cost in turns associated with each zone type.
    MOVE_COST = {
        ZoneType.NORMAL: 1,
        ZoneType.PRIORITY: 1,
        ZoneType.RESTRICTED: 2,
        ZoneType.BLOCKED: 0,
    }

    def __init__(
        self,
        name: str,
        x: int,
        y: int,
        zone: ZoneType = ZoneType.NORMAL,
        color: Optional[str] = None,
        max_drones: int = 1,
    ) -> None:
        """Initialize a zone.

        Args:
            name: Unique identifier of the zone.
            x: X coordinate.
            y: Y coordinate.
            zone: Zone type (normal, blocked, restricted, priority).
            color: Optional display color.
            max_drones: Max drones allowed simultaneously in this zone.
        """
        self.name: str = name
        self.coords: tuple[int, int] = (x, y)
        self.zone: ZoneType = zone
        self.color: Optional[str] = color
        self.max_drones: int = 0 if zone == ZoneType.BLOCKED else max_drones
        self.connections: dict[str, Connection] = {}

    @property
    def move_cost(self) -> int:
        """Return the turn cost of moving into this zone."""
        return Node.MOVE_COST[self.zone]

    def neighbors(self) -> list["Node"]:
        """Return the list of nodes directly connected to this one."""
        return [conn.other(self) for conn in self.connections.values()]

    def __repr__(self) -> str:
        """Return a debug-friendly representation of the node."""
        return f"Node({self.name!r}, zone={self.zone.value})"


class Graph:
    """Owns the full set of nodes and connections parsed from a map file."""

    def __init__(self) -> None:
        """Initialize an empty graph."""
        self.nodes: dict[str, Node] = {}
        self.start: Optional[Node] = None
        self.end: Optional[Node] = None

    def add_node(self, node: Node, line_number: int) -> None:
        """Register a new node, raising if the name already exists.

        Args:
            node: The node to add.
            line_number: Source line, used for error reporting.

        Raises:
            ParsingError: If a node with the same name already exists.
        """
        if node.name in self.nodes:
            raise ParsingError(line_number, f"duplicate zone name '{node.name}'")
        self.nodes[node.name] = node

    def get_node(self, name: str, line_number: int) -> Node:
        """Fetch a previously defined node by name.

        Args:
            name: Zone name to look up.
            line_number: Source line, used for error reporting.

        Raises:
            ParsingError: If no zone with that name was defined yet.
        """
        if name not in self.nodes:
            raise ParsingError(line_number, f"unknown zone '{name}' referenced")
        return self.nodes[name]

    def add_connection(
        self, name_a: str, name_b: str, max_link_capacity: int, line_number: int
    ) -> None:
        """Create a bidirectional connection between two existing nodes.

        Args:
            name_a: Name of the first zone.
            name_b: Name of the second zone.
            max_link_capacity: Max drones allowed to traverse simultaneously.
            line_number: Source line, used for error reporting.

        Raises:
            ParsingError: If either zone is undefined or the connection
                (in either direction) was already declared.
        """
        node_a = self.get_node(name_a, line_number)
        node_b = self.get_node(name_b, line_number)

        if name_b in node_a.connections or name_a in node_b.connections:
            raise ParsingError(
                line_number, f"duplicate connection '{name_a}-{name_b}'"
            )

        connection = Connection(node_a, node_b, max_link_capacity)
        node_a.connections[name_b] = connection
        node_b.connections[name_a] = connection


def _parse_brackets(bracket_content: str, line_number: int) -> dict[str, str]:
    """Parse the ``key=value`` pairs inside a ``[...]`` metadata block.

    Args:
        bracket_content: The raw text found between the brackets.
        line_number: Source line, used for error reporting.

    Raises:
        ParsingError: If any token is not a valid ``key=value`` pair.
    """
    result: dict[str, str] = {}
    for token in bracket_content.split():
        if "=" not in token:
            raise ParsingError(line_number, f"invalid metadata token '{token}'")
        key, value = token.split("=", 1)
        result[key] = value
    return result


def _parse_positive_int(value: str, field: str, line_number: int) -> int:
    """Parse a string into a strictly positive integer.

    Args:
        value: The raw string to convert.
        field: Field name, used in the error message.
        line_number: Source line, used for error reporting.

    Raises:
        ParsingError: If the value is not a positive integer.
    """
    try:
        parsed = int(value)
    except ValueError:
        raise ParsingError(line_number, f"'{field}' must be an integer, got '{value}'")
    if parsed <= 0:
        raise ParsingError(line_number, f"'{field}' must be a positive integer")
    return parsed


def parse_zone_line(
    line: str, line_number: int, *, is_start: bool = False, is_end: bool = False, nb_drones: int = 1
) -> Node:
    """Parse a single zone-definition line (hub / start_hub / end_hub).

    Args:
        line: Raw line content (without the leading type prefix).
        line_number: Source line, used for error reporting.
        is_start: Whether this line defines the start zone.
        is_end: Whether this line defines the end zone.
        nb_drones: Total drone count, used as the effective capacity for
            start/end zones (which have no real capacity limit).

    Raises:
        ParsingError: On any structural or semantic issue in the line.
    """
    head, _, bracket_part = line.strip().partition("[")
    fields = head.split()

    if len(fields) != 3:
        raise ParsingError(
            line_number, "expected '<name> <x> <y>' for a zone definition"
        )

    name, x_str, y_str = fields
    try:
        x, y = int(x_str), int(y_str)
    except ValueError:
        raise ParsingError(line_number, "zone coordinates must be integers")

    metadata: dict[str, str] = {}
    if bracket_part:
        if not bracket_part.endswith("]"):
            raise ParsingError(line_number, "unclosed metadata block '['")
        metadata = _parse_brackets(bracket_part[:-1], line_number)

    zone = ZoneType.NORMAL
    if "zone" in metadata:
        try:
            zone = ZoneType(metadata["zone"])
        except ValueError:
            raise ParsingError(
                line_number, f"invalid zone type '{metadata['zone']}'"
            )

    color = metadata.get("color")

    if is_start or is_end:
        # max_drones is ignored (not an error) on start/end zones.
        max_drones = nb_drones
    elif "max_drones" in metadata:
        max_drones = _parse_positive_int(metadata["max_drones"], "max_drones", line_number)
    else:
        max_drones = 1

    return Node(name, x, y, zone=zone, color=color, max_drones=max_drones)


def parse_connection_line(line: str, line_number: int) -> tuple[str, str, int]:
    """Parse a single connection-definition line.

    Args:
        line: Raw line content (without the leading 'connection:' prefix).
        line_number: Source line, used for error reporting.

    Returns:
        A tuple of (zone_name_a, zone_name_b, max_link_capacity).

    Raises:
        ParsingError: On any structural or semantic issue in the line.
    """
    head, _, bracket_part = line.strip().partition("[")
    head = head.strip()

    if "-" not in head:
        raise ParsingError(line_number, "expected '<zone1>-<zone2>' for a connection")

    name_a, _, name_b = head.partition("-")
    name_a, name_b = name_a.strip(), name_b.strip()
    if not name_a or not name_b:
        raise ParsingError(line_number, "connection is missing a zone name")

    max_link_capacity = 1
    if bracket_part:
        if not bracket_part.endswith("]"):
            raise ParsingError(line_number, "unclosed metadata block '['")
        metadata = _parse_brackets(bracket_part[:-1], line_number)
        if "max_link_capacity" in metadata:
            max_link_capacity = _parse_positive_int(
                metadata["max_link_capacity"], "max_link_capacity", line_number
            )

    return name_a, name_b, max_link_capacity


def parse_map_file(path: str) -> tuple[Graph, int]:
    """Parse a full map file into a Graph and the declared drone count.

    Args:
        path: Filesystem path to the map file.

    Returns:
        A tuple of (graph, nb_drones).

    Raises:
        ParsingError: On any structural or semantic issue in the file.
    """
    graph = Graph()
    nb_drones: Optional[int] = None

    with open(path, "r", encoding="utf-8") as handle:
        raw_lines = handle.readlines()

    for line_number, raw_line in enumerate(raw_lines, start=1):
        line = raw_line.split("#", 1)[0].strip()
        if not line:
            continue

        if line.startswith("nb_drones:"):
            if nb_drones is not None:
                raise ParsingError(line_number, "duplicate 'nb_drones' declaration")
            nb_drones = _parse_positive_int(
                line[len("nb_drones:"):].strip(), "nb_drones", line_number
            )
            continue

        if nb_drones is None:
            raise ParsingError(line_number, "'nb_drones' must be declared first")

        if line.startswith("start_hub:"):
            if graph.start is not None:
                raise ParsingError(line_number, "duplicate 'start_hub' declaration")
            node = parse_zone_line(
                line[len("start_hub:"):], line_number, is_start=True, nb_drones=nb_drones
            )
            graph.add_node(node, line_number)
            graph.start = node

        elif line.startswith("end_hub:"):
            if graph.end is not None:
                raise ParsingError(line_number, "duplicate 'end_hub' declaration")
            node = parse_zone_line(
                line[len("end_hub:"):], line_number, is_end=True, nb_drones=nb_drones
            )
            graph.add_node(node, line_number)
            graph.end = node

        elif line.startswith("hub:"):
            node = parse_zone_line(line[len("hub:"):], line_number)
            graph.add_node(node, line_number)

        elif line.startswith("connection:"):
            name_a, name_b, capacity = parse_connection_line(
                line[len("connection:"):], line_number
            )
            graph.add_connection(name_a, name_b, capacity, line_number)

        else:
            raise ParsingError(line_number, f"unrecognized line '{line}'")

    if nb_drones is None:
        raise ParsingError(len(raw_lines), "missing 'nb_drones' declaration")
    if graph.start is None:
        raise ParsingError(len(raw_lines), "missing 'start_hub' declaration")
    if graph.end is None:
        raise ParsingError(len(raw_lines), "missing 'end_hub' declaration")

    return graph, nb_drones
