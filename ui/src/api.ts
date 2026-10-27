// The local engine API (`/v1`), as the web app uses it. Same origin, no token: a session secret,
// kept in this page's storage (per origin, so per port) and sent in a header. Never a cookie:
// browsers would send it to every server on 127.0.0.1.

export interface Project {
  id: string;
  name: string;
  root: string;
  created_at: string;
}

export interface Turn {
  session: string;
  started: string;
  prompt: string;
  files: string[];
  message: string;
  ended: string | null;
}

/** A file and its lines; `start` 0 means the whole file. */
export interface Proof {
  file: string;
  start: number;
  end: number;
}

/** One box of the project map: a person who comes in (actor), a part that runs, or an outside service. */
export interface SystemBox {
  id: string;
  kind: "actor" | "box" | "external";
  title: string;
  detail: string;
  folder: string;
  role: string;
  proofs: Proof[];
  inferred: boolean; // deduced, not read: drawn dashed, « supposé »
  opens: boolean; // has an inside (Level 1): drawn with the « voir dedans » mark
  col: number; // placed once by the engine and stored: the map never moves
  row: number;
}

export interface SystemLink {
  id: string;
  source: string;
  target: string;
  verb: string;
  back: string; // the way back (« répond »), drawn as a second arrow; empty when none
  detail: string;
  proofs: Proof[];
  inferred: boolean;
}

export interface SystemOutput {
  id: string;
  box: string;
  label: string;
  detail: string;
  proofs: Proof[];
}

export interface AroundItem {
  id: string;
  title: string;
  short: string;
  detail: string;
  proofs: Proof[];
}

/** The Level 0 project map (ADR-0007), built from hard signals without any LLM. */
export interface SystemMap {
  name: string;
  sentence: string;
  branch: string;
  last_change: string; // YYYY-MM-DD
  boxes: SystemBox[];
  links: SystemLink[];
  outputs: SystemOutput[];
  around: AroundItem[];
  actions: number;
}

/** One part inside a box (Level 1, #105), or a grey stub standing for a neighbour of the box on Level 0. */
export interface InsidePart {
  id: string;
  kind: string; // « entry », « routes », « data »…, or « stub »
  title: string;
  detail: string;
  folders: string[]; // mono lines, relative to the box's folder
  role: string;
  proofs: Proof[];
  chips: Proof[]; // files drawn as chips inside the part (Routes)
  neighbour: string; // a stub: the Level 0 box it stands for
  side: "in" | "out" | "";
  opens: boolean; // a stub whose neighbour has an inside too
  inferred: boolean;
  col: number; // stored by the engine: the parts never move
  row: number;
}

/** Level 1 (ADR-0007): the inside of one box, ≤ 7 parts left → right, its neighbours as stubs. */
export interface InsideMap {
  box: string;
  title: string;
  folder: string;
  sentence: string;
  parts: InsidePart[];
  links: SystemLink[];
  outputs: SystemOutput[];
  around: AroundItem[];
}

/** One word of a card line: plain, a repo name in monospace, or deduced (dashed, « supposé »). */
export interface CardWord {
  text: string;
  mono: boolean;
  inferred: boolean;
  hint: string; // on hover: the files behind it; empty when none
}

/** « Reçoit », « Renvoie », « Appelé par » or « Appelle »; no word when nothing was read. */
export interface CardLine {
  label: string;
  words: CardWord[];
  proofs: Proof[];
}

/** A function of the card, opened in VS Code at its line; a route also has its verb and address. */
export interface CardFunction {
  name: string;
  file: string;
  line: number;
  verb: string;
  path: string;
  label: string; // « Voir un item », « Voir son profil »; empty when no rule names it (#108)
  action: string; // a route: its id in « Ce qu'on peut faire », whose path « chemin → » lights (#107)
}

/** One thing the project can be asked to do (#107): an address the server answers, or a CLI command. */
export interface Action {
  id: string; // the function's file and line: « backend/app/api/routes/items.py:62 »
  kind: "routes" | "commands";
  verb: string; // « POST »; empty for a command
  label: string; // « Créer un item », « Voir son profil »; empty when no rule names it (#108)
  address: string; // « /api/v1/items/ », or the command as typed: « insert »
  name: string;
  file: string;
  line: number;
}

/** « Ce qu'on peut faire », grouped by the file that holds them. */
export interface ActionList {
  total: number;
  groups: { file: string; kind: "routes" | "commands"; role: string; actions: Action[] }[];
}

/** Level 2 (ADR-0007, #106): one part of a box, or one file of it, in four lines and its functions. */
export interface PartCard {
  box: string;
  part: string;
  file: string; // empty for the whole part
  title: string;
  folder: string;
  path: string;
  sentence: string;
  open_file: string;
  lines: CardLine[];
  section: string;
  functions: CardFunction[];
  more: number;
}

