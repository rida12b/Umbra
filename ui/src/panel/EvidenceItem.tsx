import { useEffect, useState } from "react";
import { api, type Claim, type Excerpt } from "../api";

type Loaded = { claim: Claim | null; excerpt: Excerpt } | { error: string } | null;

interface Props {
  projectId: string;
  /** A Claim key, or a plain file location when the element has no Claim of its own (a Module). */
  source: { claim: string } | { file: string; start: number; end: number };
}

export function shortVersion(version: string): string {
  return version.startsWith("worktree:") ? `uncommitted (${version.slice(9, 17)})` : version.slice(0, 10);
}

/** One piece of Evidence: what is claimed, where, from which version, and the guarded lines. */
export function EvidenceItem({ projectId, source }: Props) {
  const [loaded, setLoaded] = useState<Loaded>(null);
  const sourceKey = "claim" in source ? source.claim : `${source.file}:${source.start}`;

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

  if (loaded === null) return <div className="evidence muted">Reading evidence…</div>;
  if ("error" in loaded) return <div className="evidence error-text">Evidence unavailable: {loaded.error}</div>;
  const { claim, excerpt } = loaded;
  return (
    <figure className="evidence">
      {claim && (
        <div className="evidence-claim">
          <span className={`badge badge-${claim.status}`}>{claim.status}</span>{" "}
          <code>{claim.relation}</code> <span className="evidence-object">{claim.object}</span>
        </div>
      )}
      <figcaption className="evidence-where">
        <span className="evidence-file">
          {excerpt.file}:{excerpt.start}
          {excerpt.end !== excerpt.start ? `–${excerpt.end}` : ""}
        </span>
        <span className="muted">{shortVersion(excerpt.version)}</span>
      </figcaption>
      {!excerpt.current && (
        <div className="warning">The file changed since indexing: these lines may have moved.</div>
      )}
      <pre className="excerpt">
        {excerpt.lines.map((line, index) => {
          const number = excerpt.first_line + index;
          const cited = number >= excerpt.start && number <= excerpt.end;
          return (
            <div key={number} className={cited ? "line cited" : "line"}>
              <span className="line-number">{number}</span>
              <span className="line-text">{line || " "}</span>
            </div>
          );
        })}
      </pre>
    </figure>
  );
}
