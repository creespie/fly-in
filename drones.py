from map_creator import Node
from path import faster_path
import math

class Drone:
    drones = []

    def __init__(self, name: str):
        self.name = name
        self.path = []
        self.arrived = False
        Drone.drones.append(self)

def drone_creator(number: int):
    for i in range(1, number + 1):
        Drone(f"D{i}")

def remove_all_capacity(path: list[str]):
    if "travelling to " in path[0]:
        Node.nodes["start_hub"].slim_connection(Node.nodes[path[1]])
    else:
        Node.nodes["start_hub"].slim_connection(Node.nodes[path[0]])
    for i in range(1, len(path)):
        if "travelling to " in path[i]:
            continue
        Node.nodes[path[i]].remove_space()
        if "travelling to " in path[i + 1]:
            Node.nodes[path[i]].slim_connection(Node.nodes[path[i + 2]])
        else:
            Node.nodes[path[i]].slim_connection(Node.nodes[path[i + 1]])
    if "travelling to " not in path[len(path) - 1]:
        Node.nodes[path[len(path) - 1]].remove_space()
        Node.nodes[path[len(path) - 1]].slim_connection(Node.nodes["goal"])

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
            damount, index = confirm_path(path, current_drone, damount, index, paths)
            if index < len(Drone.drones):
                current_drone = Drone.drones[index]
    if path is None:
        return None
    while damount > 0:
        new_path = faster_path(starting_node)
        while new_path is not None and new_path[0] == path[0]:
            path = new_path
            damount, index = confirm_path(path, current_drone, damount, index, paths)
            if index < len(Drone.drones):
                current_drone = Drone.drones[index]
            new_path = faster_path(starting_node)
        if new_path:  #if there is a next biger path go over all stored paths to reassign for turns between new path and old path
            for i in range(1, new_path[0] - path[0] + 1):
                damount, index = assign_all(paths, damount, index, i)
        if new_path is not None and damount > 0:
            path = new_path
            damount, index = confirm_path(path, current_drone, damount, index, paths)
            if index < len(Drone.drones):
                current_drone = Drone.drones[index]
        else:
            break
    while damount > 0:
        for i in range(1, math.ceil(damount / len(paths)) + 1):
            damount, index = assign_all(paths, damount, index, i)

def confirm_path(path: tuple[int, list[str]], current_drone: Drone, damount: int, index: int, paths: list[list[tuple[int, list[str]]]]):
    paths.append(path)
    remove_all_capacity(path[1])
    current_drone.path.extend(path[1])
    current_drone.arrived = True
    damount -= 1
    index += 1
    return damount, index
            
def assign_all(paths: list[tuple[int, list[str]]], damount, index, wait_number):
    ref_number = paths[len(paths) - 1][0]
    for path in paths:
        if damount == 0:
            return 0, 0
        else:
            if index < len(Drone.drones):
                current_drone = Drone.drones[index]
            index += 1
            for _ in range(0, ref_number - path[0] + wait_number): # add waiting turns
                current_drone.path.append("wait")
            current_drone.path.extend(path[1])
            current_drone.arrived = True
            damount -= 1
    return damount, index