import { ChevronRight, Play } from "lucide-react";
import type { ReactNode } from "react";
import type { Cited, ProjectModel } from "../api";
import { machinePlate, projectPlate, roomPlate, type Item, type Seen } from "./plateData";

// The plate (#79, inventaire V67-V75): the same slots in the same order for every machine, so the reader looks in
// the same place every time. A slot without data says so in one line; it is never hidden and never guessed.

export type OpenCode = (path: string, line: number | null) => void;
const NOT_YET = "pas encore dans le modèle — relancer l'étude (nouvelle méthode)";

export function MachinePlateView({ model, id, onPlay, onOpenCode, onEnter }: {
  model: ProjectModel; id: string; onPlay: (journey: string, step: number) => void; onOpenCode: OpenCode; onEnter: (() => void) | null;
}) {
  const plate = machinePlate(model, id);
  if (!plate) return null;
  return (
    <PlateFrame path={`${plate.room} ›`} title={plate.title} onEnter={onEnter}>
      <Slot label="Fait">
        <p className="text-[16px] leading-snug font-bold text-ink">{plate.fait}</p>
        {plate.detail && <p className="mt-1 text-[13px] leading-relaxed text-muted">{plate.detail}</p>}
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
      <Slot label="Reçoit">{plate.recoit ? <Items list={plate.recoit} /> : <Empty />}</Slot>
      <Slot label="Rend">{plate.rend ? <Items list={plate.rend} /> : <Empty />}</Slot>
      <Slot label="Réglages">
        {plate.reglages ? (
          <ul className="flex flex-col">
            {plate.reglages.map((r, i) => (
              // V73: name and file:line, the exact code, the effect, the check.
              <li key={i} className="flex flex-col gap-1 border-t border-line-soft py-2 first:border-t-0 first:pt-0">
                <span className="flex items-baseline justify-between gap-3">
                  <span className="text-[14px] text-ink">{r.nom}</span>
                  <CodeLink cited={r} onOpenCode={onOpenCode} short />
                </span>
                <code className="fl-codechip self-start">{r.code}</code>
                {r.effet && <span className="text-[12.5px] leading-snug text-muted">{r.effet}</span>}
                <Check cited={r} />
              </li>
            ))}
          </ul>
        ) : (
          <Empty />
        )}
      </Slot>
      <Slot label="Où">
        {plate.ou.length > 0 ? (
          <ul className="flex flex-col gap-2">
            {plate.ou.map((o, i) => (
              <li key={i} className="flex flex-col items-start gap-0.5 text-[13.5px]">
                <code className="fl-codechip">{o.quoi}</code>
                <span className="flex flex-wrap items-baseline gap-x-2">
                  <CodeLink cited={o} onOpenCode={onOpenCode} />
                  <Check cited={o} />
                </span>
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-[13px] text-faint">Le modèle ne cite aucune fonction pour cette machine.</p>
        )}
        {plate.fichiers.length > 0 && (
          <p className="mt-2 text-[12.5px] text-faint">
            Fichiers :{" "}
            {plate.fichiers.map((f, i) => (
              <span key={f}>
                {i > 0 && ", "}
                <button type="button" onClick={() => onOpenCode(f, null)} className="font-mono text-fl-service hover:underline [overflow-wrap:anywhere]">
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
export function RoomPlateView({ model, bloc, onPlay, onSelect, onEnter }: {
  model: ProjectModel; bloc: string; onPlay: (journey: string, step: number) => void; onSelect: (id: string) => void; onEnter: (() => void) | null;
}) {
  const plate = roomPlate(model, bloc);
  if (!plate) return null;
  return (
    <PlateFrame path="L'usine ›" title={plate.title} onEnter={onEnter}>
      <Slot label="Fait">
        <p className="text-[16px] leading-snug font-bold text-ink">{plate.fait}</p>
        {plate.detail && <p className="mt-1 text-[13px] leading-relaxed text-muted">{plate.detail}</p>}
      </Slot>
      <Slot label="Reçoit">{plate.recoit ? <Items list={plate.recoit} /> : <Empty />}</Slot>
      <Slot label="Rend">{plate.rend ? <Items list={plate.rend} /> : <Empty />}</Slot>
      <Slot label="Machines">
        {plate.machines.length > 0 ? (
          <ul className="flex flex-col gap-1">
            {plate.machines.map((m) => (
              <li key={m.id}>
                <button type="button" onClick={() => onSelect(m.id)} className="text-left text-[14px] hover:underline">
                  <span className="text-ink">{m.nom}</span> <span className="text-muted">— {m.words}</span>
                </button>
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-[13px] text-faint">Pas de machine étudiée dans cette pièce.</p>
        )}
      </Slot>
      <Slot label="Vu dans">
        <SeenList seen={plate.vuDans} onPlay={onPlay} withMachine />
      </Slot>
    </PlateFrame>
  );
}

/** The project's own settings (V18's card): which file, which value, and whether any code reads it. */
export function ProjectPlateView({ model, onOpenCode }: { model: ProjectModel; onOpenCode: OpenCode }) {
  const rows = projectPlate(model);
  return (
    <PlateFrame path="L'usine ›" title="Réglages du projet" onEnter={null}>
      <Slot label="Réglages">
        {rows.length > 0 ? (
          <ul className="flex flex-col">
            {rows.map((r, i) => (
              <li key={i} className="flex flex-col gap-1 border-t border-line-soft py-2 first:border-t-0 first:pt-0">
                <span className="flex items-baseline justify-between gap-3">
                  <span className="text-[14px] text-ink">{r.nom}</span>
                  <CodeLink cited={r} onOpenCode={onOpenCode} short />
                </span>
                <code className="fl-codechip self-start">{r.code}</code>
                {r.notRead && <span className="text-[12.5px] text-lamp-ink">lu par le code : non — changer cette valeur ne change rien pour l'instant</span>}
                <Check cited={r} />
              </li>
            ))}
          </ul>
        ) : (
          <Empty />
        )}
      </Slot>
    </PlateFrame>
  );
}

function PlateFrame({ path, title, onEnter, children }: { path: string; title: string; onEnter: (() => void) | null; children: ReactNode }) {
  return (
    <div className="px-6 pt-6 pb-10" aria-label={`Fiche : ${title}`}>
      <p className="text-[13px] text-faint">{path}</p>
      <h2 className="mt-0.5 text-[20px] leading-tight font-bold">{title}</h2>
      {onEnter && (
        <button type="button" onClick={onEnter} className="mt-3 flex items-center gap-1 rounded-lg border border-line px-3 py-1.5 text-[14px] hover:bg-raised">
          Entrer dedans <ChevronRight size={15} aria-hidden="true" />
        </button>
      )}
      <div className="mt-3 flex flex-col">{children}</div>
    </div>
  );
}

function Slot({ label, children }: { label: string; children: ReactNode }) {
  return (
    <section className="border-t border-line-soft py-3 first:border-t-0" aria-label={label}>
      <h3 className="mb-1.5 text-[11px] font-semibold tracking-[0.08em] text-faint uppercase">{label}</h3>
      {children}
    </section>
  );
}

function Items({ list }: { list: Item[] }) {
  return (
    <ul className="flex flex-col gap-1 text-[14px] leading-snug">
      {list.map((item, i) => (
        <li key={i} className={item.refusal ? "text-fl-refus" : "text-ink"}>
          {item.text}
        </li>
      ))}
    </ul>
  );
}

const Empty = () => <p className="text-[13px] text-faint">{NOT_YET}</p>;

/** ✓ when Umbra found the cited lines in the file; ? when it did not: a hypothesis of the model. */
function Check({ cited }: { cited: Cited }) {
  return cited.verifie ? (
    <span className="text-[12px] font-medium text-ok">✓ trouvé dans le fichier</span>
  ) : (
    <span className="text-[12px] font-medium text-lamp-ink" title="Umbra n'a pas trouvé ce fichier ou ces lignes">
      ? hypothèse : pas trouvé dans le fichier
    </span>
  );
}

function CodeLink({ cited, onOpenCode, short = false }: { cited: Cited; onOpenCode: OpenCode; short?: boolean }) {
  if (!cited.fichier) return null;
  const lines = cited.lignes ? (cited.lignes[0] === cited.lignes[1] ? `:${cited.lignes[0]}` : `:${cited.lignes[0]}-${cited.lignes[1]}`) : "";
  const shown = short ? cited.fichier.split("/").pop() : cited.fichier;
  return (
    <button
      type="button"
      onClick={() => onOpenCode(cited.fichier!, cited.lignes?.[0] ?? null)}
      title={`Ouvrir ${cited.fichier}${lines}`}
      aria-label={`${cited.fichier}${lines}`}
      className="shrink-0 text-left font-mono text-[12px] text-fl-service hover:underline [overflow-wrap:anywhere]"
    >
      {shown}
      {lines}
    </button>
  );
}

function SeenList({ seen, onPlay, withMachine = false }: { seen: Seen[]; onPlay: (journey: string, step: number) => void; withMachine?: boolean }) {
  if (seen.length === 0) return <p className="text-[13px] text-faint">Aucun trajet ne passe ici.</p>;
  return (
    <ul className="flex flex-col gap-1.5">
      {seen.map((s) => (
        <li key={`${s.journey}:${s.step}`}>
          {/* V75: a click plays the journey from this step. */}
          <button type="button" onClick={() => onPlay(s.journey, s.step)} className="flex w-full items-start gap-2 rounded-lg border border-line px-3 py-2 text-left text-[13.5px] leading-snug hover:bg-raised">
            <span className="mt-1 h-1 w-3 shrink-0 rounded-full bg-fl-data" aria-hidden="true" />
            <span className="min-w-0">
              {s.nom} · étape {s.step} — <span className="font-semibold">{s.action}</span>
              {withMachine && s.where && <span className="block text-[12px] text-faint">sur « {s.where} »</span>}
            </span>
            <Play size={13} className="mt-1 ml-auto shrink-0 text-fl-data" aria-hidden="true" />
          </button>
        </li>
      ))}
    </ul>
  );
}
