import { ChevronLeft, ChevronRight, X } from "lucide-react";
import { useEffect } from "react";
import type { Journey } from "../api";
import { stepLabel } from "../arch/story";
import type { Station, StepGroup } from "./stations";

interface Props {
  journey: Journey;
  step: number; // 1-based
  station: Station | null;
  group: StepGroup | null; // a long journey: the phase or room the step is in
  onStep: (step: number) => void;
  onStop: () => void;
  onOpenFile: (path: string) => void;
}

/** The data path being played (V65): its step in words, under the map, with previous and next. */
export function PlayerBar({ journey, step, station, group, onStep, onStop, onOpenFile }: Props) {
  const current = journey.etapes[step - 1];
  const last = journey.etapes.length;

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (event.altKey || event.ctrlKey || event.metaKey) return;
      if (event.target instanceof HTMLElement && event.target.closest("input, textarea, select, [contenteditable], [cmdk-root]")) return;
      if (event.key === "ArrowRight" && step < last) onStep(step + 1);
      else if (event.key === "ArrowLeft" && step > 1) onStep(step - 1);
      else return;
      event.preventDefault();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [step, last, onStep]);

  if (!current) return null;
  const lines = current.lignes ? ` l.${current.lignes[0]}-${current.lignes[1]}` : "";
  return (
    <section className="border-t-2 border-lamp-line bg-panel px-5 py-3 max-sm:px-3" aria-label="Chemin de données en lecture">
      <div className="flex items-center gap-4 max-sm:gap-2">
        <button
          type="button"
          onClick={() => onStep(step - 1)}
          disabled={step <= 1}
          className="rounded-lg border border-line p-2 hover:bg-raised disabled:opacity-30"
          aria-label="Étape précédente"
        >
          <ChevronLeft size={20} />
        </button>
        <div className="min-w-0 flex-1">
          <p className="truncate text-[13px] text-faint">
            {journey.nom} · étape {step} sur {last}
            {group && (
              <>
                {" "}· <span className="text-muted">{group.title}</span> · étapes {group.from}–{group.to}
              </>
            )}
          </p>
          <p className="text-[18px] leading-snug max-sm:text-[15px]">
            <span className="mr-2 inline-flex size-7 items-center justify-center rounded-full bg-lamp text-[14px] font-bold text-on-lamp">{step}</span>
            <b>{stepLabel(current)}</b>
            <span className="text-muted"> — {current.simple || current.texte}</span>
          </p>
          <p className="mt-0.5 flex flex-wrap items-baseline gap-x-3 text-[13px]">
            {station?.note && <span className="text-lamp-ink">{station.note}</span>}
            {station?.manual && station.machine && <span className="text-ok">fait par une personne</span>}
            {current.fichier && (
              <button
                type="button"
                onClick={() => onOpenFile(current.fichier!)}
                title="Ouvrir ce fichier"
                className="max-w-full truncate font-mono text-[12px] text-fl-service hover:underline"
              >
                {current.fichier}
                {lines}
              </button>
            )}
          </p>
        </div>
        {step < last ? (
          <button
            type="button"
            onClick={() => onStep(step + 1)}
            className="rounded-lg bg-ink px-4 py-2 text-[15px] font-medium text-bg hover:opacity-90 max-sm:px-2.5"
            aria-label="Étape suivante"
          >
            <span className="flex items-center gap-1">
              <span className="max-sm:sr-only">Suivante</span> <ChevronRight size={18} aria-hidden="true" />
            </span>
          </button>
        ) : (
          <button type="button" onClick={onStop} className="rounded-lg bg-ink px-4 py-2 text-[15px] font-medium text-bg hover:opacity-90 max-sm:px-2.5">
            Terminer
          </button>
        )}
        <button type="button" onClick={onStop} className="rounded-lg p-2 text-muted hover:bg-raised" aria-label="Arrêter le chemin">
          <X size={18} />
        </button>
      </div>
    </section>
  );
}
