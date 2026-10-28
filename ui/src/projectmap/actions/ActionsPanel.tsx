import { useEffect, useState } from "react";
import { api, type Action, type ActionList } from "../../api";
import { commonAddress, shortAddress } from "../card/addresses";
import { useActions } from "./useActions";

interface Props {
  projectId: string;
  name: string; // the repo: « sqlite-utils »
  onClose: () => void;
}

/** « Ce qu'on peut faire » (ADR-0007, #107, prototype state p-actions): the addresses the server accepts,
 * or the commands of the CLI, grouped by file. A click lights the action's path traced in the code. */
export function ActionsPanel({ projectId, name, onClose }: Props) {
  const state = useActions(projectId, true);
  const [failed, setFailed] = useState<string | null>(null);

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (event.key !== "Escape") return;
      event.stopImmediatePropagation(); // Esc closes the panel first, before anything on the map
      onClose();
    };
    window.addEventListener("keydown", onKey, true);
    return () => window.removeEventListener("keydown", onKey, true);
  }, [onClose]);

  const pick = (action: Action) => {
    setFailed(null);
    // The engine lights it on every open tab (as a `show`); the map opens where the path is drawn.
    api.showAction(projectId, action.id).then(onClose, (error: Error) => setFailed(`Le chemin n'a pas pu être tracé : ${error.message}`));
  };
  const list = state.kind === "ready" ? state.list : null;
  const commands = list ? list.groups.every((g) => g.kind === "commands") : false;
  return (
    <aside className="pm-panel" aria-label="Ce qu'on peut faire">
      <div className="hd">
        <h3>
          Ce qu'on peut faire {list && <span className="n">{list.total}</span>}
          <button type="button" className="pm-btn" onClick={onClose}>
            fermer
          </button>
        </h3>
        <div className="sub">
          {commands ? (
            <>
              Les commandes de <span className="mono">{name}</span>, lues dans {readIn(list)}. Noms en français lus dans leur nom, la commande à taper à côté. Clic : voir le chemin.
            </>
          ) : (
            "Les adresses que le serveur accepte, rangées par fichier. Noms en français lus dans le code, l'adresse exacte au survol. Clic : voir le chemin."
          )}
        </div>
        {failed && (
          <p role="alert" className="err">
            {failed}
          </p>
        )}
      </div>
      {state.kind === "loading" && <p className="wait">Lecture des actions…</p>}
      {state.kind === "failed" && <p className="wait err">La lecture a échoué : {state.message}</p>}
      {list && <Groups list={list} onPick={pick} />}
      {list && list.total === 0 && <p className="wait">Ni adresse de serveur ni commande lue dans le code.</p>}
    </aside>
  );
}

/** « cli.py »: the file the commands are read in, or « le code » when they are spread over several. */
function readIn(list: ActionList | null): string {
  const files = list ? list.groups.map((g) => g.file.split("/").pop() ?? g.file) : [];
  return files.length === 1 && files[0] ? files[0] : "le code";
}

function Groups({ list, onPick }: { list: ActionList; onPick: (action: Action) => void }) {
  const under = commonAddress(list.groups.flatMap((g) => g.actions.filter((a) => a.kind === "routes").map((a) => a.address)));
  return (
    <>
      {list.groups.map((group) => {
        const file = group.file.split("/").pop() ?? group.file;
        const count = group.actions.length;
        // « items · 5 » as the mock reads; a file of commands: « 47 commandes »
        const said = group.kind === "commands" ? `${count} ${count > 1 ? "commandes" : "commande"}` : `${group.role || "adresses"} · ${count}`;
        return (
          <section key={group.file} className="grp" aria-label={`${file} : ${said}`}>
            <div className="gh" title={group.file}>
              <b>{file}</b>
              <span>{said}</span>
            </div>
            {group.actions.map((action) => (
              // A route: « POST Créer un item », its address on hover. A command (#108): « Créer une table »,
              // the command as typed always beside it (it is what one types, and a phone has no hover);
              // one no rule names shows as typed.
              <button key={action.id} type="button" className={action.verb ? "act" : "act cmd"} title={action.verb ? `${action.verb} ${action.address}` : `${file}:${action.line}`} onClick={() => onPick(action)}>
                {action.verb && <span className="m">{action.verb}</span>}
                {action.label ? <span className="lab">{action.label}</span> : <span className="lab mono">{action.verb ? shortAddress(action.address, under) : action.address}</span>}
                {action.label && <span className="rt">{action.address}</span>}
                <span className="go">chemin →</span>
              </button>
            ))}
          </section>
        );
      })}
    </>
  );
}
