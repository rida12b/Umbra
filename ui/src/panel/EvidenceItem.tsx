import { useEffect, useState } from "react";
import { api, type Claim, type Excerpt } from "../api";

type Loaded = { claim: Claim | null; excerpt: Excerpt } | { error: string } | null;

interface Props {
  projectId: string;
  /** A Claim key, or a plain file location when the element has no Claim of its own (a Module). */
  source: { claim: string } | { file: string; start: number; end: number };
  onClose?: () => void;
}

export function shortVersion(version: string): string {
  return version.startsWith("worktree:") ? `non commité (${version.slice(9, 17)})` : version.slice(0, 10);
}

const STATUS_WORD: Record<string, string> = { fact: "Fait", hypothesis: "Hypothèse", declaration: "Déclaré" };

/** One piece of Evidence: what is claimed, where, from which version, and the guarded lines. */
export function EvidenceItem({ projectId, source, onClose }: Props) {
  const [loaded, setLoaded] = useState<Loaded>(null);
  const sourceKey = "claim" in source ? source.claim : `${source.file}:${source.start}:${source.end}`;

  useEffect(() => {
    let current = true;
    setLoaded(null);
    (async () => {
      const claim = "claim" in source ? await api.claim(projectId, source.claim) : null;
      const where = claim
        ? { file: claim.file, start: claim.line_start, end: claim.line_end }
        : (source as { file: string; start: number; end: number });
      const excerpt = await api.evidence(projectId, where.file, where.start, where.end);
      return { claim, excerpt };
    })()
      .then((result) => current && setLoaded(result))
      .catch((error: Error) => current && setLoaded({ error: error.message }));
    return () => {
      current = false;
    };
  }, [projectId, sourceKey]); // `source` is a new object on each render: `sourceKey` identifies it

  // Esc closes the open excerpt before anything else on the page reacts to it (going up a level).
  useEffect(() => {
    if (!onClose) return;
    const onKey = (event: KeyboardEvent) => {
      if (event.key !== "Escape") return;
      if (event.target instanceof HTMLElement && event.target.closest("[cmdk-root]")) return; // the search closes first
      event.stopImmediatePropagation();
      onClose();
    };
    window.addEventListener("keydown", onKey, true);
    return () => window.removeEventListener("keydown", onKey, true);
  }, [onClose]);

  if (loaded === null) return <div className="mt-2 text-[12px] text-faint">Lecture du code…</div>;
  if ("error" in loaded) return <div className="mt-2 text-[12px] text-danger">Code indisponible : {loaded.error}</div>;
  const { claim, excerpt } = loaded;
  return (
    <figure className="mt-2 overflow-hidden rounded-md border border-line">
      <figcaption className="flex items-center gap-3 border-b border-line-soft bg-panel px-3 py-1.5 text-[12px]">
        <span className="min-w-0 truncate font-mono text-muted">
          {excerpt.file}:{excerpt.start}
          {excerpt.end !== excerpt.start ? `–${excerpt.end}` : ""}
        </span>
        <span className="ml-auto shrink-0 text-faint">{shortVersion(excerpt.version)}</span>
        {onClose && (
          <button type="button" className="shrink-0 text-faint hover:text-ink" onClick={onClose}>
            Masquer
          </button>
        )}
      </figcaption>
      {claim && (
        <p className="border-b border-line-soft px-3 py-1.5 text-[12px] text-muted">
          <span className="mr-1.5 rounded border border-line px-1.5 py-px">{STATUS_WORD[claim.status] ?? claim.status}</span>
          <code className="font-mono">{claim.relation}</code> {claim.object}
        </p>
      )}
      {!excerpt.current && (
        <p className="border-b border-line-soft px-3 py-1.5 text-[12px] text-danger">
          Le fichier a changé depuis l'indexation : ces lignes ont pu bouger.
        </p>
      )}
      <pre className="excerpt">
        {excerpt.lines.map((line, index) => {
          const number = excerpt.first_line + index;
          return (
            <div key={number} className="excerpt-line" data-cited={number >= excerpt.start && number <= excerpt.end}>
              <span className="excerpt-number">{number}</span>
              <span>{line || " "}</span>
            </div>
          );
        })}
      </pre>
    </figure>
  );
}
