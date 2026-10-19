import type { ModelState } from "../api";
import { useModel } from "../model";

/** While there is no model yet: what is happening, in plain words. */
export function ModelPending({ state }: { state: ModelState | null }) {
  if (state?.state === "error") {
    return (
      <div className="state">
        <p className="error-text">L'étude du projet a échoué : {state.message}</p>
      </div>
    );
  }
  return (
    <div className="state">
      <p className="writing">Claude Code étudie le projet : il lit la carte, suit les parcours et écrit le modèle.</p>
      <p className="muted">Une seule fois, quelques minutes. Ensuite, chaque modification ne relit que ce qui a changé.</p>
    </div>
  );
}

/** "Studied on …; 2 files changed, update in progress." */
export function ModelStatusLine() {
  const state = useModel();
  if (!state?.model) return null;
  const updating = state.state === "queued" || state.state === "working";
  return (
    <p className="card-footer">
      <span className="badge badge-hypothesis">Hypothèse</span> Étudié par Claude Code
      {state.created_at ? ` le ${state.created_at.slice(0, 10)} à ${state.created_at.slice(11, 16)}` : ""}.
      {state.changed.length > 0 && ` ${state.changed.length} fichier(s) modifié(s) depuis`}
      {updating ? " : mise à jour en cours…" : state.changed.length > 0 ? "." : ""}
      {state.state === "error" && ` Mise à jour impossible : ${state.message}`}
    </p>
  );
}
