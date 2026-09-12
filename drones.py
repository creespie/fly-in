from map_creator import Node
from path import faster_path
import math


class Drone:
    drones = []

    def __init__(self, name: str):
        self.name = name
        self.path = []
        self.arrived = False
        self.assigned = False
        Drone.drones.append(self)


def drone_creator(number: int):
    for i in range(1, number + 1):
        Drone(f"D{i}")


def remove_all_capacity(path: list[str]):
    if "travelling to " in path[0]:
        Node.nodes["start_hub"].slim_connection(Node.nodes[path[1]])
    else:
        Node.nodes["start_hub"].slim_connection(Node.nodes[path[0]])
        Node.nodes[path[0]].remove_space()
        if len(path) > 2:
            if "travelling to " in path[1]:
                Node.nodes[path[0]].slim_connection(Node.nodes[path[2]])
            else:
                Node.nodes[path[0]].slim_connection(Node.nodes[path[1]])
    for i in range(1, len(path)):
        if "travelling to " in path[i]:
            continue
        Node.nodes[path[i]].remove_space()
        if i < len(path) - 1:
            if "travelling to " in path[i + 1]:
                Node.nodes[path[i]].slim_connection(Node.nodes[path[i + 2]])
            else:
                Node.nodes[path[i]].slim_connection(Node.nodes[path[i + 1]])


def filler(starting_node: Node):
    damount = len(Drone.drones)
    paths = []
    index = 0
    if index < len(Drone.drones):
        current_drone = Drone.drones[index]
    starting_node = Node.nodes["start_hub"]
    path = None
    if path is None:
        path = faster_path(starting_node)
        if path is not None:
            damount, index = confirm_path(
                path, current_drone, damount, index, paths)
            if index < len(Drone.drones):
                current_drone = Drone.drones[index]
    if path is None:
        return None
    while damount > 0:
        new_path = faster_path(starting_node)
        while new_path is not None and new_path[0] == path[0]:
            path = new_path
            damount, index = confirm_path(
                path, current_drone, damount, index, paths)
            if index < len(Drone.drones):
                current_drone = Drone.drones[index]
            new_path = faster_path(starting_node)
        if (
            new_path
        ):
            for i in range(1, new_path[0] - path[0] + 1):
                damount, index = assign_all(paths, damount, index, i)
            if index < len(Drone.drones):
                current_drone = Drone.drones[index]
        if new_path is not None and damount > 0:
            path = new_path
            damount, index = confirm_path(
                path, current_drone, damount, index, paths)
            if index < len(Drone.drones):
                current_drone = Drone.drones[index]
        else:
            break
    while damount > 0:
        for i in range(1, math.ceil(damount / len(paths)) + 1):
            damount, index = assign_all(paths, damount, index, i)


def confirm_path(
    path: tuple[int, list[str]],
    current_drone: Drone,
    damount: int,
    index: int,
    paths: list[tuple[int, list[str]]],
):
    paths.append(path)
    remove_all_capacity(path[1])
    current_drone.path.extend(path[1])
    current_drone.assigned = True
    damount -= 1
    index += 1
    return damount, index


def assign_all(
    paths: list[
        tuple[int, list[str]]], damount: int, index: int, wait_number: int
):
    ref_number = paths[len(paths) - 1][0]
    for path in paths:
        if damount == 0:
            return 0, 0
        else:
            if index < len(Drone.drones):
                current_drone = Drone.drones[index]
            index += 1
            for _ in range(0, ref_number - path[0] + wait_number):
                current_drone.path.append("wait")
            current_drone.path.extend(path[1])
            current_drone.assigned = True
            damount -= 1
    return damount, index


def print_all(drones: list[Drone]):
    finished = False
    turn = 0
    while not finished:
        finished = True
        for drone in drones:
            if drone.arrived:
                continue
            else:
                finished = False
            if drone.path[turn] == "goal":
                print(f"{drone.name}-goal", end=" ")
                drone.arrived = True
            else:
                if drone.path[turn] == "wait":
                    continue
                elif "travelling to " in drone.path[turn]:
                    if turn == 0 or drone.path[turn - 1] == "wait":
                        print(f"{drone.name}-start_hub-"
                              f"{drone.path[turn + 1]}", end=" ")
                    else:
                        print(
                            f"{drone.name}-{drone.path[turn - 1]}-"
                            f"{drone.path[turn + 1]}",
                            end=" ",
                        )
                else:
                    print(f"{drone.name}-{drone.path[turn]}", end=" ")
        turn += 1
        print()


def generate_lines(drones: list[Drone]) -> list[str]:
    """Ritorna le righe di output della simulazione come lista.

    Non modifica lo stato dei droni (a differenza di ``print_all``),
    così puoi chiamare questa funzione e poi decidere se stampare
    a terminale o passare a un visualizzatore grafico.
    """
    lines: list[str] = []
    arrived = {d.name: False for d in drones}
    turn = 0
    max_turns = 100_000  # salvagente contro loop infiniti

    while True:
        finished = True
        parts: list[str] = []

        for drone in drones:
            if arrived[drone.name]:
                continue
            finished = False

            if turn >= len(drone.path):
                # Path esaurito senza aver raggiunto il goal: anomalia
                continue

            step = drone.path[turn]

            if step == "goal":
                parts.append(f"{drone.name}-goal")
                arrived[drone.name] = True
            elif step == "wait":
                continue
            elif "travelling to " in step:
                if turn == 0 or drone.path[turn - 1] == "wait":
                    parts.append(
                        f"{drone.name}-start_hub-{drone.path[turn + 1]}")
                else:
                    parts.append(
                        f"{drone.name}-{drone.path[turn - 1]}-"
                        f"{drone.path[turn + 1]}"
                    )
            else:
                parts.append(f"{drone.name}-{step}")

        lines.append(" ".join(parts))
        turn += 1
        if finished or turn > max_turns:
            break

    return lines
