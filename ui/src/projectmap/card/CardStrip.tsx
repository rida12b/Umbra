import type { CardFunction, CardLine, Proof } from "../../api";
import type { CardState } from "./useCard";
import { commonAddress, shortAddress } from "./addresses";
import { vscodeLink } from "./vscode";

/** Level 2 (ADR-0007, #106, mock p-items.png): the card under the map, on the same screen. Its name and
 * « ouvrir le code », the four lines, then the functions, each opening VS Code at its line. Nothing below. */
export function CardStrip({ state, root }: { state: CardState; root: string }) {
  if (state.kind === "closed" || state.kind === "none") return null;
  if (state.kind === "loading")
    return (
      <section className="pm-card pm-card-wait" aria-busy="true">
        Lecture de la carte…
      </section>
    );
  if (state.kind === "failed")
    return (
      <section className="pm-card pm-card-wait" role="alert">
        La lecture de la carte a échoué : <span className="font-mono text-[12.5px] text-danger">{state.message}</span>
      </section>
    );
  const { card } = state;
  const files = new Set(card.functions.map((f) => f.file));
  const total = card.functions.length + card.more;
  const under = commonAddress(card.functions.map((f) => f.path).filter(Boolean)); // said once in « Reçoit »
  return (
    <section className="pm-card" aria-label={`Carte de ${card.title}`}>
      <div className="pm-card-id">
        <h2 className={card.file ? "mono" : undefined}>{card.title}</h2>
        <div className="path">{card.path}</div>
        <a className="pm-btn pm-link" href={vscodeLink(root, card.open_file, 1)} title={`Ouvre ${card.open_file} dans VS Code`}>
          ouvrir le code
        </a>
      </div>
      <dl className="pm-four">
        {card.lines.map((line) => (
          <div key={line.label} title={proofText(line.proofs)}>
            <dt>{line.label}</dt>
            <dd>{line.words.length ? <Words line={line} /> : <span className="none">rien lu dans le code</span>}</dd>
          </div>
        ))}
      </dl>
      <div className="pm-card-fns">
        <h3 className="sec">
          {card.section}
          {total > 5 && <span className="count"> ({total})</span>}
        </h3>
        {card.functions.length ? (
          <ul className="acts">
            {card.functions.map((fn) => (
              <li key={`${fn.file}:${fn.line}:${fn.name}`}>
                <FunctionRow fn={fn} root={root} many={files.size > 1} under={under} />
              </li>
            ))}
            {card.more > 0 && <li className="more">+ {card.more} autres, dans le code</li>}
          </ul>
        ) : (
          <p className="none">Aucune fonction lue dans ce fichier.</p>
        )}
      </div>
    </section>
  );
}

function Words({ line }: { line: CardLine }) {
  return (
    <>
      {line.words.map((word, i) => {
        const title = [word.inferred ? "supposé : déduit, pas lu tel quel" : "", word.hint].filter(Boolean).join(" · ");
        const className = [word.mono ? "mono" : "", word.inferred ? "guess" : ""].filter(Boolean).join(" ");
        return (
          <span key={i}>
            {i > 0 && " "}
            <span className={className || undefined} title={title || undefined}>
              {word.text}
            </span>
          </span>
        );
      })}
    </>
  );
}

/** « GET  Lister les items  read_items · l.14 »; a route of another shape shows its address; any other
 * function its name and line (and its file when the part has several). */
function FunctionRow({ fn, root, many, under }: { fn: CardFunction; root: string; many: boolean; under: string }) {
  const file = fn.file.split("/").pop() ?? fn.file;
  const where = many ? `${file} · l.${fn.line}` : `l.${fn.line}`;
  const route = Boolean(fn.verb);
  return (
    <a className="act" href={vscodeLink(root, fn.file, fn.line)} title={`${fn.path || fn.name} — ouvre ${fn.file}:${fn.line} dans VS Code`}>
      {route && <span className="m">{fn.verb}</span>}
      {fn.label ? <span className="lab">{fn.label}</span> : <span className="lab mono">{route ? shortAddress(fn.path, under) : fn.name}</span>}
      <span className="fn">{route && fn.name !== fn.path ? `${fn.name} · ${where}` : where}</span>
    </a>
  );
}

function proofText(proofs: Proof[]): string | undefined {
  if (!proofs.length) return undefined;
  return `lu dans ${proofs.map((p) => (p.start ? `${p.file}:${p.start}` : p.file)).join(", ")}`;
}

export function cardTitle(state: CardState): string | null {
  return state.kind === "ready" ? state.card.title : null;
}
