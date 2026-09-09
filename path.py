from map_creator import Node, ZoneType
import math

def faster_path(starting_node: Node):
    if starting_node.name != "start_hub":
        raise ReferenceError("start_hub not provided correctly")
    fail = False
    visited = set()
    unvisited = {node for node in starting_node.nodes.values()}
    unvisited.remove(starting_node)
    nodes_map = {node:[math.inf, None, False] for node in starting_node.nodes}
    nodes_map["start_hub"] = [0, None, False]
    chosen_node = starting_node
    while chosen_node.name != "goal":
        next_node = None
        visited.add(chosen_node)
        if chosen_node in unvisited:
            unvisited.remove(chosen_node)
        cost_up_to_here = nodes_map[chosen_node.name][0]    
        for contact in chosen_node.contacts:
            contact_node, max_through = chosen_node.contacts[contact]
            if max_through == 0 or contact_node in visited:
                continue
            if contact_node.cap == 0:
                if contact_node in unvisited:
                    unvisited.remove(contact_node)
                visited.add(contact_node)
                nodes_map[contact_node.name] = [-1, None, False]
                continue
            if contact_node.zone == ZoneType.PRIORITY:
                nodes_map[contact_node.name][2] = True
            if (contact_node.zone in (ZoneType.PRIORITY, ZoneType.NORMAL)) and cost_up_to_here + 1 < nodes_map[contact_node.name][0]:
                nodes_map[contact_node.name][0] = cost_up_to_here + 1
                nodes_map[contact_node.name][1] = chosen_node
            elif contact_node.zone == ZoneType.RESTRICTED and cost_up_to_here + 2 < nodes_map[contact_node.name][0]:
                nodes_map[contact_node.name][0] = cost_up_to_here + 2
                nodes_map[contact_node.name][1] = chosen_node
        for nodes in unvisited:
            if next_node is None:
                if nodes_map[nodes.name][0] != math.inf: 
                    next_node = nodes
                continue
            elif nodes_map[nodes.name][0] < nodes_map[next_node.name][0] or (
                (nodes_map[nodes.name][0] == nodes_map[next_node.name][0]) and nodes_map[nodes.name][2]):
             next_node = nodes

        if next_node is not None:
            chosen_node = next_node
        else:
            fail = True
            break
    if fail:
        return None
    path = ["goal"]
    prev_node = nodes_map["goal"][1]
    while prev_node.name != "start_hub":
        path.append(prev_node.name)
        if prev_node.zone == ZoneType.RESTRICTED:
            path.append("travelling to " + prev_node.name)
        prev_node = nodes_map[prev_node.name][1]
    path.reverse()
    return (len(path), path)
