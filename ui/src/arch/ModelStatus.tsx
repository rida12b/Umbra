import type { ModelState } from "../api";
import { useModel } from "../model";
import { HypothesisNote, StateMessage } from "../ui";

/** While there is no model yet: what is happening, in plain words. */
export function ModelPending({ state }: { state: ModelState | null }) {
  if (state?.state === "error")
    return (
      <StateMessage title="L'étude du projet a échoué">
        <p className="text-danger">{state.message}</p>
        <p className="mt-2">Vérifiez que Claude Code est connecté (commande `claude`), puis rechargez la page.</p>
      </StateMessage>
    );
  return (
    <StateMessage title="Claude Code étudie le projet">
      <p>Il lit la carte du code, suit les parcours de bout en bout et écrit le modèle.</p>
      <p className="mt-2 text-faint">Une seule fois, quelques minutes. Ensuite, chaque modification ne relit que ce qui a changé.</p>
    </StateMessage>
  );
}

/** "Studied on …; 2 files changed, update in progress." */
export function ModelStatusLine() {
  const state = useModel();
  if (!state?.model) return null;
  const updating = state.state === "queued" || state.state === "working";
  const when = state.created_at ? ` le ${state.created_at.slice(0, 10)} à ${state.created_at.slice(11, 16)}` : "";
  return (
    <HypothesisNote>
      Écrit par Claude Code{when} à partir du code.
      {state.changed.length > 0 && ` ${state.changed.length} fichier(s) modifié(s) depuis`}
      {updating ? " : mise à jour en cours…" : state.changed.length > 0 ? "." : ""}
      {state.state === "error" && ` Mise à jour impossible : ${state.message}`}
    </HypothesisNote>
  );
}
