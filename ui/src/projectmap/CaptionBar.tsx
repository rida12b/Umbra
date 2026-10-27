import type { Highlight } from "../api";

interface Props {
  highlight: Highlight;
  step: number | null; // the step the path is on (an action's path starts at 1)
  onMove: (forward: boolean) => void;
  onCopy: () => void;
  onClear: () => void;
}

/** One bar above the lit map. A question asked in Claude Code (mock p-question.png): the question,
 * « copier pour Claude » (the files, ready for an agent) and « effacer ». An action's path traced in the
 * code (mock p-chemin.png): the action, « tracé automatiquement », the step it is on with ← →. */
export function CaptionBar({ highlight, step, onMove, onCopy, onClear }: Props) {
  const path = highlight.kind === "path";
  const at = path ? highlight.steps.find((s) => s.n === step) : undefined;
  return (
    <section className="pm-caption" aria-label={path ? "Chemin tracé dans le code" : "Question posée dans Claude Code"}>
      <div className="what">
        <span className="kind">{path ? "Chemin" : "Question"}</span>
        <span className="q">{path ? highlight.caption : quoted(highlight.caption)}</span>
        {path ? (
          <span className="tag" title="Suivi automatique des appels dans le code, sans IA">
            tracé automatiquement
          </span>
        ) : (
          <span className="tag">posée dans Claude Code</span>
        )}
        {at && (
          <span className="step" title={at.why || undefined}>
            <b>
              Étape {at.n} sur {highlight.steps.length}
            </b>
            {GAP}
            {at.note}
            {GAP}
            <span className="mono">{at.label}</span>
            {at.guess && <span className="guess"> supposé</span>}
          </span>
        )}
      </div>
      {path && (
        <>
          <button type="button" className="pm-btn icon" aria-label="Étape précédente" onClick={() => onMove(false)}>
            ←
          </button>
          <button type="button" className="pm-btn icon" aria-label="Étape suivante" onClick={() => onMove(true)}>
            →
          </button>
        </>
      )}
      <button type="button" className="pm-btn primary" onClick={onCopy}>
        copier pour Claude
      </button>
      <button type="button" className="pm-btn" onClick={onClear}>
        effacer
      </button>
    </section>
  );
}

const NBSP = " ";
const GAP = ` ${NBSP}`; // as the mock: « Étape 3 sur 5 &nbsp;vérifie la connexion &nbsp;deps.py:30 »

/** French quotes with no-break spaces: « ? » never ends alone on the next line (narrow screens). */
export function quoted(caption: string): string {
  return `«${NBSP}${caption.trim().replace(/ (?=[?!:;])/g, NBSP)}${NBSP}»`;
}
