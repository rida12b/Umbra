import { useEffect, useState } from "react";
import { api, type Project, type Turn } from "./api";
import { useLive } from "./live";
import { Command, StateMessage } from "./ui";

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

  if (turns === null) return <StateMessage>Lecture de l'activité…</StateMessage>;
  if (turns.length === 0)
    return (
      <StateMessage title="Aucune activité de Claude pour l'instant">
        <p>
          Installez le plugin Umbra dans Claude Code. Chaque demande, les fichiers modifiés et la réponse de Claude
          apparaîtront ici.
        </p>
        <Command>claude plugin marketplace add rida12b/rida-skills{"\n"}claude plugin install umbra@rida-skills</Command>
        <p className="text-[13px] text-faint">Puis ouvrez une nouvelle session Claude Code dans ce projet.</p>
      </StateMessage>
    );
  return (
    <div className="h-full overflow-y-auto">
      <ol className="mx-auto max-w-3xl px-6 py-6">
        {turns.map((turn) => (
          <li key={`${turn.session}-${turn.started}`} className="border-b border-line-soft py-5 first:pt-0">
            <p className="text-[12px] text-faint">
              <time dateTime={turn.started}>{new Date(turn.started).toLocaleString("fr-FR")}</time>
              <span className="ml-3">session {turn.session.slice(0, 8)}</span>
              {!turn.ended && <span className="ml-3 text-lamp-ink">en cours</span>}
            </p>
            <p className="mt-1.5 text-[15px] leading-snug text-ink">
              {turn.prompt || <span className="text-muted">Demande non vue : la session avait déjà commencé.</span>}
            </p>
            {turn.files.length > 0 && (
              <ul className="mt-2.5 flex flex-wrap gap-1.5" aria-label="Fichiers modifiés">
                {turn.files.map((file) => (
                  <li key={file}>
                    <span className="rounded border border-line bg-panel px-2 py-0.5 font-mono text-[12px] text-ink">{file}</span>
                  </li>
                ))}
              </ul>
            )}
            {turn.message && <FinalMessage text={turn.message} />}
          </li>
        ))}
      </ol>
    </div>
  );
}

const LONG = 420;

/** Claude's final answer, folded when long: the list stays readable, the whole text one click away. */
function FinalMessage({ text }: { text: string }) {
  const [open, setOpen] = useState(false);
  const long = text.length > LONG;
  return (
    <div className="mt-2.5 border-l-2 border-line pl-3 text-[13.5px] text-muted">
      <p className={`whitespace-pre-line ${long && !open ? "line-clamp-4" : ""}`}>{text}</p>
      {long && (
        <button type="button" className="mt-1 text-[12.5px] text-ink underline decoration-line underline-offset-[3px]" onClick={() => setOpen(!open)}>
          {open ? "Replier" : "Lire toute la réponse"}
        </button>
      )}
    </div>
  );
}
