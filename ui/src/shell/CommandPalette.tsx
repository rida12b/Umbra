import { Command } from "cmdk";
import { useEffect, useState } from "react";
import { api, type ProjectModel, type SearchHit } from "../api";
import { KIND_LABEL } from "../map/ElementNode";
import { levelNode } from "../explorer/Explorer";
import { ARCHITECTURE_VIEW, navigate } from "../route";
import { steps } from "../ui";

const WAIT_MS = 200;
const MAX_LOCAL = 6;

interface Props {
  projectId: string;
  model: ProjectModel | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

/** Accents and case do not count: "etude" finds "Étude". */
function plain(text: string): string {
  return text.normalize("NFD").replace(/\p{Diacritic}/gu, "").toLowerCase();
}

/** Ctrl K: jump to a journey, a block of the architecture, or any file or function of the code. */
export function CommandPalette({ projectId, model, open, onOpenChange }: Props) {
  const [query, setQuery] = useState("");
  const [hits, setHits] = useState<SearchHit[]>([]);

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

  const wanted = plain(query.trim());
  const matches = (text: string) => wanted === "" || plain(text).includes(wanted);
  // A path is found by its name, by the words of its steps (opened at that step) or of its other cases.
  const journeys = (model?.parcours ?? [])
    .flatMap((journey) => {
      const step = journey.etapes.findIndex((s) => matches(`${s.action ?? ""} ${s.simple ?? ""} ${s.texte}`));
      const other = (journey.branches ?? []).some((b) => matches(`${b.quand} ${b.alors}`));
      if (matches(journey.nom)) return [{ journey, step: 1, why: "" }];
      if (step >= 0) return [{ journey, step: step + 1, why: `étape ${step + 1}` }];
      return other ? [{ journey, step: 1, why: "cas particulier" }] : [];
    })
    .slice(0, MAX_LOCAL);
  const blocks = (model?.blocs ?? []).filter((b) => matches(`${b.nom} ${b.en_bref ?? ""} ${b.role}`)).slice(0, MAX_LOCAL);

  const go = (target: Parameters<typeof navigate>[0]) => {
    onOpenChange(false);
    setQuery("");
    navigate(target);
  };
  const group = "[&_[cmdk-group-heading]]:px-3 [&_[cmdk-group-heading]]:py-1.5 [&_[cmdk-group-heading]]:text-[12px] [&_[cmdk-group-heading]]:text-faint";
  const item = "flex cursor-pointer items-center gap-3 rounded-md px-3 py-2 text-[13.5px] data-[selected=true]:bg-raised";

  return (
    <Command.Dialog
      open={open}
      onOpenChange={onOpenChange}
      label="Chercher dans le projet" // cmdk names both the dialog and its input with it
      shouldFilter={false}
      loop
      overlayClassName="fixed inset-0 z-40 bg-black/40"
      contentClassName="fixed top-[12vh] left-1/2 z-50 w-[min(640px,calc(100vw-32px))] -translate-x-1/2 overflow-hidden rounded-xl border border-line bg-panel shadow-[0_24px_60px_rgba(0,0,0,0.35)]"
    >
      <Command.Input
        value={query}
        onValueChange={setQuery}
        placeholder="Un chemin, une pièce, un fichier, un mot (« erreur », « limite »)…"
        className="w-full border-b border-line-soft bg-transparent px-4 py-3.5 text-[15px] text-ink outline-none placeholder:text-faint"
      />
      <Command.List className="max-h-[min(420px,60vh)] overflow-y-auto p-2">
        <Command.Empty className="px-3 py-6 text-center text-[13px] text-muted">
          {wanted.length < 2 ? "Tapez au moins deux lettres pour chercher dans le code." : "Rien trouvé sous ce nom."}
        </Command.Empty>
        {journeys.length > 0 && (
          <Command.Group heading="Chemins de données" className={group}>
            {journeys.map(({ journey, step, why }) => (
              <Command.Item
                key={journey.id}
                value={`parcours:${journey.id}`}
                className={item}
                onSelect={() => go({ projectId, node: ARCHITECTURE_VIEW, expand: false, journey: journey.id, step })}
              >
                <span className="flex-1 truncate">{journey.nom}</span>
                <span className="text-[12px] text-faint">{why || steps(journey.etapes.length)}</span>
              </Command.Item>
            ))}
          </Command.Group>
        )}
        {blocks.length > 0 && (
          <Command.Group heading="Pièces du projet" className={group}>
            {blocks.map((block) => (
              <Command.Item
                key={block.id}
                value={`bloc:${block.id}`}
                className={item}
                onSelect={() => go({ projectId, node: levelNode(`part:${block.id}`), expand: false })} // inside the part: found even when grouped
              >
                <span className="flex-1 truncate">{block.nom}</span>
              </Command.Item>
            ))}
          </Command.Group>
        )}
        {hits.length > 0 && (
          <Command.Group heading="Code" className={group}>
            {hits.map((hit) => (
              <Command.Item
                key={hit.key}
                value={`code:${hit.key}`}
                className={item}
                onSelect={() => go({ projectId, node: hit.level, expand: true, select: hit.key })}
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