/** One numbered place of a lit path, under its box: « 3 models.py — ajouter le champ ». */
export interface LitStep {
  n: number;
  box: string;
  label: string; // short, in the box's own terms
  path: string; // repo path, a folder ends with "/"; empty for a box without a folder
  note: string;
  why: string; // « pourquoi ici », on hover; empty when Claude gave none
  part: string; // drawn inside `Highlight.inside` (Level 1): the part or stub it numbers
  guess: boolean; // deduced, not read: drawn dashed, « supposé »
  chip: string; // the file chip that lights with it (« items.py » in Routes)
}

/** What is lit on the map (#104, #107): a question Claude Code answered with `show`, or the path of an
 * action traced in the code. Boxes or parts lit, ≤ 6 numbered steps, the rest dimmed. */
export interface Highlight {
  caption: string;
  boxes: string[];
  steps: LitStep[];
  files: string[]; // what « copier pour Claude » copies
  serial: number;
  kind: "question" | "path";
  detail: string; // said after the caption when copied: « POST /api/v1/items/ »
  inside: string; // the box whose inside (Level 1) shows it; empty: the whole map
  parts: string[]; // Level 1: lit parts and stubs
  passed: string[]; // Level 1: parts the path goes through without a number
}

/** Why a request failed, in the terms the page shows. */
export class ApiError extends Error {
  constructor(
    readonly status: number,
    message: string,
  ) {
    super(message);
  }

  get needsLogin(): boolean {
    return this.status === 401;
  }
}

const SESSION_KEY = "umbra-session";
let memorySession: string | null = null; // when storage is blocked: this page only
let onUnauthorized: () => void = () => undefined;

function readSession(): string | null {
  try {
    return window.localStorage.getItem(SESSION_KEY) ?? memorySession;
  } catch {
    return memorySession;
  }
}

function keepSession(session: string | null): void {
  memorySession = session;
  try {
    if (session) window.localStorage.setItem(SESSION_KEY, session);
    else window.localStorage.removeItem(SESSION_KEY);
  } catch {
    // kept in memory only
  }
}

/** The session header, for requests made outside `call` (the live stream). */
export function readSessionHeader(): Record<string, string> {
  const session = readSession();
  return session ? { "X-Umbra-Session": session } : {};
}

/** The session is gone (engine restarted, or expired): forget it and ask the person to sign in again. */
export function signedOut(): void {
  keepSession(null);
  onUnauthorized();
}

/** Called once by the app: any 401 means the session is gone (engine restarted, or expired). */
export function whenSignedOut(handler: () => void): void {
  onUnauthorized = handler;
}

async function call<T>(path: string, init: RequestInit = {}): Promise<T> {
  let response: Response;
  const session = readSession();
  try {
    response = await fetch(path, {
      ...init,
      credentials: "omit",
      headers: {
        ...(session ? { "X-Umbra-Session": session } : {}),
        ...(init.body ? { "Content-Type": "application/json" } : {}),
      },
    });
  } catch {
    throw new ApiError(0, "The Umbra engine does not answer. Is `umbra-engine serve` running?");
  }
  if (response.status === 401 && !path.startsWith("/v1/ui/")) signedOut();
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    const detail = typeof body.detail === "string" ? body.detail : response.statusText;
    throw new ApiError(response.status, detail);
  }
  return response.status === 204 ? (undefined as T) : ((await response.json()) as T);
}

const project = (id: string) => `/v1/projects/${encodeURIComponent(id)}`;

export const api = {
  openSession: async (code: string) => {
    const { session } = await call<{ session: string }>("/v1/ui/session", {
      method: "POST",
      body: JSON.stringify({ code }),
    });
    keepSession(session);
  },
  projects: () => call<Project[]>("/v1/projects"),
  /** `retry`: after a failed read, read the project again at once (« Réessayer »). */
  system: (id: string, retry = false) => call<SystemMap>(`${project(id)}/system${retry ? "?relire=true" : ""}`),
  /** Level 1: the inside of one box of the map; 404 when it has none. */
  inside: (id: string, box: string) => call<InsideMap>(`${project(id)}/system/inside?box=${encodeURIComponent(box)}`),
  /** Level 2: the card of one part of a box, or of one file of it; 404 when it is not drawn there. */
  card: (id: string, box: string, part: string, file: string | null) =>
    call<PartCard>(`${project(id)}/system/card?${new URLSearchParams({ box, part, file: file ?? "" })}`),
  activity: (id: string) => call<Turn[]>(`${project(id)}/activity`),
  /** What is lit now (a tab opened after Claude's `show` call); null when nothing. */
  shownNow: (id: string) => call<Highlight | null>(`${project(id)}/show`),
  /** « Ce qu'on peut faire »: the addresses and commands, grouped by file. */
  actions: (id: string) => call<ActionList>(`${project(id)}/system/actions`),
  /** Lights an action's traced path on every open tab (the same highlight as a `show`). */
  showAction: (id: string, action: string) => call<Highlight>(`${project(id)}/show/action`, { method: "POST", body: JSON.stringify({ action }) }),
  /** « effacer »: every open tab goes back to the plain map. */
  clearShown: (id: string) => call<{ cleared: boolean }>(`${project(id)}/show`, { method: "DELETE" }),
};
