import { useState } from "react";
import type { Explanation, Located } from "../api";
import { HypothesisNote, SectionTitle } from "../ui";
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
  if (explanation === null) return <p className="mt-4 text-[13px] text-faint">Lecture de l'explication…</p>;
  const { card, state } = explanation;
  const writing = state === "queued" || state === "working";
  if (!card) {
    if (writing) return <p className="mt-4 text-[13px] text-muted">Claude Code lit le code et écrit l'explication (environ 30 s)…</p>;
    return <p className="mt-4 text-[13px] text-danger">Pas d'explication : {explanation.message ?? "raison inconnue"}</p>;
  }
  const titles = TITLES[explanation.level ?? ""] ?? DEFAULT_TITLES;
  return (
    <section className="mt-5 border-t border-line-soft pt-1">
      <p className="mt-3 text-[14px] text-ink">{card.role}</p>
      <List title={titles.entrees} items={card.entrees} />
      <List title={titles.sorties} items={card.sorties} />
      {card.etapes.length > 0 && (
        <>
          <SectionTitle>{titles.etapes}</SectionTitle>
          <ol className="list-decimal space-y-1.5 pl-5 text-[13px] text-muted">
            {card.etapes.map((step, index) => (
              <Step key={index} projectId={projectId} step={step} defaultFile={defaultFile} />
            ))}
          </ol>
        </>
      )}
      {card.points_entree.length > 0 && (
        <>
          <SectionTitle>Où ça commence</SectionTitle>
          <ul className="list-disc space-y-1.5 pl-5 text-[13px] text-muted">
            {card.points_entree.map((entry, index) => (
              <Step key={index} projectId={projectId} step={entry} defaultFile={defaultFile} />
            ))}
          </ul>
        </>
      )}
      <List title="S'appuie sur" items={card.depend_de} />
      <List title="Ce qu'on ne peut pas savoir d'ici" items={card.incertitudes} />
      <HypothesisNote>
        Expliqué par Claude Code{explanation.created_at ? ` le ${explanation.created_at.slice(0, 10)}` : ""}.
        {state === "stale" && " Le code a changé depuis : mise à jour demandée."}
        {writing && " Mise à jour en cours…"}
        {state === "error" && ` Mise à jour impossible : ${explanation.message}`}
      </HypothesisNote>
    </section>
  );
}

function List({ title, items }: { title: string; items: string[] }) {
  if (items.length === 0) return null;
  return (
    <>
      <SectionTitle>{title}</SectionTitle>
      <ul className="list-disc space-y-1 pl-5 text-[13px] text-muted">
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
      {file && step.lignes && !open && (
        <button type="button" className="ml-1.5 font-mono text-[12px] text-faint hover:text-ink" onClick={() => setOpen(true)}>
          l. {step.lignes[0]}–{step.lignes[1]}
        </button>
      )}
      {open && file && step.lignes && (
        <EvidenceItem projectId={projectId} source={{ file, start: step.lignes[0], end: step.lignes[1] }} onClose={() => setOpen(false)} />
      )}
    </li>
  );
}
