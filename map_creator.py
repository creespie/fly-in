"""Parsing of the Fly-in map format and the zone graph it describes."""
from __future__ import annotations

import sys
from enum import Enum


class ZoneType(Enum):
    """The four zone types a hub can have, per the subject."""

    NORMAL = "normal"
    BLOCKED = "blocked"
    RESTRICTED = "restricted"
    PRIORITY = "priority"


class Contact:
    """One endpoint of a connection, as seen from a specific `Node`.

    Attributes:
        node: The neighbouring zone this connection leads to.
        capacity: How many drones may still traverse this connection
            simultaneously (decremented as drones are scheduled onto it).
    """

    def __init__(self, node: Node, capacity: int) -> None:
        self.node = node
        self.capacity = capacity


class Node:
    """A single zone of the map, and its outgoing connections.

    Attributes:
        name: Unique identifier of the zone.
        coords: (x, y) integer coordinates, used only for display.
        zone: The `ZoneType` of this zone (movement-cost category).
        color: Optional display color, as given in the map file.
        cap: Remaining drone capacity of this zone (0 forever if blocked).
        contacts: Map from a neighbour's name to the `Contact` describing
            that connection.
    """

    nodes: dict[str, Node] = {}

    def __init__(
        self,
        name: str,
        x: int,
        y: int,
        zone: ZoneType = ZoneType.NORMAL,
        color: str = "white",
        max_drones: int = 1,
    ) -> None:
        self.name: str = name
        self.coords: tuple[int, int] = (x, y)
        self.zone: ZoneType = zone
        self.color: str | None = color
        self.cap: int
        if self.zone == ZoneType.BLOCKED:
            self.cap = 0
        else:
            self.cap = max_drones
        self.contacts: dict[str, Contact] = {}
        Node.nodes[self.name] = self

    def remove_space(self) -> None:
        """Consume one unit of this zone's drone capacity.

        Prints (rather than raising) if the capacity would go negative,
        which would indicate a scheduling bug upstream.
        """
        try:
            self.cap -= 1
            if self.cap < 0:
                raise ValueError(f"{self.name} went negative")
        except ValueError as e:
            print(e)

    def slim_connection(self, node: Node) -> None:
        """Consume one unit of capacity on the connection to `node`.

        Args:
            node: The neighbouring zone this connection leads to.
        """
        try:
            self.contacts[node.name].capacity -= 1
            node.contacts[self.name].capacity -= 1
            if (
                self.contacts[node.name].capacity < 0
                or node.contacts[self.name].capacity < 0
            ):
                raise ValueError(
                    f"Connection between {self.name} and {node.name} "
                    "went negative"
                )
        except ValueError as e:
            print(e)


def add_contact(node1: Node, node2: Node, max: int = 1) -> None:
    """Register a bidirectional connection between two zones.

    Args:
        node1: One endpoint of the connection.
        node2: The other endpoint of the connection.
        max: Maximum number of drones allowed on this connection at once.

    Raises:
        ValueError: If the connection already exists, or `max` isn't a
            positive integer.
    """
    if (node1.name in node2.contacts) or (node2.name in node1.contacts):
        raise ValueError("Duplicated connection")
    elif max <= 0:
        raise ValueError("Connection capacity can't be negative")
    else:
        node1.contacts[node2.name] = Contact(node2, max)
        node2.contacts[node1.name] = Contact(node1, max)


def zone_parser(input_str: str) -> Node:
    """Parse a `hub: <name> <x> <y> [metadata]` line and build its Node.

    Args:
        input_str: The full map-file line, prefix included.

    Returns:
        The newly created `Node`.

    Raises:
        ValueError: On any malformed field or metadata.
    """
    meta = input_str.lstrip().split("[")
    general_info = meta[0].split()

    zone = ZoneType.NORMAL
    color = "white"
    max_drones = 1

    if len(meta) == 2:
        if meta[1][-1] != "]":
            raise ValueError("Not Closed bracket")
        try:
            d = dict(item.split("=", 1) for item in meta[1][:-1].split())
        except Exception as exc:
            raise ValueError("Wrong metadata format") from exc
        for key in d.keys():
            if key not in ("zone", "color", "max_drones"):
                raise ValueError(f"Unexpected argument: {key}")
        if "zone" in d:
            zone = ZoneType(d["zone"])
        if "color" in d:
            color = d["color"]
        if "max_drones" in d:
            max_drones = int(d["max_drones"])
    elif len(meta) > 2:
        raise ValueError("More than one opening bracket")

    if general_info[1] in Node.nodes:
        raise ValueError("Duplicate node")
    if (len(general_info) != 4) or "-" in general_info[1]:
        raise ValueError("Spaces and dashes are not accepted")
    try:
        x = int(general_info[2])
        y = int(general_info[3])
    except ValueError as exc:
        raise ValueError("Coordinates must be ints") from exc

    return Node(
        general_info[1], x, y, zone=zone, color=color, max_drones=max_drones
    )


