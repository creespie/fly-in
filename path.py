"""From-scratch Dijkstra-style pathfinding for the zone graph."""
from __future__ import annotations

import math
from dataclasses import dataclass

from map_creator import Node, ZoneType


@dataclass
class NodeState:
    """Search state tracked for one node during `faster_path`.

    Attributes:
        cost: Best known turn-cost from `start_hub` to this node so far
            (``math.inf`` until first reached).
        previous: The node right before this one on the current
            best-known path, or ``None`` if not reached yet.
        priority: Whether this node is a `priority` zone, used as a
            tie-breaker when several candidates share the same cost.
    """

    cost: float
    previous: Node | None
    priority: bool


def faster_path(starting_node: Node) -> tuple[int, list[str]] | None:
    """Find the cheapest path from `start_hub` to `goal`.

    `normal`/`priority` zones cost 1 turn, `restricted` zones cost 2 and
    are represented in the returned path as two consecutive entries (a
    `"travelling to <zone>"` placeholder followed by the zone itself, so
    a drone can be forced to complete the crossing in one go without
    stopping mid-transit). `blocked` zones (capacity 0) are never
    expanded, and `priority` zones are preferred over `normal` ones when
    two candidates have the same cost.

    Args:
        starting_node: The `start_hub` node to search from.

    Returns:
        A tuple `(cost, path)`, where `path` is the ordered list of zone
        names / restricted-connection placeholders needed to reach
        `goal` (excluding `start_hub` itself), or ``None`` if `goal` is
        currently unreachable given the remaining capacities.

    Raises:
        ReferenceError: If `starting_node` is not the `start_hub` node.
    """
    if starting_node.name != "start_hub":
        raise ReferenceError("start_hub not provided correctly")

    fail = False
    visited: set[Node] = set()
    unvisited: set[Node] = set(starting_node.nodes.values())
    unvisited.remove(starting_node)

    nodes_map: dict[str, NodeState] = {
        name: NodeState(math.inf, None, False)
        for name in starting_node.nodes
    }
    nodes_map["start_hub"] = NodeState(0, None, False)

    chosen_node = starting_node
    while chosen_node.name != "goal":
        next_node: Node | None = None
        visited.add(chosen_node)
        if chosen_node in unvisited:
            unvisited.remove(chosen_node)
        cost_up_to_here = nodes_map[chosen_node.name].cost

        for contact in chosen_node.contacts.values():
            contact_node, max_through = contact.node, contact.capacity
            if max_through == 0 or contact_node in visited:
                continue
            if contact_node.cap == 0:
                if contact_node in unvisited:
                    unvisited.remove(contact_node)
                visited.add(contact_node)
                nodes_map[contact_node.name] = NodeState(-1, None, False)
                continue
            if contact_node.zone == ZoneType.PRIORITY:
                nodes_map[contact_node.name].priority = True
            if (
                contact_node.zone in (ZoneType.PRIORITY, ZoneType.NORMAL)
                and cost_up_to_here + 1 < nodes_map[contact_node.name].cost
            ):
                nodes_map[contact_node.name].cost = cost_up_to_here + 1
                nodes_map[contact_node.name].previous = chosen_node
            elif (
                contact_node.zone == ZoneType.RESTRICTED
                and cost_up_to_here + 2 < nodes_map[contact_node.name].cost
            ):
                nodes_map[contact_node.name].cost = cost_up_to_here + 2
                nodes_map[contact_node.name].previous = chosen_node

        for node in unvisited:
            state = nodes_map[node.name]
            if next_node is None:
                if state.cost != math.inf:
                    next_node = node
                continue
            next_state = nodes_map[next_node.name]
            if state.cost < next_state.cost or (
                state.cost == next_state.cost and state.priority
            ):
                next_node = node

        if next_node is not None:
            chosen_node = next_node
        else:
            fail = True
            break

    if fail:
        return None

    path = ["goal"]
    prev_node = nodes_map["goal"].previous
    while prev_node is not None and prev_node.name != "start_hub":
        path.append(prev_node.name)
        if prev_node.zone == ZoneType.RESTRICTED:
            path.append("travelling to " + prev_node.name)
        prev_node = nodes_map[prev_node.name].previous
    path.reverse()
    return (len(path), path)
