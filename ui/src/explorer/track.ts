import type { Journey } from "../api";
import { stepLabel } from "../arch/story";
import type { Level } from "./levels";
import type { Station } from "./stations";

/** Where one step of a journey shows on the current level. */
export interface StepOnMap {
  boxes: string[]; // the station: the box of its machine at this zoom (the machine, its room, its file)
  touched: string[]; // the parts it reaches: a faint ring
  link: string | null; // the arrow from the step before's station, if the level has one
  words: string; // the step's short action
}

/**
 * Each station of a journey (see journeyStations), placed on a level: its machine is mapped to the box that
 * holds it at this zoom (the room on the floor, the machine in a room, the step's file in a machine).
 */
export function trackJourney(journey: Journey, stations: Station[], level: Level): StepOnMap[] {
  const ids = new Set(level.boxes.map((b) => b.id));
  const here = (id: string | null) => (id && ids.has(id) ? id : null);
  const boxOf = (s: Station, n: number) =>
    here(s.machine) ?? here(s.room) ?? here(s.person) ?? here(journey.etapes[n]?.fichier ? `file:${journey.etapes[n]!.fichier}` : null);
  return stations.map((station, i) => {
    const box = boxOf(station, i);
    const before = i > 0 ? boxOf(stations[i - 1]!, i - 1) : null;
    const link = box && before && box !== before ? (level.links.find((l) => (l.from === before && l.to === box) || (l.from === box && l.to === before))?.id ?? null) : null;
    return {
      boxes: box ? [box] : [],
      touched: station.touches.flatMap((id) => (ids.has(id) && id !== box ? [id] : [])),
      link,
      words: stepLabel(journey.etapes[i]!),
    };
  });
}
