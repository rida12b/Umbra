import type { Door, Machine, Room } from "./room.ts";

// Where each piece of an open room sits, as in mockup B (V27-V38): a frame with the room's title, the
// start-up wiring band at its top, the machines on a belt that wraps like a line of text, under each
// machine its refusals then what it searches or calls, and under all of them the answer's lane. The
// doors stand outside the frame: data comes in on the left, leaves on the right. Pure and measured:
// roomLayout.test.ts checks nothing overlaps and nothing runs past the width.

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
  rects: Map<string, Rect>; // keys: machine ids, `door:<bloc>`, `chute:<machine>:<n>`, `hung:<machine>:<bloc>`, "band", "reply"
  frame: Rect; // the room's own box; everything but the doors is inside it
  belt: Segment[]; // machine to machine, in belt order (a wrap runs back left between the lines)
  doorLinks: Segment[]; // a door to the machine it feeds, or a machine to the door it feeds
  reply: Segment | null; // from the answering machine, under the room, up into the entry door
  size: { width: number; height: number };
}

const MACHINE = { w: 180, h: 176 }; // number, name on up to 3 lines, words, then its two in/out chips
const DOOR = { w: 130, h: 170 }; // the height grows with what it says (doorHeight)
const LINE = 17; // a 12.5px line of a refusal or a door
const PER_LINE = 23; // characters on one line of a 180px refusal (about 24-28 in practice)
const HUNG_H = 50;
const GAP = 48; // between machines: room for the belt arrow
const GUTTER = 30; // between a door and the frame: the belt arrow goes through it
const PAD = 16; // inside the frame
const TITLE = 34; // the frame's title line
const STACK = 12; // between things stacked under a machine
const LINE_GAP = 40;
const BAND_H = 62;
const REPLY_H = 46; // the answer's words (V38)

const lines = (text: string, per = PER_LINE) => Math.max(1, Math.ceil(text.length / per));
/** A refusal: its title, its condition in full and up to five lines of what follows. */
const chuteHeight = (c: { quand: string; alors: string; technical: boolean }) =>
  40 + LINE * (Math.min(lines(`Si ${c.quand}`), 4) + Math.min(lines(c.alors), 5)) + (c.technical ? 18 : 0);
/** A door: its badge, « depuis / vers <name> — <verb> » on up to four lines, then one chip per crossing out. */
const doorHeight = (d: Door, name: number): number =>
  Math.max(DOOR.h, 44 + LINE * Math.min(lines("x".repeat(name + d.verb.length + 10), 17), 5) + 26 * Math.min(d.crossings.length, 3) + 26);

