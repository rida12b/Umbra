import { useEffect, useState } from "react";
import { api, type SearchHit } from "./api";
import { KIND_LABEL } from "./map/ElementNode";
import { navigate } from "./route";

const WAIT_MS = 200;

/** Jump to any service, folder, file or function by name. */
export function SearchBox({ projectId }: { projectId: string }) {
  const [query, setQuery] = useState("");
  const [hits, setHits] = useState<SearchHit[]>([]);

  useEffect(() => {
    if (query.trim().length < 2) {
      setHits([]);
      return;
    }
    let current = true;
    const timer = window.setTimeout(() => {
      api.search(projectId, query).then((found) => current && setHits(found), () => current && setHits([]));
    }, WAIT_MS);
    return () => {
      current = false;
      window.clearTimeout(timer);
    };
  }, [projectId, query]);

  const open = (hit: SearchHit) => {
    setQuery("");
    navigate({ projectId, node: hit.level, expand: true, select: hit.key });
  };

  return (
    <div className="search">
      <input
        type="search"
        placeholder="Chercher un fichier, une fonction…"
        aria-label="Chercher dans le projet"
        value={query}
        onChange={(event) => setQuery(event.target.value)}
        onKeyDown={(event) => {
          if (event.key === "Enter" && hits[0]) open(hits[0]);
          if (event.key === "Escape") setQuery("");
        }}
      />
      {hits.length > 0 && (
        <ul className="search-hits" role="listbox">
          {hits.map((hit) => (
            <li key={hit.key}>
              <button onClick={() => open(hit)}>
                <span className="search-kind">{KIND_LABEL[hit.kind]}</span>
                <span className="search-label">{hit.label}</span>
                {hit.path && <span className="search-path">{hit.path}</span>}
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
