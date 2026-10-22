import type { Placed, Point } from "../arch/archLayout";

// The zoned levels (context, parts) drawn as rows, read from top to bottom: who uses it, what receives,
// what processes, where it is kept, outside services. A screen is wider than tall and a row holds few
// boxes, so five zones fit at a readable size, and the gaps between rows are wide enough for the
// arrows' words. Arrows run at right angles in those gaps; an arrow that skips a row goes round
// by a lane on the right, never over a box.

export interface RowBox {
  id: string;
  row: number; // the zone's index: rows keep this order, empty ones are dropped
}

export interface RowArrow {
  key: string;
  source: string;
  target: string;
}

export interface RowLabel {
  at: Point; // the middle of the arrow's words, in a gap between rows
}

export interface RowsPlaced extends Placed {
  labels: Map<string, RowLabel>;
  rows: { row: number; y: number; height: number }[]; // where each zone's rows are, for its title
}

const BOX_GAP = 40; // between two boxes of a row
const TRACK = 18; // between two arrows running in the same gap
const MIN_GAP = 76; // between two rows: room for one line of words
const LANE = 16; // between two lanes on the right
const PER_ROW = 3; // a zone with more boxes wraps onto the next row: the map stays readable on a laptop
export const ROW_TITLE_WIDTH = 150; // the zone titles, left of the rows

