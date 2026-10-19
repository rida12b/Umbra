import { useState } from "react";
import type { Explanation, Located } from "../api";
import { EvidenceItem } from "./EvidenceItem";

interface Props {
  projectId: string;
  explanation: Explanation | null;
  /** File of the element, used when a step names no file (a step inside the shown module). */
  defaultFile: string | null;
}

// Each kind of element is read in its own terms: a document has key points, tests check things.
const TITLES: Record<string, { entrees: string; sorties: string; etapes: string }> = {
  doc: { entrees: "Ce qui entre", sorties: "Ce qui sort", etapes: "Ce que dit ce document" },
  test: { entrees: "Les situations testées", sorties: "Ce qui est vérifié", etapes: "Les scénarios" },
};
const DEFAULT_TITLES = { entrees: "Ce qui entre", sorties: "Ce qui sort", etapes: "Ce qui se passe" };

/** The card first: what it is for, what goes in and out, what happens. Code only on demand. */
export function ExplanationCard({ projectId, explanation, defaultFile }: Props) {
  if (explanation === null) return <p className="muted">Lecture de l'explication…</p>;
  const { card, state } = explanation;
  const writing = state === "queued" || state === "working";
  if (!card) {
    if (writing) return <p className="writing">Claude Code lit le code et écrit l'explication (environ 30 s)…</p>;
    return <p className="error-text">Pas d'explication : {explanation.message ?? "inconnue"}</p>;
  }
  const titles = TITLES[explanation.level ?? ""] ?? DEFAULT_TITLES;
  return (
    <section className="card">
      <p className="card-role">{card.role}</p>
      <List title={titles.entrees} items={card.entrees} />
      <List title={titles.sorties} items={card.sorties} />
      {card.etapes.length > 0 && (
        <>
          <h3 className="card-title">{titles.etapes}</h3>
          <ol className="card-steps">
            {card.etapes.map((step, index) => (
              <Step key={index} projectId={projectId} step={step} defaultFile={defaultFile} />
            ))}
          </ol>
        </>
      )}
      {card.points_entree.length > 0 && (
        <>
          <h3 className="card-title">Où ça commence</h3>
          <ul className="card-list">
            {card.points_entree.map((entry, index) => (
              <Step key={index} projectId={projectId} step={entry} defaultFile={defaultFile} />
            ))}
          </ul>
        </>
      )}
      <List title="S'appuie sur" items={card.depend_de} />
      <List title="Ce qu'on ne peut pas savoir d'ici" items={card.incertitudes} muted />
      <p className="card-footer">
        <span className="badge badge-hypothesis">Hypothèse</span> Expliqué par Claude Code
        {explanation.created_at ? ` le ${explanation.created_at.slice(0, 10)}` : ""}.
        {state === "stale" && " Le code a changé depuis : mise à jour demandée."}
        {writing && " Mise à jour en cours…"}
        {state === "error" && ` Mise à jour impossible : ${explanation.message}`}
      </p>
    </section>
  );
}

function List({ title, items, muted }: { title: string; items: string[]; muted?: boolean }) {
  if (items.length === 0) return null;
  return (
    <>
      <h3 className="card-title">{title}</h3>
      <ul className={`card-list${muted ? " muted" : ""}`}>
        {items.map((item, index) => (
          <li key={index}>{item}</li>
        ))}
      </ul>
    </>
  );
}

function Step({ projectId, step, defaultFile }: { projectId: string; step: Located; defaultFile: string | null }) {
  const [open, setOpen] = useState(false);
  const file = step.fichier ?? defaultFile;
  return (
    <li>
      {step.texte}
      {file && step.lignes && (
        <button className="link-button" onClick={() => setOpen(!open)}>
          {open ? "masquer le code" : `voir le code (l. ${step.lignes[0]}–${step.lignes[1]})`}
        </button>
      )}
      {open && file && step.lignes && (
        <EvidenceItem projectId={projectId} source={{ file, start: step.lignes[0], end: step.lignes[1] }} />
      )}
    </li>
  );
}
