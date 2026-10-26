import { type PageModelState, useModel } from "../model";
import { HypothesisNote, StateMessage } from "../ui";

// What the engine's refusal means for the reader, and what to do: never « check Claude Code » here.
const FAILURE = {
  unreachable: { title: "Umbra ne répond pas", hint: "Vérifiez que le moteur Umbra tourne (umbra-engine serve), puis réessayez." },
  read: { title: "Umbra n'a pas pu lire le projet", hint: "Souvent un fichier bloqué ou un dossier déplacé un instant. Réessayez : Umbra relit le projet." },
  other: { title: "Umbra n'a pas pu ouvrir le projet", hint: "Réessayez ; si cela revient, le message ci-dessus dit pourquoi." },
} as const;

/** While there is no model yet: what is happening, in plain words. */
export function ModelPending({ state }: { state: PageModelState | null }) {
  if (state?.state === "error" && state.failure) {
    const { title, hint } = FAILURE[state.failure];
    return (
      <StateMessage title={title}>
        <p className="text-danger">{state.message}</p>
        <p className="mt-2">{hint}</p>
        {state.retry && (
          <button type="button" onClick={state.retry} className="mt-3 rounded-md border border-line px-3 py-1.5 text-[14px] hover:bg-panel">
            Réessayer
          </button>
        )}
      </StateMessage>
    );
  }
  if (state?.state === "indexing")
    return (
      <StateMessage title="Umbra lit le projet">
        <p>Il passe chaque fichier au gardien des secrets, puis repère les fonctions et leurs liens.</p>
        <p className="mt-2 text-faint">Quelques secondes. Ensuite, Claude Code étudie le projet.</p>
      </StateMessage>
    );
  if (state?.state === "error")
    return (
      <StateMessage title="L'étude du projet a échoué">
        <p className="text-danger">{state.message}</p>
        <p className="mt-2">Vérifiez que Claude Code est connecté (commande `claude`), puis rechargez la page.</p>
      </StateMessage>
    );
  if (state === null) return <StateMessage>Ouverture du projet…</StateMessage>; // not asked yet: no study is running
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
