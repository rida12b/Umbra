import type { Door, Machine, Room } from "./room.ts";

// Where each piece of an open room sits: the start-up wiring band on top, the doors the data comes in
// by on the left, the doors it leaves by on the right, the machines in between on a belt that wraps
// like a line of text, and under each machine its refusals then what it searches or calls. Pure and
// measured: roomLayout.test.ts checks nothing overlaps and nothing runs past the width.

export interface Rect {
  x: number;
  y: number;
  w: number;
  h: number;
}
export interface Segment {
  from: string;
  to: string;
  points: { x: number; y: number }[];
}
export interface RoomPlan {
  rects: Map<string, Rect>; // keys: machine ids, `door:<bloc>`, `chute:<machine>:<n>`, `hung:<machine>:<bloc>`, "band"
  belt: Segment[]; // machine to machine, in belt order (a wrap runs back left between the lines)
  doorLinks: Segment[]; // a door to the machine it feeds, or a machine to the door it feeds
  size: { width: number; height: number };
}

const MACHINE = { w: 170, h: 150 };
const DOOR = { w: 170, h: 156 }; // the height grows with the crossings it lists (doorHeight)
const LINE = 17; // a 12.5px line of a refusal or a door
const PER_LINE = 26; // characters on one line of a 180px refusal (about 24-28 in practice)
const HUNG_H = 50;
const GAP = 48; // between machines: room for the belt arrow
const SIDE = 16; // between the door columns and the machines
const STACK = 10; // between things stacked under a machine
const LINE_GAP = 40;
const BAND_H = 70;

const lines = (text: string, per = PER_LINE) => Math.max(1, Math.ceil(text.length / per));
/** A refusal shows its condition in full and up to five lines of what follows. */
const chuteHeight = (c: { quand: string; alors: string; technical: boolean }) =>
  12 + LINE * (Math.min(lines(`Si ${c.quand}`), 4) + Math.min(lines(c.alors), 5)) + (c.technical ? 16 : 0);
/** A door: its name and verb on two lines each, then each crossing on up to two lines. */
const doorHeight = (d: Door) => Math.max(DOOR.h, 20 + LINE * 4 + d.crossings.slice(0, 3).reduce((h, c) => h + LINE * Math.min(lines(`→ ${c.step} · ${c.machine}`, 30), 2), 0));