export function placeRoom(room: Room, available: number, nameLength: (bloc: string) => number = () => 24): RoomPlan {
  const rects = new Map<string, Rect>();
  const left = room.doors.filter((d) => d.side === "left");
  const right = room.doors.filter((d) => d.side === "right");
  const height = (d: Door) => doorHeight(d, nameLength(d.bloc));
  // Too narrow for a door column on each side of a machine: doors in go above the frame, doors out below.
  const stacked = available < (left.length ? DOOR.w + GUTTER : 0) + (right.length ? DOOR.w + GUTTER : 0) + MACHINE.w + 2 * PAD;
  const leftW = left.length && !stacked ? DOOR.w + GUTTER : 0;
  const rightW = right.length && !stacked ? DOOR.w + GUTTER : 0;
  const row = (doors: Door[], from: number) => {
    const per = Math.max(1, Math.floor((available + STACK) / (DOOR.w + STACK)));
    const rowH = Math.max(0, ...doors.map(height));
    doors.forEach((door, i) => rects.set(`door:${door.bloc}`, { x: (i % per) * (DOOR.w + STACK), y: from + Math.floor(i / per) * (rowH + STACK), w: DOOR.w, h: height(door) }));
    return doors.length ? from + Math.ceil(doors.length / per) * (rowH + STACK) - STACK + LINE_GAP : from;
  };
  const frameTop = stacked ? row(left, 0) : 0;
  const inner = Math.max(MACHINE.w, available - leftW - rightW - 2 * PAD);
  const perLine = Math.max(1, Math.floor((inner + GAP) / (MACHINE.w + GAP)));
  const beltW = Math.min(perLine, Math.max(room.belt.length, 1)) * (MACHINE.w + GAP) - GAP;
  const x0 = leftW + PAD;
  let y = frameTop + TITLE;
  if (room.band.length) {
    rects.set("band", { x: x0, y, w: Math.max(beltW, Math.min(inner, 640)), h: BAND_H }); // wide enough for its file path (V29)
    y += BAND_H + 30; // room for the « câblage » marks down to the machines (V30)
  }
  const lines_: Machine[][] = [];
  for (let i = 0; i < room.belt.length; i += perLine) lines_.push(room.belt.slice(i, i + perLine));

  const top = y;
  const gapBelow = new Map<string, number>();
  lines_.forEach((line, n) => {
    let lineBottom = y + MACHINE.h;
    line.forEach((machine, i) => {
      const x = x0 + i * (MACHINE.w + GAP);
      rects.set(machine.id, { x, y, w: MACHINE.w, h: MACHINE.h });
      let under = y + MACHINE.h + 26; // the dashed tie to the refusal (V35)
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
    if (n < lines_.length - 1) gapBelow.set(line.at(-1)!.id, y - LINE_GAP / 2);
  });
  const beltBottom = Math.max(y - LINE_GAP, top);
  const contentW = Math.max(beltW, rects.get("band")?.w ?? 0);
  const frameW = contentW + 2 * PAD;

  // Doors stand at the height of the machine they deal with, stacked when several meet the same line.
  const machineOf = (door: Door, dir: "in" | "out") =>
    room.belt.find((m) => m.nom === door.crossings.find((c) => c.dir === dir)?.machine) ?? (dir === "in" ? room.belt[0] : room.belt.at(-1));
  const stack = (doors: Door[], x: number, dir: "in" | "out") => {
    let next = top;
    for (const door of doors) {
      const target = machineOf(door, dir);
      const at = target ? Math.max(next, rects.get(target.id)!.y) : next;
      rects.set(`door:${door.bloc}`, { x, y: at, w: DOOR.w, h: height(door) });
      next = at + height(door) + STACK;
    }
    return next;
  };
  const rightX = leftW + frameW + GUTTER;
  const leftEnd = stacked ? 0 : stack(left, 0, "in");

  // The answer runs under everything in the room, then climbs into the door it answers (V37).
  let reply: Segment | null = null;
  let frameBottom = beltBottom + PAD;
  const entry = room.reply && rects.get(`door:${room.reply.door}`);
  const speaker = room.reply && rects.get(room.reply.machine);
  if (room.reply && entry && speaker && !stacked) {
    const lane = Math.max(beltBottom + 22, entry.y + entry.h + 18);
    const labelW = Math.min(contentW, 470);
    const from = speaker.x + speaker.w - 16;
    const to = entry.x + entry.w / 2;
    const labelX = Math.min(Math.max(x0, (from + leftW) / 2 - labelW / 2), x0 + contentW - labelW);
    rects.set("reply", { x: labelX, y: lane + 10, w: labelW, h: REPLY_H });
    reply = { from: room.reply.machine, to: `door:${room.reply.door}`, points: [{ x: from, y: speaker.y + speaker.h }, { x: from, y: lane }, { x: to, y: lane }, { x: to, y: entry.y + entry.h }] };
    frameBottom = lane + 10 + REPLY_H + PAD;
  }
  const frame: Rect = { x: leftW, y: frameTop, w: frameW, h: frameBottom - frameTop };
  const rightEnd = stacked ? row(right, frameBottom + LINE_GAP) + STACK - LINE_GAP : stack(right, rightX, "out");

  const mid = (r: Rect) => r.y + Math.min(r.h, MACHINE.h) / 2;
  const belt: Segment[] = room.belt.slice(1).map((machine, i) => {
    const a = rects.get(room.belt[i]!.id)!;
    const b = rects.get(machine.id)!;
    if (a.y === b.y) return { from: room.belt[i]!.id, to: machine.id, points: [{ x: a.x + a.w, y: mid(a) }, { x: b.x, y: mid(b) }] };
    const gap = gapBelow.get(room.belt[i]!.id) ?? a.y + a.h + LINE_GAP / 2;
    const lane = a.x + a.w + PAD / 2; // inside the frame, clear of the right doors
    return {
      from: room.belt[i]!.id,
      to: machine.id,
      points: [{ x: a.x + a.w, y: mid(a) }, { x: lane, y: mid(a) }, { x: lane, y: gap }, { x: b.x - PAD / 2, y: gap }, { x: b.x - PAD / 2, y: mid(b) }, { x: b.x, y: mid(b) }],
    };
  });

  // A door's line is drawn only when nothing stands between it and its machine (first or last of its line).
  const doorLinks: Segment[] = [];
  for (const door of stacked ? [] : left) {
    const m = machineOf(door, "in");
    const d = rects.get(`door:${door.bloc}`)!;
    const r = m ? rects.get(m.id) : undefined;
    const y = Math.min(mid(d), r ? mid(r) : 0);
    if (m && r && r.x === x0 && y >= r.y && y <= r.y + r.h && y <= d.y + d.h) doorLinks.push({ from: `door:${door.bloc}`, to: m.id, points: [{ x: d.x + d.w, y }, { x: r.x, y }] });
  }
  for (const door of stacked ? [] : right) {
    const m = machineOf(door, "out");
    const d = rects.get(`door:${door.bloc}`)!;
    const r = m ? rects.get(m.id) : undefined;
    const lastOfLine = m && lines_.some((line) => line.at(-1)?.id === m.id);
    const y = r ? Math.max(d.y + 30, mid(r)) : 0;
    if (!m || !r || !lastOfLine) continue;
    if (y >= r.y && y <= r.y + r.h && y <= d.y + d.h) doorLinks.push({ from: m.id, to: `door:${door.bloc}`, points: [{ x: r.x + r.w, y }, { x: d.x, y }] });
    else {
      // A door stacked lower in the right column: the belt turns down in the gutter, then goes in (the exit is never left unlinked).
      const turn = d.x - GUTTER / 2;
      const into = d.y + Math.min(d.h / 2, 60);
      doorLinks.push({ from: m.id, to: `door:${door.bloc}`, points: [{ x: r.x + r.w, y: mid(r) }, { x: turn, y: mid(r) }, { x: turn, y: into }, { x: d.x, y: into }] });
    }
  }
  const bottom = Math.max(frameBottom, leftEnd - STACK, rightEnd - STACK);
  const width = stacked ? Math.max(frameW, Math.min(available, DOOR.w * Math.min(room.doors.length, 2) + STACK)) : right.length ? rightX + DOOR.w : leftW + frameW;
  return { rects, frame, belt, doorLinks, reply, size: { width, height: bottom } };
}
