import sys
from map_creator import load_map
from drones import drone_creator, Drone, filler, print_all

def main():
    start_node, nb_drones = load_map(sys.argv[1])
    drone_creator(nb_drones)
    filler(start_node)
    print_all(Drone.drones)

if __name__ == "__main__":
    main()