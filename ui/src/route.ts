import { useEffect, useState } from "react";

// Where the user is, kept in the URL fragment so Back/Forward and reloads work.
// `#/` lists Projects; `#/p/<id>?node=<key>&expand=1` shows one map view.
// A login link arrives as `#login=<code>`: it is consumed once and replaced, never kept in history.

export interface Route {
  projectId: string | null;
  node: string;
  expand: boolean;
}

export const APPLICATION = "app:";
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
  return {
    projectId: match?.[1] ? safeDecode(match[1]) : null,
    node: params.get("node") ?? APPLICATION,
    expand: params.get("expand") === "1",
  };
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
  if (route.node !== APPLICATION) params.set("node", route.node);
  if (route.expand) params.set("expand", "1");
  const query = params.toString();
  return `#/p/${encodeURIComponent(route.projectId)}${query ? `?${query}` : ""}`;
}

export function navigate(route: Route): void {
  window.location.hash = routeHash(route);
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
