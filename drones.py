"""Multi-drone scheduling: assigning and replaying per-drone paths."""
from __future__ import annotations

import math

from map_creator import Node
from path import faster_path


class Drone:
    """A single drone and the sequence of steps it has been assigned.

    Attributes:
        name: Drone identifier, e.g. ``"D1"``.
        path: Ordered list of steps (`zone` name, `"travelling to X"`
            placeholder, or `"wait"`) this drone will replay turn by
            turn once assigned by `filler`.
        arrived: Set to True once this drone reaches `goal` during replay
            (see `print_all`/`generate_lines`); unrelated to `assigned`.
        assigned: Set to True once this drone has received a path during
            planning (see `confirm_path`/`assign_all`).
    """

    drones: list[Drone] = []

    def __init__(self, name: str) -> None:
        self.name = name
        self.path: list[str] = []
        self.arrived = False
        self.assigned = False
        Drone.drones.append(self)


def drone_creator(number: int) -> None:
    """Create `number` drones, named `D1`..`D<number>`.

    Args:
        number: How many drones to create.
    """
    for i in range(1, number + 1):
        Drone(f"D{i}")


def remove_all_capacity(path: list[str]) -> None:
    """Consume the zone/connection capacity used by a confirmed path.

    Args:
        path: The step list (as returned by `faster_path`) that is being
            assigned to a drone.
    """
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


def filler(starting_node: Node) -> None:
    """Assign a path to every created drone.

    Repeatedly finds the cheapest still-available path and assigns it to
    the next drone, consuming capacity as it goes; once the cheapest
    remaining path costs more turns, already-found paths are replayed
    (with a wait at `start_hub`) for more drones before moving on to the
    new, longer path. Once no new path can be found at all, remaining
    drones keep reusing the paths found so far.

    Args:
        starting_node: The `start_hub` node (also re-fetched internally
            from the registry, so any node may technically be passed).
    """
    damount = len(Drone.drones)
    paths: list[tuple[int, list[str]]] = []
    index = 0
    # nb_drones is validated to be >= 1 by the parser, so Drone.drones
    # is guaranteed non-empty here.
    current_drone = Drone.drones[index]
    starting_node = Node.nodes["start_hub"]
    path: tuple[int, list[str]] | None = None
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
        if new_path:
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
    return None


def confirm_path(
    path: tuple[int, list[str]],
    current_drone: Drone,
    damount: int,
    index: int,
    paths: list[tuple[int, list[str]]],
) -> tuple[int, int]:
    """Assign a freshly found path to `current_drone` and consume it.

    Args:
        path: The `(cost, steps)` path to assign.
        current_drone: The drone to assign it to.
        damount: Number of drones still left to assign (before this one).
        index: Index of `current_drone` within `Drone.drones`.
        paths: Running list of all distinct paths found so far, to be
            reused later by `assign_all`.

    Returns:
        The updated `(damount, index)` after this assignment.
    """
    paths.append(path)
    remove_all_capacity(path[1])
    current_drone.path.extend(path[1])
    current_drone.assigned = True
    damount -= 1
    index += 1
    return damount, index


def assign_all(
    paths: list[tuple[int, list[str]]],
    damount: int,
    index: int,
    wait_number: int,
) -> tuple[int, int]:
    """Reuse every path in `paths` for one more drone each, with a wait.

    Each drone waits at `start_hub` for exactly the number of turns
    needed so it trails whichever drone already used that same path,
    without ever sharing a zone/connection at the same turn.

    Args:
        paths: All distinct paths found so far.
        damount: Number of drones still left to assign.
        index: Index of the next unassigned drone within `Drone.drones`.
        wait_number: Which "round" of reuse this is (1 for the first
            extra lap over `paths`, 2 for the second, and so on).

    Returns:
        The updated `(damount, index)` after these assignments.
    """
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


def print_all(drones: list[Drone]) -> None:
    """Print the turn-by-turn simulation output for every drone.

    Same replay logic as `generate_lines`, but prints directly instead
    of returning the lines, and mutates `drone.arrived` as a side effect.

    Args:
        drones: The drones to replay, each already carrying an assigned
            `path`.
    """
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
    """Return the simulation's turn-by-turn output as a list of lines.

    Unlike `print_all`, this does not mutate `drone.arrived`, so it can
    be called safely and the result handed to either the terminal
    output or a graphical visualizer.

    Args:
        drones: The drones to replay, each already carrying an assigned
            `path`.

    Returns:
        One string per simulation turn, in the subject's required
        `D<id>-<zone>`/`D<id>-<connection>` format.
    """
    lines: list[str] = []
    arrived = {d.name: False for d in drones}
    turn = 0
    max_turns = 100_000  # safety net against infinite loops

    while True:
        finished = True
        parts: list[str] = []

        for drone in drones:
            if arrived[drone.name]:
                continue
            finished = False

            if turn >= len(drone.path):
                # Path exhausted without reaching goal: anomaly.
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
