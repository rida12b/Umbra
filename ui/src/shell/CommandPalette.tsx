import { Command } from "cmdk";
import { useEffect, useMemo, useState } from "react";
import { api, type ProjectModel, type SearchHit } from "../api";
import { KIND_LABEL } from "../map/ElementNode";
import { DEFAULT_LEVEL, levelNode } from "../explorer/Explorer";
import { PROJECT_SETTINGS } from "../explorer/levels";
import { enterable } from "../explorer/room";
import { buildIndex, searchIndex, type Target } from "../explorer/searchIndex";
import { followedRoom, journeyStations } from "../explorer/stations";
import { navigate, type Route } from "../route";

const WAIT_MS = 200;
const PER_GROUP = 8; // more than this in a group: « +N » (#80)

interface Props {
  projectId: string;
  model: ProjectModel | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

/** Where a result lands (#80): the room with the machine's plate open and the row lit, the journey at its step, the code. */
function landing(model: ProjectModel, target: Target): Omit<Route, "projectId"> {
  const floor = { node: levelNode(DEFAULT_LEVEL), expand: false, journey: null, step: null, select: null, row: null };
  switch (target.kind) {
    case "machine":
      return { ...floor, node: levelNode(`part:${target.bloc}`), select: target.machine, row: target.row };
    case "room":
      return { ...floor, select: target.bloc };
    case "projet":
      return { ...floor, select: PROJECT_SETTINGS, row: target.row };
    case "etape": {
      const journey = model.parcours.find((j) => j.id === target.journey);
      const room = journey ? followedRoom(journeyStations(model, journey)[target.step - 1], enterable(model)) : null;
      return { ...floor, node: room ? levelNode(`part:${room}`) : floor.node, journey: target.journey, step: target.step };
    }
    case "code":
      return { ...floor, node: target.path, select: target.lines ? `line:${target.lines[0]}-${target.lines[1]}` : null };
    case "doute":
      return { ...floor, row: `doute:${target.index}` };
  }
}

/** Ctrl K: anything the study names, in the reader's own words, then any file or function of the code. */
export function CommandPalette({ projectId, model, open, onOpenChange }: Props) {
  const [query, setQuery] = useState("");
  const [hits, setHits] = useState<SearchHit[]>([]);
  const index = useMemo(() => (model ? buildIndex(model) : []), [model]);
  const groups = useMemo(() => searchIndex(index, query), [index, query]);

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        onOpenChange(!open);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onOpenChange]);

  useEffect(() => {
    setHits([]); // results of the previous query must never be opened by Enter
    if (query.trim().length < 2) return;
    let current = true;
    const timer = window.setTimeout(() => {
      api.search(projectId, query).then((found) => current && setHits(found), () => current && setHits([]));
    }, WAIT_MS);
    return () => {
      current = false;
      window.clearTimeout(timer);
    };
  }, [projectId, query]);

  const go = (target: Omit<Route, "projectId">) => {
    onOpenChange(false);
    setQuery("");
    navigate({ projectId, ...target });
  };
  const group = "[&_[cmdk-group-heading]]:px-3 [&_[cmdk-group-heading]]:py-1.5 [&_[cmdk-group-heading]]:text-[12px] [&_[cmdk-group-heading]]:text-faint";
  const item = "flex cursor-pointer flex-col gap-0.5 rounded-md px-3 py-2 text-[13.5px] data-[selected=true]:bg-raised";

  return (
    <Command.Dialog
      open={open}
      onOpenChange={onOpenChange}
      label="Chercher dans le projet" // cmdk names both the dialog and its input with it
      shouldFilter={false}
      loop
      overlayClassName="fixed inset-0 z-40 bg-black/40"
      contentClassName="fixed top-[12vh] left-1/2 z-50 w-[min(680px,calc(100vw-32px))] -translate-x-1/2 overflow-hidden rounded-xl border border-line bg-panel shadow-[0_24px_60px_rgba(0,0,0,0.35)]"
    >
      <Command.Input
        value={query}
        onValueChange={setQuery}
        placeholder="Vos mots : « nom du client », « port », « je veux changer »…"
        className="w-full border-b border-line-soft bg-transparent px-4 py-3.5 text-[15px] text-ink outline-none placeholder:text-faint"
      />
      <Command.List className="max-h-[min(480px,64vh)] overflow-y-auto p-2">
        <Command.Empty className="px-3 py-6 text-center text-[13px] text-muted">
          {query.trim().length < 2 ? "Tapez au moins deux lettres : un nom, un mot de l'interface, un mot du code." : "Rien trouvé avec ces mots."}
        </Command.Empty>
        {model &&
          groups.map((g) => (
            <Command.Group key={g.kind} heading={g.results.length > PER_GROUP ? `${g.title} (+${g.results.length - PER_GROUP})` : g.title} className={group}>
              {g.results.slice(0, PER_GROUP).map((r) => (
                <Command.Item key={r.key} value={r.key} className={item} onSelect={() => go(landing(model, r.target))}>
                  <span className="flex min-w-0 items-baseline gap-2">
                    <span className="line-clamp-2 text-ink">{r.label}</span>
                    {r.note && <span className="shrink-0 text-[12px] text-lamp-ink">{r.note}</span>}
                  </span>
                  {r.detail && (
                    // The code a setting is about may be long: two lines, cut anywhere, never its key word lost to « … ».
                    <span className={`line-clamp-2 text-[12px] text-muted ${g.kind === "reglage" || g.kind === "changer" || g.kind === "code" ? "font-mono [overflow-wrap:anywhere]" : ""}`}>{r.detail}</span>
                  )}
                  <span className="truncate text-[11.5px] text-faint">{r.address}</span>
                </Command.Item>
              ))}
            </Command.Group>
          ))}
        {hits.length > 0 && (
          <Command.Group heading="Dans le code (noms exacts)" className={group}>
            {hits.map((hit) => (
              <Command.Item
                key={hit.key}
                value={`code:${hit.key}`}
                className="flex cursor-pointer items-center gap-3 rounded-md px-3 py-2 text-[13.5px] data-[selected=true]:bg-raised"
                onSelect={() => go({ node: hit.level, expand: true, select: hit.key, journey: null, step: null, row: null })}
              >
                <span className="w-20 shrink-0 text-[12px] text-faint">{KIND_LABEL[hit.kind]}</span>
                <span className="truncate">{hit.label}</span>
                {hit.path && <span className="ml-auto truncate font-mono text-[11.5px] text-faint">{hit.path}</span>}
              </Command.Item>
            ))}
          </Command.Group>
        )}
      </Command.List>
    </Command.Dialog>
  );
}
