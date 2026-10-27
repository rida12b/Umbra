import { useEffect, useState } from "react";

// Where the user is, kept in the URL fragment so Back/Forward and reloads work.
// `#/` lists Projects; `#/p/<id>` opens its map; `#/p/<id>?node=activite:` what Claude Code did in it.
// A login link arrives as `#login=<code>`: it is consumed once and replaced, never kept in history.

export interface Route {
  projectId: string | null;
  node: string;
}

export const MAP_VIEW = "arch:"; // a Project opens on its map; links made for older views open it too
export const ACTIVITY_VIEW = "activite:";
const LOGIN = "#login=";

/** `#login=<code>&p=<id>` (`umbra-engine start`): the code, and the page to land on once signed in. */
export function parseLogin(hash: string): { code: string | null; landing: string } | null {
  if (!hash.startsWith(LOGIN)) return null;
  const [code = "", ...rest] = hash.slice(LOGIN.length).split("&");
  const projectId = new URLSearchParams(rest.join("&")).get("p");
  return { code: safeDecode(code) || null, landing: projectId ? routeHash({ projectId, node: MAP_VIEW }) : "#/" };
}

export function takeLoginCode(): string | null {
  const login = parseLogin(window.location.hash);
  if (!login) return null;
  window.history.replaceState(null, "", `${window.location.pathname}${login.landing}`);
  return login.code;
}

export function parseRoute(hash: string): Route {
  const [path = "", query = ""] = hash.replace(/^#/, "").split("?", 2);
  const match = /^\/p\/([^/]+)$/.exec(path);
  const node = new URLSearchParams(query).get("node");
  return {
    projectId: match?.[1] ? safeDecode(match[1]) : null,
    node: node === ACTIVITY_VIEW ? ACTIVITY_VIEW : MAP_VIEW,
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
  const query = route.node === MAP_VIEW ? "" : `?${new URLSearchParams({ node: route.node })}`;
  return `#/p/${encodeURIComponent(route.projectId)}${query}`;
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
