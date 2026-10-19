// The local engine API (`/v1`), as the web app uses it. Same origin, session cookie, no token.

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

const UI_HEADER = { "X-Umbra-Client": "web" };

async function call<T>(path: string, init: RequestInit = {}): Promise<T> {
  let response: Response;
  try {
    response = await fetch(path, {
      ...init,
      credentials: "same-origin",
      headers: { ...UI_HEADER, ...(init.body ? { "Content-Type": "application/json" } : {}) },
    });
  } catch {
    throw new ApiError(0, "The Umbra engine does not answer. Is `umbra-engine serve` running?");
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
  openSession: (code: string) =>
    call<void>("/v1/ui/session", { method: "POST", body: JSON.stringify({ code }) }),
  projects: () => call<Project[]>("/v1/projects"),
  index: (id: string) => call<IndexSummary>(`${project(id)}/index`, { method: "POST" }),
  map: (id: string, node: string, expand: boolean) =>
    call<MapView>(`${project(id)}/map?${new URLSearchParams({ node, expand: String(expand) })}`),
  claim: (id: string, key: string) => call<Claim>(`${project(id)}/claims/${encodeURIComponent(key)}`),
  evidence: (id: string, file: string, start: number, end: number) =>
    call<Excerpt>(
      `${project(id)}/evidence?${new URLSearchParams({ file, start: String(start), end: String(end) })}`,
    ),
};
