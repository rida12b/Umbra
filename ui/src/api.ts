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
  activity: (id: string) => call<Turn[]>(`${project(id)}/activity`),
};
