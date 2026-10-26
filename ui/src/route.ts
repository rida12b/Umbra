import { useEffect, useState } from "react";

// Where the user is, kept in the URL fragment so Back/Forward and reloads work.
// `#/` lists Projects; `#/p/<id>?node=x:<level>` one level of its explorer; any other node is a code map view.
// A login link arrives as `#login=<code>`: it is consumed once and replaced, never kept in history.

export interface Route {
  projectId: string | null;
  node: string;
  expand: boolean;
  journey?: string | null; // on the architecture: the journey lit on the map, and its active step
  step?: number | null;
  select?: string | null; // on a map view: the element to select (from a search)
  row?: string | null; // on a plate: the settings row a search landed on (its exact code), lit and in view
}

export const ARCHITECTURE_VIEW = "arch:"; // a Project opens on its architecture
const OLD_JOURNEYS_VIEW = "parcours:"; // journeys now live on the architecture: old links still open
export const ACTIVITY_VIEW = "activite:";
const LOGIN = "#login=";

export function takeLoginCode(): string | null {
  if (!window.location.hash.startsWith(LOGIN)) return null;
  const code = safeDecode(window.location.hash.slice(LOGIN.length));
  window.history.replaceState(null, "", `${window.location.pathname}#/`);
  return code || null;
}

export function parseRoute(hash: string): Route {
  const [path = "", query = ""] = hash.replace(/^#/, "").split("?", 2);
  const match = /^\/p\/([^/]+)$/.exec(path);
  const params = new URLSearchParams(query);
  const node = params.get("node");
  return {
    projectId: match?.[1] ? safeDecode(match[1]) : null,
    node: !node || node === OLD_JOURNEYS_VIEW ? ARCHITECTURE_VIEW : node,
    expand: params.get("expand") === "1",
    journey: params.get("journey"),
    step: positive(params.get("step")),
    select: params.get("select"),
    row: params.get("row"),
  };
}

/** `step=3` → 3; anything else (`abc`, `0`, `-2`) → no step. */
function positive(text: string | null): number | null {
  const value = Number(text);
  return text && Number.isInteger(value) && value > 0 ? value : null;
}

/** A mistyped or truncated link (`%E0`) must not blank the page. */
function safeDecode(text: string): string | null {
  try {
    return decodeURIComponent(text);
  } catch {
    return null;
  }
}

export function routeHash(route: Route): string {
  if (!route.projectId) return "#/";
  const params = new URLSearchParams();
  if (route.node !== ARCHITECTURE_VIEW) params.set("node", route.node);
  if (route.expand) params.set("expand", "1");
  if (route.journey) params.set("journey", route.journey);
  if (route.step) params.set("step", String(route.step));
  if (route.select) params.set("select", route.select);
  if (route.row) params.set("row", route.row);
  const query = params.toString();
  return `#/p/${encodeURIComponent(route.projectId)}${query ? `?${query}` : ""}`;
}

/** `replace`: the new place takes the current history entry (a step the reader did not choose, like going down to
 * the function that holds a cited line), so Back skips it instead of landing on it again. */
export function navigate(route: Route, { replace = false }: { replace?: boolean } = {}): void {
  if (!replace) {
    window.location.hash = routeHash(route);
    return;
  }
  window.history.replaceState(null, "", routeHash(route));
  window.dispatchEvent(new HashChangeEvent("hashchange"));
}

export function useRoute(): Route {
  const [route, setRoute] = useState(() => parseRoute(window.location.hash));
  useEffect(() => {
    const update = () => setRoute(parseRoute(window.location.hash));
    window.addEventListener("hashchange", update);
    return () => window.removeEventListener("hashchange", update);
  }, []);
  return route;
}
