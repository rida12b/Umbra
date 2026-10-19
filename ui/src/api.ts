// The local engine API (`/v1`), as the web app uses it. Same origin, no token: a session secret,
// kept in this page's storage (per origin, so per port) and sent in a header. Never a cookie:
// browsers would send it to every server on 127.0.0.1.

export type NodeKind =
  | "application" | "service" | "component" | "module"
  | "function" | "class" | "method" | "type" | "group";
export type MapStatus = "fact" | "hypothesis" | "declaration";

export interface Project {
  id: string;
  name: string;
  root: string;
  created_at: string;
}

export interface MapNode {
  key: string;
  kind: NodeKind;
  label: string;
  status: MapStatus;
  children: number;
  path: string | null;
  lines: [number, number] | null;
  details: Record<string, string[]>;
  hidden: string[];
  evidence: string[];
}

export interface MapEdge {
  source: string;
  target: string;
  relation: string;
  status: MapStatus;
  count: number;
  evidence: string[];
}

export interface Crumb {
  key: string;
  kind: NodeKind;
  label: string;
}

export interface MapView {
  parent: MapNode;
  breadcrumbs: Crumb[];
  nodes: MapNode[];
  edges: MapEdge[];
  total_children: number;
}

export interface Claim {
  key: string;
  file: string;
  subject: string;
  relation: string;
  object: string;
  status: "fact" | "hypothesis" | "observation";
  line_start: number;
  line_end: number;
  producer: string;
  evidence_version: string;
}

export interface Excerpt {
  file: string;
  version: string;
  start: number;
  end: number;
  first_line: number;
  lines: string[];
  current: boolean;
}

export interface IndexSummary {
  files: number;
  readable: number;
  claims: Record<string, number>;
}

export interface Located {
  texte: string;
  fichier: string | null;
  lignes: [number, number] | null;
}

/** What Claude Code wrote about one element: an LLM's reading of the code, so a Hypothesis. */
export interface Card {
  role: string;
  entrees: string[];
  sorties: string[];
  etapes: Located[];
  points_entree: Located[];
  depend_de: string[];
  enfants: Record<string, string>;
  incertitudes: string[];
}

export type BlockType =
  | "user" | "frontend" | "backend" | "worker" | "database" | "storage" | "queue" | "external"
  | "ml_model" | "device" | "cli" | "library" | "docs" | "tests" | "infra";

export interface ArchBlock {
  id: string;
  nom: string;
  type: BlockType;
  role: string;
  techno: string;
  code: { chemin: string; element: string }[];
  indices: string;
}

export interface ArchFlow {
  de: string;
  vers: string;
  quoi: string;
}

/** The Project drawn as running parts, stores and outside services: Claude Code's reading (Hypothesis). */
export interface Architecture {
  resume: string;
  blocs: ArchBlock[];
  flux: ArchFlow[];
  parcours: string[];
  incertitudes: string[];
}

export const ARCHITECTURE = "arch:";

export interface Explanation<T = Card> {
  state: "ready" | "stale" | "missing" | "queued" | "working" | "error";
  card: T | null;
  producer: string | null;
  created_at: string | null;
  message: string | null;
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

  get staleIndex(): boolean {
    return this.status === 409;
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
  if (response.status === 401 && !path.startsWith("/v1/ui/")) {
    keepSession(null);
    onUnauthorized();
  }
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
  index: (id: string) => call<IndexSummary>(`${project(id)}/index`, { method: "POST" }),
  map: (id: string, node: string, expand: boolean) =>
    call<MapView>(`${project(id)}/map?${new URLSearchParams({ node, expand: String(expand) })}`),
  explanation: (id: string, node: string) =>
    call<Explanation>(`${project(id)}/explain?${new URLSearchParams({ node })}`),
  explain: (id: string, node: string) =>
    call<Explanation>(`${project(id)}/explain?${new URLSearchParams({ node })}`, { method: "POST" }),
  claim: (id: string, key: string) => call<Claim>(`${project(id)}/claims/${encodeURIComponent(key)}`),
  evidence: (id: string, file: string, start: number, end: number) =>
    call<Excerpt>(
      `${project(id)}/evidence?${new URLSearchParams({ file, start: String(start), end: String(end) })}`,
    ),
};
