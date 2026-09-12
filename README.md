*This project has been created as part of the 42 curriculum by lurossi.*

# Fly-in

## Description

Fly-in is a multi-drone routing simulator. Given a map of connected zones
(a graph with `normal`, `priority`, `restricted` and `blocked` zones, and
capacity limits on both zones and connections), the program computes how to
route a fleet of drones from a unique `start_hub` to a unique `end_hub` in
the fewest possible simulation turns, while respecting every movement and
occupancy constraint described in the subject.

The project is split into four responsibilities:

- **Parsing** (`map_creator.py`): reads the custom map format, builds the
  zone graph as a network of `Node` objects, and validates the file
  line by line.
- **Pathfinding** (`path.py`): a from-scratch Dijkstra-style search
  (no graph libraries used) that finds the cheapest path from
  `start_hub` to `end_hub`, taking zone movement costs and priority
  preference into account.
- **Scheduling** (`drones.py`): assigns a path to every drone, consuming
  zone/connection capacity as paths are confirmed, and reusing already
  found paths (with a waiting delay at `start_hub`) once no new distinct
  path can be found at the current turn count.
- **Output** (`drones.py` / `visualizer.py`): turns the per-drone plans
  into the turn-by-turn textual output required by the subject, and,
  optionally, into an animated graphical replay.

## Instructions

### Requirements

- Python 3.10+
- `pygame` (only needed for the graphical visualizer; the terminal output
  works without it)

### Install

```bash
make install
```

which just installs the dependencies listed in `requirements.txt`.

### Run

```bash
make run MAP=maps/easy/01_linear_path.txt
```

`MAP` defaults to `maps/easy/01_linear_path.txt` if you omit it, so
`make run` alone also works. Under the hood this calls:

```bash
python3 main.py <map_file> [--visual terminal|pygame|both|none] [--delay MS]
```

- `--visual terminal`: prints the turn-by-turn simulation to stdout only.
- `--visual pygame`: opens the animated graphical replay only.
- `--visual both` (default): does both.
- `--visual none`: only runs the simulation (useful for benchmarking, or
  when you just want the exit code / errors).
- `--delay`: milliseconds between turns in the pygame replay
  (default `500`).

### Debug

```bash
make debug MAP=maps/easy/01_linear_path.txt
```

runs `main.py` under Python's built-in debugger (`pdb`).

### Lint / type-check

```bash
make lint          # flake8 + mypy (subject's mandatory flags)
make lint-strict    # flake8 + mypy --strict
```

### Clean

```bash
make clean
```

removes `__pycache__` and `.mypy_cache` directories.

## Resources

