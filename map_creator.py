from enum import Enum
import sys

class ZoneType(Enum):
    NORMAL = "normal"
    BLOCKED = "blocked"
    RESTRICTED = "restricted"
    PRIORITY = "priority"


class Node:
    nodes = {}

    def __init__(self, name: str, x: int, y: int, zone:ZoneType = ZoneType.NORMAL, color: str ="white", max_drones: int =1):
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
        raise ValueError("Duplicated connection")
    elif max <= 0:
        raise ValueError("Connection capacity can't be negative")
    else:
        node1.contacts[node2.name] = [node2, max]
        node2.contacts[node1.name] = [node1, max]


def zone_parser(input_str: str):
    meta = input_str.lstrip().split("[")
    general_info = meta[0].split()

    kwargs = {}

    if len(meta) == 2:
        if meta[1][-1] != "]":
            raise ValueError("Not Closed bracket")
        try:
            d = dict(item.split("=", 1) for item in meta[1][:-1].split())
        except:
            raise ValueError("Wrong metadata format")
        for key in d.keys():
            if key not in ("zone", "color", "max_drones"):
                raise ValueError(f"Unexpected argument: {key}")
        if "zone" in d:
            kwargs["zone"] = ZoneType(d["zone"])

        if "color" in d:
            kwargs["color"] = d["color"]

        if "max_drones" in d:
            kwargs["max_drones"] = int(d["max_drones"])
    elif len(meta) > 2:
        raise ValueError("More than one opening bracket")
    if general_info[1] in Node.nodes.keys():
        raise ValueError("Duplicate node")
    if (len(general_info) != 4) or "-" in general_info[1]:
        raise ValueError("Spaces and dashes are not accepted")
    try:
        x = int(general_info[2])
        y = int(general_info[3])
    except ValueError:
        raise ValueError("Coordinates must be ints")
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
        if meta[1][-1] != "]":
            raise ValueError("Not Closed bracket")
        try:
            datadict = dict(item.split("=", 1) for item in meta[1][:-1].split())
        except:
            raise ValueError("Wrong metadata format")
        for key in datadict.keys():
            if key not in ("color", "max_drones"):
                raise ValueError(f"Unexpected argument: {key}")
        if "color" in datadict:
            kwargs["color"] = datadict["color"]

    if (len(general_info) != 4) or "-" in general_info[1]:
        raise ValueError("Spaces and dashes are not accepted")
    try:
        x = int(general_info[2])
        y = int(general_info[3])
    except ValueError:
        raise ValueError("Coordinates must be ints")
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
        for key in d.keys():
            if key not in ("max_link_capacity"):
                raise ValueError(f"Unexpected argument: {key}")
        if "max_link_capacity" in d:
            try:
                kwargs["max"] = int(d["max_link_capacity"])
            except ValueError:
                raise ValueError("Link capacity must be an integer")

    add_contact(Node.nodes[name1], Node.nodes[name2], **kwargs)


def load_map(filepath: str) -> tuple[Node, int]:
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
                        raise ValueError("Number of drones can't be 0 or negative")
                elif not nb_drones:
                    raise ValueError("Files doesnt begin with nb_drones")
                elif stripped.startswith("start_hub:"):
                    file_name = stripped.split("[")[0].split()[1]
                    if "start_hub" in node_names.values():
                        raise ValueError("Start_hub was defined more than once")
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
