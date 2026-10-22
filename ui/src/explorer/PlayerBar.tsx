import { ChevronLeft, ChevronRight, X } from "lucide-react";
import { useEffect } from "react";
import type { Journey } from "../api";
import { stepLabel } from "../arch/story";
import type { StepOnMap } from "./track";

interface Props {
  journey: Journey;
  step: number; // 1-based
  where: StepOnMap | null;
  onStep: (step: number) => void;
  onStop: () => void;
  onEnterElsewhere: () => void;
}

/** The data path being played: its step in words, under the map, with previous and next. */
export function PlayerBar({ journey, step, where, onStep, onStop, onEnterElsewhere }: Props) {
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
  return (
    <section className="border-t-2 border-lamp-line bg-panel px-5 py-3" aria-label="Chemin de données en lecture">
      <div className="flex items-center gap-4">
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
          </p>
          <p className="text-[18px] leading-snug">
            <span className="mr-2 inline-flex size-7 items-center justify-center rounded-full bg-lamp text-[14px] font-bold text-on-lamp">
              {step}
            </span>
            <b>{stepLabel(current)}</b>
            <span className="text-muted"> — {current.simple || current.texte}</span>
          </p>
          {where && where.boxes.length === 0 && (
            <p className="mt-1 text-[13.5px] text-faint">Cette étape ne touche aucune pièce visible à ce niveau.</p>
          )}
          {where?.elsewhere && (
            <button type="button" onClick={onEnterElsewhere} className="mt-1 text-[13.5px] text-lamp-ink hover:underline">
              Elle se passe dans « {where.elsewhere.title} » : entrer pour la voir de près
            </button>
          )}
        </div>
        {step < last ? (
          <button
            type="button"
            onClick={() => onStep(step + 1)}
            className="rounded-lg bg-ink px-4 py-2 text-[15px] font-medium text-bg hover:opacity-90"
            aria-label="Étape suivante"
          >
            <span className="flex items-center gap-1">
              Suivante <ChevronRight size={18} aria-hidden="true" />
            </span>
          </button>
        ) : (
          <button type="button" onClick={onStop} className="rounded-lg bg-ink px-4 py-2 text-[15px] font-medium text-bg hover:opacity-90">
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
