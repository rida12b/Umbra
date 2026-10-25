import type { Journey, ProjectModel } from "../api";
import type { FloorItem, FloorLink, LinkStyle } from "./floor.ts";

// The words and lines of the factory floor: how each room is fed along the belt, how a hung part is
// linked to its room, and the style of every other flow. Pure, tested through floor.test.ts.

// Verbs are the model's plain words (« cherche dans », « démarre »): their first word says the kind.
export const READ = /^(cherche|lit|lis|lire|télécharge|telecharge|récupère|recupere|demande|consulte|interroge)/i;
const CONTROL = /^(démarre|demarre|lance|vérifie|verifie|configure|teste|déploie|deploie|surveille)/i;

/**
 * One link per belt segment: the flow that brings the data into the next room, from the room just
 * before when the model says so, else from the latest room before it (« Serveur fait analyser par »).
 * Without any flow, the action of the first step done in that room.
 */
export function beltLinks(model: ProjectModel, rooms: string[], journey: Journey | null, nameOf: (id: string) => string): FloorLink[] {
  return rooms.slice(1).map((to, i) => {
    const before = rooms.slice(0, i + 1);
    const feeding = model.flux.filter((f) => f.vers === to && before.includes(f.de) && !READ.test(f.verbe ?? ""));
    feeding.sort((a, b) => before.indexOf(b.de) - before.indexOf(a.de));
    const from = before[before.length - 1]!;
    const flow = feeding[0];
    const verb = flow
      ? flow.de === from
        ? (flow.verbe ?? flow.quoi)
        : `${nameOf(flow.de)} ${flow.verbe ?? flow.quoi}`
      : (firstAction(model, journey, to) ?? "");
    return { id: `belt:${from}>${to}`, from, to, verb, full: flow?.quoi ?? verb, style: "data" as const, control: false, data: true };
  });
}

function firstAction(model: ProjectModel, journey: Journey | null, room: string): string | null {
  const step = journey?.etapes.find((s) => (model.composants.find((c) => c.id === s.composant)?.bloc ?? s.composant) === room);
  return step?.action ?? null;
}

/** How a hung part reads next to its room: « Serveur cherche dans », « remplit Base des articles ». */
export function relations(model: ProjectModel, items: FloorItem[], nameOf: (id: string) => string): Record<string, string> {
  const words: Record<string, string> = {};
  for (const item of items) {
    if (!item.attach) continue;
    const flow = model.flux.find((f) => (f.de === item.attach && f.vers === item.id) || (f.de === item.id && f.vers === item.attach));
    if (!flow) continue;
    const verb = flow.verbe ?? flow.quoi;
    words[item.id] = flow.de === item.attach ? `${nameOf(item.attach)} ${verb}` : `${verb} ${nameOf(item.attach)}`;
  }
  return words;
}

/** Every other flow with its style. A reply goes back upstream to a part that sent something first. */
export function styledLinks(model: ProjectModel, position: (id: string) => number): FloorLink[] {
  const seen = new Set<string>();
  return model.flux.flatMap((flow) => {
    const id = `${flow.de}>${flow.vers}`;
    if (seen.has(id) || flow.de === flow.vers) return [];
    seen.add(id);
    const verb = flow.verbe ?? "";
    const back = model.flux.some((f) => f.de === flow.vers && f.vers === flow.de) && position(flow.vers) < position(flow.de);
    // The model's own word first (v1.7 `nature`); the verb is only a guess for older models.
    const isControl = (f: (typeof model.flux)[number]) => (f.nature ? f.nature === "controle" : CONTROL.test(f.verbe ?? ""));
    const same = model.flux.filter((f) => f.de === flow.de && f.vers === flow.vers);
    const control = same.some(isControl);
    const data = same.some((f) => !isControl(f));
    const style: LinkStyle = back ? "reply" : isControl(flow) ? "control" : READ.test(verb) ? "lookup" : "data";
    return [{ id, from: flow.de, to: flow.vers, verb, full: flow.quoi, style, control, data }];
  });
}
