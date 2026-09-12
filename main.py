import argparse
from map_creator import load_map, Node
from drones import drone_creator, Drone, filler, generate_lines


def main() -> None:
    parser = argparse.ArgumentParser(description="Fly-in drone simulation")
    parser.add_argument("map_file", help="Path to the map file")
    parser.add_argument(
        "--visual",
        choices=["terminal", "pygame", "both", "none"],
        default="both",
        help="Visualization mode (default: both)",
    )
    parser.add_argument(
        "--delay",
        type=int,
        default=500,
        help="Milliseconds between turns in pygame (default: 500)",
    )
    args = parser.parse_args()

    start_node, nb_drones = load_map(args.map_file)
    drone_creator(nb_drones)
    filler(start_node)

    lines = generate_lines(Drone.drones)

    if args.visual in ("terminal", "both"):
        for line in lines:
            print(line)

    if args.visual in ("pygame", "both"):
        from visualizer import parse_output_lines, PygameVisualizer

        turns = parse_output_lines(
            lines, start_hub="start_hub", nb_drones=nb_drones)
        PygameVisualizer().run_replay(
            turns, Node.nodes, turn_delay_ms=args.delay)


if __name__ == "__main__":
    main()