- [Dijkstra's algorithm — Wikipedia](https://en.wikipedia.org/wiki/Dijkstra%27s_algorithm),
  used as the base for the custom pathfinding in `path.py` (no graph
  library was used, per the subject's constraints).
- [PEP 257 — Docstring conventions](https://peps.python.org/pep-0257/)
- [mypy documentation](https://mypy.readthedocs.io/)
- [flake8 documentation](https://flake8.pycqa.org/)
- [Pygame documentation](https://www.pygame.org/docs/), used for the
  graphical visualizer.

### AI usage

AI (Claude) was used throughout the project as a **debugging and design
review partner**, not as a code generator. In practice:

- Reviewing hand-written code to find bugs (e.g. iterating over dict keys
  instead of values, mutable-default/class-attribute mistakes, off-by-one
  errors in path reconstruction, Python scoping issues where a function
  couldn't "push" an updated variable back to its caller).
- Tracing algorithm execution by hand, step by step, on concrete example
  paths to verify (or disprove) the correctness of the capacity-consumption
  and turn-scheduling logic before running it on real maps.
- Discussing and stress-testing the multi-drone scheduling strategy
  (wave-based path reuse with waiting only at `start_hub`) against the
  subject's deadlock/conflict-avoidance requirements, including arguing
  through *why* "wait only at the origin" structurally prevents circular
  deadlocks.
- Explaining the algorithmic complexity of the pathfinding implementation
  and where it could be improved (e.g. replacing the linear scan for the
  minimum-cost node with a heap).
- The parser (`connection_parser` / `load_map` orchestration) was drafted
  with AI assistance after diagnosing, together, why connections were
  never being registered (a start/end zone naming mismatch between the
  file and the internal graph representation).

All AI-assisted code was read, tested against the provided maps, and
understood before being kept — several early drafts were rejected or
rewritten after manual review and debugging.

## Algorithm choices and implementation strategy

### Pathfinding (`path.py`)

`faster_path` is a Dijkstra implementation written from scratch (no
`heapq`, no graph library): it maintains a `visited`/`unvisited` set of
`Node` objects and, at each step, scans the unvisited set linearly to pick
the lowest-cost node, preferring `priority` zones on cost ties (as
required by the subject). `restricted` zones are represented in the
reconstructed path as two consecutive entries — a `"travelling to <zone>"`
placeholder followed by the zone itself — so that the rest of the pipeline
can treat every path step as a single simulation turn uniformly, while
still being able to detect and forbid stopping mid-transit into a
restricted zone.

**Complexity**: the linear scan for the minimum-cost unvisited node makes
a single `faster_path` call `O(V² + E)` in the worst case, dominated by
the `O(V²)` node-selection loop rather than the edge relaxation. A
priority-queue based implementation would bring this down to
`O((V + E) log V)`; this was considered but not implemented, since all
provided benchmark maps (including hard/challenger ones) were solved
comfortably within the required turn targets with the simpler version.

### Scheduling (`drones.py`)

Drones are **not** scheduled turn-by-turn in real time. Instead, the
scheduler repeatedly calls `faster_path` on the *same* graph, whose
capacity is progressively consumed as paths are confirmed
(`confirm_path` → `remove_all_capacity`):

1. Find the cheapest available path and assign it to the next drone,
   consuming the zone/connection capacity it uses.
2. Repeat while new distinct paths of the same cost exist.
3. When the cheapest remaining path costs more turns than the previous
   one, first go through all *already found* paths again
   (`assign_all`) and assign them to more drones, making each of them
   **wait at `start_hub`** for the exact number of turns needed so they
   trail the original drone without ever colliding with it, before
   finally assigning the newly found, longer path.
4. Once no new path can be found at all (the graph is saturated), any
   remaining drones reuse the already-found paths, waiting increasingly
   longer at `start_hub`.

This design deliberately **never makes a drone wait mid-path** — only at
`start_hub`, which has unlimited capacity. This is a conscious trade-off:
it can occasionally cost a few extra turns compared to a fully
time-indexed, optimal scheduler, but it gives a simple, provable guarantee
against circular deadlocks, since a waiting drone never holds a resource
that another drone needs. In practice, on every provided test map the
resulting turn counts stayed within (and usually well below) the
benchmark targets from the subject.

### Output (`drones.py::generate_lines`)

`generate_lines` replays every drone's precomputed step list turn by turn,
emitting `D<id>-<zone>` for a normal move, `D<id>-<connection>` while a
drone is mid-transit into a `restricted` zone, and omitting drones that
have already reached `goal`, exactly as required by the subject's output
format.

## Visual representation

Two complementary visualizations are provided, controlled by `--visual`:

- **Terminal** (`generate_lines` + `print`): the raw turn-by-turn move log
  in the exact format required by the subject (`D1-roof1 D2-corridorA`,
  one line per turn). This is the ground truth used for scoring/validation.
- **Graphical** (`visualizer.py`, `pygame`): an animated replay of the same
  turns, showing each zone (color-coded by `Node.color`/zone type) and
  every drone moving between them, including partial progress while a
  drone is mid-transit on a `restricted` connection. This makes it much
  easier to spot visually whether drones ever share a zone/connection
  beyond its capacity, or whether the wave/wait scheduling is behaving as
  intended, without having to read the raw turn log line by line.

Both visualizations are driven by the exact same `generate_lines` output,
so what you see in the pygame window always matches what gets printed
(and what would be scored).

## Example

Input (`maps/easy/01_linear_path.txt`):

```
# Easy Level 1: Simple linear path
nb_drones: 2

start_hub: start 0 0 [color=green]
hub: waypoint1 1 0 [color=blue]
hub: waypoint2 2 0 [color=blue]
end_hub: goal 3 0 [color=red]

connection: start-waypoint1
connection: waypoint1-waypoint2
connection: waypoint2-goal
```

Command:

```bash
python3 main.py maps/easy/01_linear_path.txt --visual terminal
```

Output:

```
D1-waypoint1
D1-waypoint2 D2-waypoint1
D1-goal D2-waypoint2
D2-goal
```

4 turns for 2 drones on a strictly single-lane path — under the subject's
target of ≤ 6 turns for this scenario.
