"""Where each box of the Level 0 map sits, as grid cells (column, row): entries in column 0, then each box
right of what reaches it, outside services under their caller. A box placed once keeps its cell."""

from collections import defaultdict

from umbra_engine.projection.system_model import SystemBox, SystemLink

Cell = tuple[int, int]


def place(boxes: list[SystemBox], links: list[SystemLink], stored: dict[str, Cell]) -> dict[str, Cell]:
    cells: dict[str, Cell] = {}
    taken: set[Cell] = set()

    def put(key: str, col: int, row: int) -> None:
        while (col, row) in taken:
            row += 1
        cells[key] = (col, row)
        taken.add((col, row))

    for box in boxes:  # stored cells first: nothing that was seen before ever moves
        if box.id in stored and stored[box.id] not in taken:
            cells[box.id] = stored[box.id]
            taken.add(stored[box.id])
    kinds = {b.id: b.kind for b in boxes}
    actors = [b.id for b in boxes if b.kind == "actor"]
    for index, key in enumerate(actors):
        if key not in cells:
            put(key, 0, index)
    targets: dict[str, list[str]] = defaultdict(list)
    for link in links:
        targets[link.source].append(link.target)
    queue, seen = list(actors), set(actors)
    while queue:
        source = queue.pop(0)
        col, row = cells[source]
        right_taken = False
        # Main parts go right, outside services hang below: a database before a mail server.
        for target in sorted(targets[source], key=lambda t: kinds.get(t) == "external"):
            if target not in kinds:
                continue
            if target not in cells:
                if kinds[target] == "external" or right_taken:
                    put(target, max(col, 1), row + 1)
                else:
                    put(target, col + 1, row)
                    right_taken = True
            if target not in seen:
                seen.add(target)
                queue.append(target)
    for box in boxes:
        if box.id not in cells:
            put(box.id, 1, 0)
    return cells
