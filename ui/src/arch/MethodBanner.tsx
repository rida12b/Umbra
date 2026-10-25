import { useState } from "react";
import { api, type ModelState } from "../api";

/**
 * The model on screen was written by an older study method (#78). It stays shown; studying the project
 * again spends the user's Claude Code subscription, so only this button does it, and it says so first.
 */
export function MethodBanner({ projectId, state }: { projectId: string; state: ModelState | null }) {
  const [sent, setSent] = useState(false);
  const [failed, setFailed] = useState<string | null>(null);
  if (!state?.methode_ancienne) return null;
  const running = sent || state.state === "queued" || state.state === "working";
  const error = failed ?? (state.state === "error" && !running ? state.message : null);
  const relaunch = () => {
    setFailed(null);
    setSent(true);
    api.relaunchStudy(projectId).then(
      () => undefined,
      (reason: Error) => {
        setSent(false);
        setFailed(reason.message);
      },
    );
  };
  return (
    <section
      aria-label="Nouvelle méthode d'étude"
      className="flex flex-wrap items-center gap-x-4 gap-y-2 border-b border-line-soft bg-raised px-5 py-2.5 text-[14px]"
    >
      <p className="min-w-0 flex-1 basis-[28rem] leading-snug">
        <strong className="font-semibold">Nouvelle méthode d'étude disponible.</strong>{" "}
        {running
          ? "Claude Code étudie le projet avec la nouvelle méthode : quelques minutes. Le modèle actuel reste affiché jusqu'à la fin."
          : "Le modèle affiché vient de l'ancienne méthode : il ne dit pas encore ce qui entre, sort et se règle dans chaque pièce. Relancer lit tout le projet une fois avec Claude Code, sur votre abonnement (quelques minutes)."}
        {error && <span className="mt-1 block text-danger">L'étude n'a pas pu se faire : {error}</span>}
      </p>
      {!running && (
        <button type="button" onClick={relaunch} className="shrink-0 rounded-lg bg-ink px-3.5 py-1.5 font-medium text-bg hover:opacity-90">
          {error ? "Réessayer" : "Relancer l'étude"}
        </button>
      )}
    </section>
  );
}
