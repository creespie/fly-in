from enum import Enum

class ZoneType(Enum):
    NORMAL = "normal"
    BLOCKED = "blocked"
    RESTRICTED = "restricted"
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

    def remove_space(self):
        try:
            self.cap -= 1
            if self.cap < 0:
                raise ValueError(f"{self.name} went negative")
        except ValueError as e:
            print(e)

    def slim_connection(self, node):
        try:
            self.contacts[node.name][1] -= 1
            node.contacts[self.name][1] -= 1
            if self.contacts[node.name][1] < 0 or node.contacts[self.name][1] < 0:
                raise ValueError(f"Connection between {self.name} and {node.name} went negative")
        except ValueError as e:
            print(e)
        

def add_contact(node1: Node, node2: Node, max: int = 1):
    if (node1.name in node2.contacts) or (node2.name in node1.contacts):
        return
    else:
        node1.contacts[node2.name] = [node2, max]
        node2.contacts[node1.name] = [node1, max]


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
        "start_hub" if start else "goal",
        int(general_info[2]),
        int(general_info[3]),
        **kwargs
    )

def connection_parser(input_str: str, node_names: dict[str, str]) -> None:
    meta = input_str.lstrip().split("[")
    general_info = meta[0].split()
    name1, name2 = general_info[1].split("-")
    name1 = node_names.get(name1, name1)
    name2 = node_names.get(name2, name2)

    kwargs = {}
    if len(meta) == 2:
        d = dict(item.split("=", 1) for item in meta[1][:-1].split())
        if "max_link_capacity" in d:
            kwargs["max"] = int(d["max_link_capacity"])

    add_contact(Node.nodes[name1], Node.nodes[name2], **kwargs)


def load_map(filepath: str) -> tuple[Node, int]:
    node_names: dict[str, str] = {}
    nb_drones: int | None = None
    start_node: Node | None = None

    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            if stripped.startswith("nb_drones:"):
                nb_drones = int(stripped.split(":", 1)[1].strip())
            elif stripped.startswith("start_hub:"):
                file_name = stripped.split("[")[0].split()[1]
                node_names[file_name] = "start_hub"
                start_node = start_end(stripped, nb_drones, start=True)
            elif stripped.startswith("end_hub:"):
                file_name = stripped.split("[")[0].split()[1]
                node_names[file_name] = "goal"
                start_end(stripped, nb_drones, start=False)
            elif stripped.startswith("hub:"):
                zone_parser(stripped)
            elif stripped.startswith("connection:"):
                connection_parser(stripped, node_names)

    if nb_drones is None or start_node is None:
        raise ValueError("Missing nb_drones or start_hub in map file")
    return start_node, nb_drones