export function placeRows(boxes: RowBox[], arrows: RowArrow[], size: { width: number; height: number }): RowsPlaced {
  const { width: W, height: H } = size;
  const zones = [...new Set(boxes.map((b) => b.row))].sort((a, b) => a - b);
  const rows: string[][] = [];
  const zoneOfRow: number[] = [];
  for (const zone of zones) {
    const ids = boxes.filter((b) => b.row === zone).map((b) => b.id);
    for (let i = 0; i < ids.length; i += PER_ROW) {
      rows.push(ids.slice(i, i + PER_ROW));
      zoneOfRow.push(zone);
    }
  }
  const rowOf = new Map(rows.flatMap((row, r) => row.map((id) => [id, r] as const)));
  const links = arrows.filter((a) => rowOf.has(a.source) && rowOf.has(a.target) && a.source !== a.target);

  // Order each row by where its neighbours sit (barycentre, down then up): fewer crossings.
  const order = new Map<string, number>();
  const setOrder = () => rows.forEach((row) => row.forEach((id, i) => order.set(id, i - (row.length - 1) / 2)));
  setOrder();
  const neighbours = (id: string, rowIndex: number) =>
    links.flatMap((a) => (a.source === id ? [a.target] : a.target === id ? [a.source] : [])).filter((o) => rowOf.get(o) === rowIndex);
  const sweep = (from: number, to: number, step: number) => {
    for (let r = from; r !== to; r += step) {
      const row = rows[r];
      if (!row) continue;
      const weight = (id: string) => {
        const near = neighbours(id, r - step);
        return near.length ? near.reduce((sum, o) => sum + (order.get(o) ?? 0), 0) / near.length : (order.get(id) ?? 0);
      };
      row.sort((a, b) => weight(a) - weight(b));
      setOrder();
    }
  };
  sweep(1, rows.length, 1);
  sweep(rows.length - 2, -1, -1);

  // Which gap each arrow runs in (gap g lies under row g), so each gap gets the height it needs.
  type Route = { arrow: RowArrow; from: number; to: number; gaps: number[]; lane: number | null };
  const routes: Route[] = links.map((arrow) => {
    const from = rowOf.get(arrow.source) ?? 0;
    const to = rowOf.get(arrow.target) ?? 0;
    if (from === to) return { arrow, from, to, gaps: [from], lane: null };
    if (Math.abs(from - to) === 1) return { arrow, from, to, gaps: [Math.min(from, to)], lane: null };
    // Skips a row: out into the gap next to its start, round by a lane, in from the gap next to its end.
    return { arrow, from, to, gaps: from < to ? [from, to - 1] : [from - 1, to], lane: 0 };
  });
  let lanes = 0;
  for (const route of routes) if (route.lane !== null) route.lane = lanes++;
  const tracks: Route[][] = rows.map(() => []);
  for (const route of routes) for (const gap of route.gaps) tracks[gap]?.push(route);
  const gapHeight = tracks.map((list) => Math.max(MIN_GAP, (list.length + 1) * TRACK));

  const rowWidth = (row: string[]) => row.length * W + (row.length - 1) * BOX_GAP;
  const widest = Math.max(0, ...rows.map(rowWidth));
  const position = new Map<string, Point>();
  const rowY: number[] = [];
  let y = 0;
  rows.forEach((row, r) => {
    rowY.push(y);
    const left = ROW_TITLE_WIDTH + (widest - rowWidth(row)) / 2;
    row.forEach((id, i) => position.set(id, { x: left + i * (W + BOX_GAP), y }));
    y += H + (r < rows.length - 1 || (tracks[r]?.length ?? 0) > 0 ? (gapHeight[r] ?? MIN_GAP) : 0);
  });
  const right = ROW_TITLE_WIDTH + widest;

  const trackY = (route: Route, gap: number) => {
    const list = tracks[gap] ?? [];
    const top = (rowY[gap] ?? 0) + H;
    return top + ((list.indexOf(route) + 1) * (gapHeight[gap] ?? MIN_GAP)) / (list.length + 1);
  };
  const centre = (id: string) => (position.get(id)?.x ?? 0) + W / 2;

  // Where each arrow leaves or reaches a box edge: spread along it, in the order of the other ends.
  const ports = new Map<string, number>(); // `${arrowKey}|${end}` → x
  const ends = new Map<string, { key: string; end: "from" | "to"; toward: number }[]>();
  const sideOf = (route: Route, end: "from" | "to") => {
    const here = end === "from" ? route.from : route.to;
    const gap = end === "from" ? route.gaps[0] : route.gaps[route.gaps.length - 1];
    return gap !== undefined && gap >= here ? "bottom" : "top";
  };
  for (const route of routes)
    for (const end of ["from", "to"] as const) {
      const id = end === "from" ? route.arrow.source : route.arrow.target;
      const other = end === "from" ? route.arrow.target : route.arrow.source;
      const side = `${id}|${sideOf(route, end)}`;
      const toward = route.lane !== null ? Number.MAX_SAFE_INTEGER : centre(other);
      ends.set(side, [...(ends.get(side) ?? []), { key: route.arrow.key, end, toward }]);
    }
  for (const [side, list] of ends) {
    const left = position.get(side.split("|")[0] ?? "")?.x ?? 0;
    list.sort((a, b) => a.toward - b.toward);
    list.forEach((item, i) => ports.set(`${item.key}|${item.end}`, left + ((i + 1) * W) / (list.length + 1)));
  }

  const placedArrows = new Map<string, { points: Point[] }>();
  const labels = new Map<string, RowLabel>();
  for (const route of routes) {
    const { arrow } = route;
    const a = position.get(arrow.source);
    const b = position.get(arrow.target);
    if (!a || !b) continue;
    const ax = ports.get(`${arrow.key}|from`) ?? centre(arrow.source);
    const bx = ports.get(`${arrow.key}|to`) ?? centre(arrow.target);
    const ay = sideOf(route, "from") === "bottom" ? a.y + H : a.y;
    const by = sideOf(route, "to") === "bottom" ? b.y + H : b.y;
    const first = route.gaps[0] ?? 0;
    const last = route.gaps[route.gaps.length - 1] ?? first;
    if (route.lane === null) {
      const ty = trackY(route, first);
      placedArrows.set(arrow.key, { points: [{ x: ax, y: ay }, { x: ax, y: ty }, { x: bx, y: ty }, { x: bx, y: by }] });
      labels.set(arrow.key, { at: { x: (ax + bx) / 2, y: ty } });
    } else {
      const lx = right + 28 + route.lane * LANE;
      const ty1 = trackY(route, first);
      const ty2 = trackY(route, last);
      placedArrows.set(arrow.key, {
        points: [{ x: ax, y: ay }, { x: ax, y: ty1 }, { x: lx, y: ty1 }, { x: lx, y: ty2 }, { x: bx, y: ty2 }, { x: bx, y: by }],
      });
      labels.set(arrow.key, { at: { x: (ax + lx) / 2, y: ty1 } }); // in the gap it leaves by
    }
  }

  return {
    size: { width: right + 28 + lanes * LANE, height: y }, // a lane's words, shown on hover, may run past it
    boxes: position,
    arrows: placedArrows,
    labels,
    rows: zones.map((zone) => {
      const first = zoneOfRow.indexOf(zone);
      const last = zoneOfRow.lastIndexOf(zone);
      return { row: zone, y: rowY[first] ?? 0, height: (rowY[last] ?? 0) + H - (rowY[first] ?? 0) };
    }),
  };
}