export function placeRoom(room: Room, available: number): RoomPlan {
  const rects = new Map<string, Rect>();
  const left = room.doors.filter((d) => d.side === "left");
  const right = room.doors.filter((d) => d.side === "right");
  let y = 0;
  if (room.band.length) {
    rects.set("band", { x: 0, y: 0, w: Math.max(available, MACHINE.w), h: BAND_H });
    y = BAND_H + 24;
  }
  // Too narrow for a door column on each side of a machine: doors in go above the belt, doors out below.
  const stacked = available < (left.length ? DOOR.w + SIDE : 0) + (right.length ? DOOR.w + SIDE : 0) + MACHINE.w;
  const leftW = left.length && !stacked ? DOOR.w + SIDE : 0;
  const rightW = right.length && !stacked ? DOOR.w + SIDE : 0;
  const row = (doors: Door[], from: number) => {
    const per = Math.max(1, Math.floor((available + STACK) / (DOOR.w + STACK)));
    const rowH = Math.max(0, ...doors.map(doorHeight));
    doors.forEach((door, i) => rects.set(`door:${door.bloc}`, { x: (i % per) * (DOOR.w + STACK), y: from + Math.floor(i / per) * (rowH + STACK), w: DOOR.w, h: doorHeight(door) }));
    return doors.length ? from + Math.ceil(doors.length / per) * (rowH + STACK) - STACK + LINE_GAP : from;
  };
  if (stacked) y = row(left, y);
  const middle = Math.max(MACHINE.w, available - leftW - rightW);
  const perLine = Math.max(1, Math.floor((middle + GAP) / (MACHINE.w + GAP)));
  const lines: Machine[][] = [];
  for (let i = 0; i < room.belt.length; i += perLine) lines.push(room.belt.slice(i, i + perLine));

  const top = y;
  const gapBelow = new Map<string, number>();
  lines.forEach((line, n) => {
    let lineBottom = y + MACHINE.h;
    line.forEach((machine, i) => {
      const x = leftW + i * (MACHINE.w + GAP);
      rects.set(machine.id, { x, y, w: MACHINE.w, h: MACHINE.h });
      let under = y + MACHINE.h + STACK;
      machine.chutes.forEach((chute, k) => {
        const h = chuteHeight(chute);
        rects.set(`chute:${machine.id}:${k}`, { x, y: under, w: MACHINE.w, h });
        under += h + STACK;
      });
      machine.hung.forEach((h) => {
        rects.set(`hung:${machine.id}:${h.bloc}`, { x, y: under, w: MACHINE.w, h: HUNG_H });
        under += HUNG_H + STACK;
      });
      lineBottom = Math.max(lineBottom, under - STACK);
    });
    y = lineBottom + LINE_GAP;
    if (n < lines.length - 1) gapBelow.set(line.at(-1)!.id, y - LINE_GAP / 2);
  });
  const beltBottom = Math.max(y - LINE_GAP, top);

  // Doors stand at the height of the machine they deal with, stacked when several meet the same line.
  const machineOf = (door: Door, dir: "in" | "out") =>
    room.belt.find((m) => m.nom === door.crossings.find((c) => c.dir === dir)?.machine) ?? (dir === "in" ? room.belt[0] : room.belt.at(-1));
  const stack = (doors: Door[], x: number, dir: "in" | "out") => {
    let next = top;
    for (const door of doors) {
      const target = machineOf(door, dir);
      const at = target ? Math.max(next, rects.get(target.id)!.y) : next;
      const h = doorHeight(door);
      rects.set(`door:${door.bloc}`, { x, y: at, w: DOOR.w, h });
      next = at + h + STACK;
    }
    return next;
  };
  const rightX = leftW + Math.min(perLine, Math.max(room.belt.length, 1)) * (MACHINE.w + GAP) - GAP + SIDE;
  const leftEnd = stacked ? 0 : stack(left, 0, "in");
  const rightEnd = stacked ? row(right, beltBottom + LINE_GAP) + STACK - LINE_GAP : stack(right, rightX, "out");

  const mid = (r: Rect) => r.y + r.h / 2;
  const belt: Segment[] = room.belt.slice(1).map((machine, i) => {
    const a = rects.get(room.belt[i]!.id)!;
    const b = rects.get(machine.id)!;
    if (a.y === b.y) return { from: room.belt[i]!.id, to: machine.id, points: [{ x: a.x + a.w, y: mid(a) }, { x: b.x, y: mid(b) }] };
    const gap = gapBelow.get(room.belt[i]!.id) ?? a.y + a.h + LINE_GAP / 2;
    const lane = a.x + a.w + SIDE / 2; // clear of the right doors' column
    return {
      from: room.belt[i]!.id,
      to: machine.id,
      points: [{ x: a.x + a.w, y: mid(a) }, { x: lane, y: mid(a) }, { x: lane, y: gap }, { x: b.x - SIDE / 2, y: gap }, { x: b.x - SIDE / 2, y: mid(b) }, { x: b.x, y: mid(b) }],
    };
  });

  // A door's line is drawn only when nothing stands between it and its machine (first or last of its line).
  const doorLinks: Segment[] = [];
  for (const door of stacked ? [] : left) {
    const m = machineOf(door, "in");
    const d = rects.get(`door:${door.bloc}`)!;
    const r = m ? rects.get(m.id) : undefined;
    if (m && r && r.x === leftW && mid(d) >= r.y && mid(d) <= r.y + r.h) doorLinks.push({ from: `door:${door.bloc}`, to: m.id, points: [{ x: d.x + d.w, y: mid(d) }, { x: r.x, y: mid(d) }] });
  }
  for (const door of stacked ? [] : right) {
    const m = machineOf(door, "out");
    const d = rects.get(`door:${door.bloc}`)!;
    const r = m ? rects.get(m.id) : undefined;
    const lastOfLine = m && lines.some((line) => line.at(-1)?.id === m.id);
    if (m && r && lastOfLine && mid(d) >= r.y && mid(d) <= r.y + r.h) doorLinks.push({ from: m.id, to: `door:${door.bloc}`, points: [{ x: r.x + r.w, y: mid(d) }, { x: d.x, y: mid(d) }] });
  }
  const height = Math.max(beltBottom, leftEnd - STACK, rightEnd - STACK);
  const width = stacked ? Math.min(available, Math.max(rightX - SIDE, DOOR.w * Math.min(room.doors.length, 2) + STACK)) : Math.max(right.length ? rightX + DOOR.w : rightX - SIDE, MACHINE.w);
  if (room.band.length) rects.set("band", { ...rects.get("band")!, w: width });
  return { rects, belt, doorLinks, size: { width, height } };
}
