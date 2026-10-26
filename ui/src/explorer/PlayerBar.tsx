import { Play, SkipForward, X } from "lucide-react";
import type { ReactNode } from "react";
import { useEffect } from "react";
import type { Journey } from "../api";
import { stepLabel } from "../arch/story";
import { stepsWord, type Station, type StepGroup } from "./stations";

interface Props {
  journey: Journey;
  step: number; // 1-based
  station: Station | null;
  group: StepGroup | null; // a long journey: the phase or room the step is in
  onStep: (step: number) => void;
  onStop: () => void;
  onOpenFile: (path: string, lines: [number, number] | null) => void;
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
    <section className="border-t-2 border-lamp-line bg-panel px-5 py-2 max-sm:px-3" aria-label="Chemin de données en lecture">
      <div className="flex items-center gap-4 max-sm:gap-2">
        {/* As in mockup A (V65): three square buttons, then the step in words. */}
        <div className="flex shrink-0 gap-1.5">
          <Square label="Étape précédente" disabled={step <= 1} onClick={() => onStep(step - 1)}>
            <Play size={16} className="rotate-180 fill-current" />
          </Square>
          <Square label="Étape suivante" disabled={step >= last} onClick={() => onStep(step + 1)}>
            <Play size={16} className="fill-current" />
          </Square>
          <Square label="Dernière étape" disabled={step >= last} onClick={() => onStep(last)} wide>
            <SkipForward size={16} className="fill-current" />
          </Square>
        </div>
        <div className="min-w-0 flex-1">
          {/* Where the step sits first (step, then its group), the journey's name last: the panel already says it. */}
          <p className="text-[13px] text-faint sm:truncate">
            étape {step} sur {last}
            {group && (
              <>
                {" "}· <span className="text-muted">{group.title}</span> ({stepsWord(group)})
              </>
            )}
            <span className="max-sm:hidden"> · {journey.nom}</span>
          </p>
          <p className="line-clamp-2 text-[16px] leading-snug max-sm:text-[15px]">
            <span className="mr-2 inline-flex size-6 items-center justify-center rounded-full bg-lamp text-[13px] font-bold text-on-lamp">{step}</span>
            <b>{stepLabel(current)}</b>
            <span className="text-muted"> — {current.simple || current.texte}</span>
          </p>
          <p className="mt-0.5 flex flex-wrap items-baseline gap-x-3 text-[13px]">
            {station?.note && <span className="text-lamp-ink">{station.note}</span>}
            {station?.manual && station.machine && <span className="text-ok">fait par une personne</span>}
            {current.fichier && (
              <button
                type="button"
                onClick={() => onOpenFile(current.fichier!, current.lignes)}
                title={`Ouvrir ${current.fichier}${lines}`}
                aria-label={`${current.fichier}${lines}`}
                className="flex max-w-full min-w-0 font-mono text-[12px] text-fl-service hover:underline"
              >
                {/* The path may be cut, never the lines; a phone shows the file's name only. */}
                <span className="truncate max-sm:hidden">{current.fichier}</span>
                <span className="truncate sm:hidden">{current.fichier.split("/").pop()}</span>
                <span className="shrink-0 whitespace-pre">{lines}</span>
              </button>
            )}
          </p>
        </div>
        <button type="button" onClick={onStop} className="rounded-lg p-2 text-muted hover:bg-raised" aria-label="Arrêter le chemin">
          <X size={18} />
        </button>
      </div>
    </section>
  );
}

/** `wide`: only where there is room (not on a phone, where the step's words need the width). */
function Square({ label, disabled, onClick, children, wide = false }: { label: string; disabled: boolean; onClick: () => void; children: ReactNode; wide?: boolean }) {
  return (
    <button type="button" onClick={onClick} disabled={disabled} aria-label={label} title={label} className={`flex size-10 items-center justify-center rounded-lg border border-line text-ink hover:bg-raised disabled:opacity-30 max-sm:size-9 ${wide ? "max-sm:hidden" : ""}`}>
      {children}
    </button>
  );
}