def start_end(input_str: str, drones: int, start: bool) -> Node:
    """Parse a `start_hub:`/`end_hub:` line and build its Node.

    The zone is always stored internally as `"start_hub"` or `"goal"`
    regardless of the name used in the file, so the rest of the pipeline
    can rely on those two fixed identifiers.

    Args:
        input_str: The full map-file line, prefix included.
        drones: Total number of drones (used as the zone's capacity,
            since start/end have no real capacity limit).
        start: True to build the start zone, False for the end zone.

    Returns:
        The newly created `Node`.

    Raises:
        ValueError: On any malformed field or metadata.
    """
    meta = input_str.lstrip().split("[")
    general_info = meta[0].split()

    color = "white"

    if len(meta) == 2:
        if meta[1][-1] != "]":
            raise ValueError("Not Closed bracket")
        try:
            datadict = dict(
                item.split("=", 1) for item in meta[1][:-1].split()
            )
        except Exception as exc:
            raise ValueError("Wrong metadata format") from exc
        for key in datadict.keys():
            if key not in ("color", "max_drones"):
                raise ValueError(f"Unexpected argument: {key}")
        if "color" in datadict:
            color = datadict["color"]
        # max_drones metadata on start/end is intentionally ignored:
        # both zones have unlimited capacity, per the subject.

    if (len(general_info) != 4) or "-" in general_info[1]:
        raise ValueError("Spaces and dashes are not accepted")
    try:
        x = int(general_info[2])
        y = int(general_info[3])
    except ValueError as exc:
        raise ValueError("Coordinates must be ints") from exc

    return Node(
        "start_hub" if start else "goal",
        x,
        y,
        zone=ZoneType.NORMAL,
        color=color,
        max_drones=drones,
    )


def connection_parser(input_str: str, node_names: dict[str, str]) -> None:
    """Parse a `connection: <a>-<b> [metadata]` line and register it.

    Args:
        input_str: The full map-file line, prefix included.
        node_names: Map from the zone name as written in the file to its
            internal registry key (only start/end differ; every other
            zone maps to itself).

    Raises:
        ValueError: On any malformed field or metadata.
    """
    meta = input_str.lstrip().split("[")
    general_info = meta[0].split()
    name1, name2 = general_info[1].split("-")
    name1 = node_names.get(name1, name1)
    name2 = node_names.get(name2, name2)

    max_link_capacity = 1
    if len(meta) == 2:
        d = dict(item.split("=", 1) for item in meta[1][:-1].split())
        for key in d.keys():
            if key not in ("max_link_capacity",):
                raise ValueError(f"Unexpected argument: {key}")
        if "max_link_capacity" in d:
            try:
                max_link_capacity = int(d["max_link_capacity"])
            except ValueError as exc:
                raise ValueError(
                    "Link capacity must be an integer"
                ) from exc

    add_contact(Node.nodes[name1], Node.nodes[name2], max_link_capacity)


def load_map(filepath: str) -> tuple[Node, int]:
    """Parse an entire map file and build the zone graph.

    Args:
        filepath: Path to the map file to load.

    Returns:
        A tuple `(start_node, nb_drones)`.

    Raises:
        SystemExit: On any parsing error, with a message naming the
            offending line and the cause (via `sys.exit`).
        ValueError: If the file has no `nb_drones` or no `start_hub`.
    """
    node_names: dict[str, str] = {}
    nb_drones: int | None = None
    start_node: Node | None = None

    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            try:
                stripped = line.strip()
                if not stripped or stripped.startswith("#"):
                    continue
                if stripped.startswith("nb_drones:"):
                    nb_drones = int(stripped.split(":", 1)[1].strip())
                    if nb_drones <= 0:
                        raise ValueError(
                            "Number of drones can't be 0 or negative"
                        )
                elif not nb_drones:
                    raise ValueError("Files doesnt begin with nb_drones")
                elif stripped.startswith("start_hub:"):
                    file_name = stripped.split("[")[0].split()[1]
                    if "start_hub" in node_names.values():
                        raise ValueError(
                            "Start_hub was defined more than once"
                        )
                    node_names[file_name] = "start_hub"
                    start_node = start_end(stripped, nb_drones, start=True)
                elif stripped.startswith("end_hub:"):
                    file_name = stripped.split("[")[0].split()[1]
                    if "goal" in node_names.values():
                        raise ValueError("Goal was defined more than once")
                    node_names[file_name] = "goal"
                    start_end(stripped, nb_drones, start=False)
                elif stripped.startswith("hub:"):
                    zone_parser(stripped)
                elif stripped.startswith("connection:"):
                    connection_parser(stripped, node_names)
                else:
                    raise ValueError("Line has the wrong format")
            except Exception as e:
                sys.exit(f"{e} on line: {line}")

    if nb_drones is None or start_node is None:
        raise ValueError("Missing nb_drones or start_hub in map file")
    return start_node, nb_drones
