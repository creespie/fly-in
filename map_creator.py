from enum import Enum

class ZoneType(Enum):
    NORMAL = "normal"
    BLOCKED = "blocked"
    RESTRCTED = "restricted"
    PRIORITY = "priority"


class Node:
    nodes = {}

    def __init__(self, name: str, x: int, y: int, zone:ZoneType = ZoneType.NORMAL, color: str | None =None, max_drones: int =1):
        self.name: str = name
        self.coords: tuple[int, int] = (x, y)
        self.zone: ZoneType = zone
        self.color: str | None = color
        if self.zone == ZoneType.BLOCKED:
            self.cap: int = 0
        else:
            self.cap: int = max_drones
        self.contacts = {}
        Node.nodes[self.name] = self

def add_contact(node1: Node, node2: Node, max: int = 1):
    if (node1.name in node2.contacts) or (node2.name in node1.contacts):
        return
    else:
        node1.contacts[node2.name] = (node2, max)
        node2.contacts[node1.name] = (node1, max)


def zone_parser(input_str: str):
    meta = input_str.lstrip().split("[")
    general_info = meta[0].split()

    kwargs = {}

    if len(meta) == 2:
        d = dict(item.split("=", 1) for item in meta[1][:-1].split())

        if "zone" in d:
            kwargs["zone"] = ZoneType(d["zone"])

        if "color" in d:
            kwargs["color"] = d["color"]

        if "max_drones" in d:
            kwargs["max_drones"] = int(d["max_drones"])

    return Node(
        general_info[1],
        int(general_info[2]),
        int(general_info[3]),
        **kwargs
    )

def start_end(input_str: str, drones: int, start: bool):
    meta = input_str.lstrip().split("[")
    general_info = meta[0].split()

    kwargs = {
        "zone": ZoneType.NORMAL,
        "max_drones": drones
    }

    if len(meta) == 2:
        datadict = dict(item.split("=", 1) for item in meta[1][:-1].split())

        if "color" in datadict:
            kwargs["color"] = datadict["color"]

    return Node(
        "hub" if start else "goal",
        int(general_info[2]),
        int(general_info[3]),
        **kwargs
    )