import { useEffect, useState } from "react";
import { api, type Project, type Turn } from "./api";
import { useLive } from "./live";
import { navigate } from "./route";

/** What Claude Code did in this Project, turn by turn: the prompt, the files it changed, its answer. */
export function ActivityView({ project }: { project: Project }) {
  const [turns, setTurns] = useState<Turn[] | null>(null);
  const { revision } = useLive(); // a new hook event or a changed file: read again

  useEffect(() => {
    let current = true;
    api.activity(project.id).then((found) => current && setTurns(found), () => current && setTurns([]));
    return () => {
      current = false;
    };
  }, [project.id, revision]);

  if (turns === null) return <div className="state">Lecture de l'activité…</div>;
  if (turns.length === 0)
    return (
      <div className="state">
        <h1>Aucune activité de Claude pour l'instant</h1>
        <p>Installez le plugin Umbra dans Claude Code : chaque demande, les fichiers modifiés et la réponse de Claude apparaîtront ici.</p>
        <pre className="command">/plugin marketplace add &lt;dossier Umbra&gt;{"\n"}/plugin install umbra@umbra</pre>
      </div>
    );
  return (
    <ol className="activity">
      {turns.map((turn) => (
        <li key={`${turn.session}-${turn.started}`} className="turn">
          <p className="turn-time muted">
            {new Date(turn.started).toLocaleString()} · session {turn.session.slice(0, 8)}
            {!turn.ended && " · en cours"}
          </p>
          <p className="turn-prompt">{turn.prompt || "(demande non vue : session déjà commencée)"}</p>
          {turn.files.length > 0 && (
            <ul className="turn-files">
              {turn.files.map((file) => (
                <li key={file}>
                  <button
                    className="link-button code-link"
                    onClick={() => navigate({ projectId: project.id, node: file, expand: false })}
                  >
                    {file}
                  </button>
                </li>
              ))}
            </ul>
          )}
          {turn.message && <p className="turn-message">{turn.message}</p>}
        </li>
      ))}
    </ol>
  );
}
