import type { ProjectModel } from "../api";
import { machinePlate, projectPlate, roomPlate } from "./plateData";
import { Check, CodeLink, Empty, Fait, Items, PlateFrame, SeenList, SettingRow, Slot, type OpenCode, type Play } from "./plateParts";

// The plate (#79, inventaire V67-V75): the same slots in the same order for every machine, so the reader looks in
// the same place every time. A slot without data says so in one line; it is never hidden and never guessed.

export type { OpenCode } from "./plateParts";

/** What an empty slot means: an older study never asked for it, or the study found nothing there. */
const empty = (oldMethod: boolean, found: string) =>
  oldMethod ? "pas encore dans le modèle — relancer l'étude (nouvelle méthode)" : found;

export function MachinePlateView({ model, id, oldMethod, row, onPlay, onOpenCode, onEnter }: {
  model: ProjectModel; id: string; oldMethod: boolean; row: string | null; onPlay: Play; onOpenCode: OpenCode; onEnter: (() => void) | null;
}) {
  const plate = machinePlate(model, id);
  if (!plate) return null;
  return (
    <PlateFrame path={`${plate.room} › ${plate.title}`} title={plate.title} onEnter={onEnter}>
      <Slot label="Fait">
        <Fait fait={plate.fait} detail={plate.detail} />
        {plate.mots.length > 0 && (
          <p className="mt-2 text-[12.5px] text-muted">
            <span className="text-faint">Mots : </span>
            {plate.mots.map((m, i) => (
              <span key={m.simple}>
                {i > 0 && " · "}
                {m.simple} = <code className="fl-codechip">{m.code}</code>
              </span>
            ))}
          </p>
        )}
      </Slot>
      <Slot label="Reçoit">{plate.recoit ? <Items list={plate.recoit} /> : <Empty text={empty(oldMethod, "Rien n'entre d'après l'étude.")} />}</Slot>
      <Slot label="Rend">{plate.rend ? <Items list={plate.rend} /> : <Empty text={empty(oldMethod, "Rien ne sort d'après l'étude.")} />}</Slot>
      <Slot label="Réglages">
        {plate.reglages ? (
          <ul className="flex flex-col">
            {plate.reglages.map((r, i) => (
              <SettingRow key={i} nom={r.nom} code={r.code} cited={r} onOpenCode={onOpenCode} lit={r.code === row}>
                {r.effet && <span className="text-[12.5px] leading-snug text-muted">{r.effet}</span>}
              </SettingRow>
            ))}
          </ul>
        ) : (
          <Empty text={empty(oldMethod, "L'étude n'a trouvé aucun réglage pour cette machine.")} />
        )}
      </Slot>
      <Slot label="Où">
        {plate.ou.length > 0 ? (
          <ul className="flex flex-col gap-2">
            {plate.ou.map((o, i) => (
              <li key={i} className="flex min-w-0 flex-col items-start gap-0.5 text-[13.5px]">
                <code className="fl-codechip">{o.quoi}</code>
                <span className="flex max-w-full min-w-0 flex-wrap items-baseline gap-x-2">
                  <CodeLink cited={o} onOpenCode={onOpenCode} />
                  <Check cited={o} />
                </span>
              </li>
            ))}
          </ul>
        ) : (
          <Empty text="Le modèle ne cite aucune fonction pour cette machine." />
        )}
        {plate.fichiers.length > 0 && (
          <p className="mt-2 text-[12.5px] text-faint">
            Fichiers :{" "}
            {plate.fichiers.map((f, i) => (
              <span key={f}>
                {i > 0 && ", "}
                <button type="button" onClick={() => onOpenCode(f, null)} className="text-left font-mono text-fl-service hover:underline [overflow-wrap:anywhere]">
                  {f}
                </button>
              </span>
            ))}
          </p>
        )}
      </Slot>
      <Slot label="Vu dans">
        <SeenList seen={plate.vuDans} onPlay={onPlay} />
      </Slot>
    </PlateFrame>
  );
}

/** A room's plate: the same frame; its machines take the place of the settings. */
export function RoomPlateView({ model, bloc, oldMethod, onPlay, onOpenMachine, onEnter }: {
  model: ProjectModel; bloc: string; oldMethod: boolean; onPlay: Play; onOpenMachine: (bloc: string, machine: string) => void; onEnter: (() => void) | null;
}) {
  const plate = roomPlate(model, bloc);
  if (!plate) return null;
  return (
    <PlateFrame path={`L'usine › ${plate.title}`} title={plate.title} onEnter={onEnter}>
      <Slot label="Fait">
        <Fait fait={plate.fait} detail={plate.detail} />
      </Slot>
      <Slot label="Reçoit">{plate.recoit ? <Items list={plate.recoit} /> : <Empty text={empty(oldMethod, "Rien n'entre d'après l'étude.")} />}</Slot>
      <Slot label="Rend">{plate.rend ? <Items list={plate.rend} /> : <Empty text={empty(oldMethod, "Rien ne sort d'après l'étude.")} />}</Slot>
      <Slot label="Machines">
        {plate.machines.length > 0 ? (
          <ul className="flex flex-col gap-1">
            {plate.machines.map((m) => (
              <li key={m.id}>
                {/* Opens the room with this machine's plate, from the floor as well as inside the room. */}
                <button type="button" onClick={() => onOpenMachine(bloc, m.id)} className="text-left text-[14px] hover:underline">
                  <span className="text-ink">{m.nom}</span> <span className="text-muted">— {m.words}</span>
                </button>
              </li>
            ))}
          </ul>
        ) : (
          <Empty text="Pas de machine étudiée dans cette pièce." />
        )}
      </Slot>
      <Slot label="Vu dans">
        <SeenList seen={plate.vuDans} onPlay={onPlay} withMachine />
      </Slot>
    </PlateFrame>
  );
}

/** The project's own settings (V18's card): which file, which value, and whether any code reads it. */
export function ProjectPlateView({ model, row, onOpenCode }: { model: ProjectModel; row: string | null; onOpenCode: OpenCode }) {
  const rows = projectPlate(model);
  return (
    <PlateFrame path="L'usine › Réglages du projet" title="Réglages du projet" onEnter={null}>
      {rows.some((r) => r.notRead) && (
        // Dry run of #81: the first place a reader looks for Q5; say where the setting that counts is.
        <p className="mt-3 rounded-lg border border-line-soft px-3 py-2 text-[13px] leading-snug text-muted">
          Les lignes « lu par le code : non » ne changent rien. Le réglage que le code lit est sur la fiche d'une machine : cherchez son nom avec Ctrl K (par exemple « port » ou « en-tête »).
        </p>
      )}
      <Slot label="Réglages">
        {rows.length > 0 ? (
          <ul className="flex flex-col">
            {rows.map((r, i) => (
              <SettingRow key={i} nom={r.nom} code={r.code} cited={r} onOpenCode={onOpenCode} lit={r.code === row}>
                {r.notRead && <span className="text-[12.5px] text-lamp-ink">lu par le code : non — changer cette valeur ne change rien pour l'instant</span>}
              </SettingRow>
            ))}
          </ul>
        ) : (
          <Empty text="L'étude n'a trouvé aucun réglage de projet." />
        )}
      </Slot>
    </PlateFrame>
  );
}
