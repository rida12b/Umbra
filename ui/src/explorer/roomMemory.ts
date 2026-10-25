import type { ProjectModel } from "../api";

// Where the reader was on the floor before entering a room, shared by the map and the phone list:
// Échap brings them back there, with focus on the room they were last in (also after a door).
const memory: { model: ProjectModel | null; top: number; entered: string | null } = { model: null, top: 0, entered: null };

export function enteredRoom(model: ProjectModel, bloc: string, top: number) {
  Object.assign(memory, { model, top, entered: bloc });
}

/** Going from room to room by a door. */
export function rememberRoom(bloc: string) {
  if (memory.model) memory.entered = bloc;
}

/** Once, on coming back to this project's floor: the scroll to restore and the room to focus. */
export function takeReturn(model: ProjectModel): { top: number; entered: string | null } | null {
  if (memory.model !== model) return null;
  memory.model = null;
  return { top: memory.top, entered: memory.entered };
}
