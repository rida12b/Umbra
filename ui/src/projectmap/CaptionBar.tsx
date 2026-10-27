/** One bar above the lit map (mock p-question.png): the question asked in Claude Code, « copier pour Claude »
 * (the files, ready for an agent) and « effacer » (back to the plain map). ← → move along the numbered steps. */
export function CaptionBar({ caption, onCopy, onClear }: { caption: string; onCopy: () => void; onClear: () => void }) {
  return (
    <section className="pm-caption" aria-label="Question posée dans Claude Code">
      <div className="what">
        <span className="kind">Question</span>
        <span className="q">{quoted(caption)}</span>
        <span className="tag">posée dans Claude Code</span>
      </div>
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

/** French quotes with no-break spaces: « ? » never ends alone on the next line (narrow screens). */
export function quoted(caption: string): string {
  return `«${NBSP}${caption.trim().replace(/ (?=[?!:;])/g, NBSP)}${NBSP}»`;
}
