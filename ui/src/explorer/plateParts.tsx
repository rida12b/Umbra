import { ChevronRight } from "lucide-react";
import { useId, useLayoutEffect, useRef, type ReactNode } from "react";
import type { Cited } from "../api";
import type { Item, Seen } from "./plateData";

// The pieces every plate is made of (#79, inventaire V67-V75): the frame, a slot, a settings row, the ✓/? check, a
// file:line link, the list of journey steps. Shared by the machine, room and project plates (Plate.tsx).

export type OpenCode = (path: string, lines: [number, number] | null) => void;
export type Play = (journey: string, step: number) => void;

export function PlateFrame({ path, title, onEnter, children }: { path: string; title: string; onEnter: (() => void) | null; children: ReactNode }) {
  const heading = useId();
  return (
    <section className="px-6 pt-6 pb-10" aria-labelledby={heading} data-plate={title}>
      {/* V67: the room, then the machine. */}
      <p className="text-[13px] text-faint">{path}</p>
      <h2 id={heading} className="mt-0.5 text-[20px] leading-tight font-bold">
        {title}
      </h2>
      {onEnter && (
        <button type="button" onClick={onEnter} className="mt-3 flex items-center gap-1 rounded-lg border border-line px-3 py-1.5 text-[14px] hover:bg-raised">
          Entrer dedans <ChevronRight size={15} aria-hidden="true" />
        </button>
      )}
      <div className="mt-3 flex flex-col border-t border-line-soft">{children}</div>
    </section>
  );
}

/** One slot (V69): a small-caps label, a rule between two slots. A plain block: six slots are not six landmarks. */
export function Slot({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="border-t border-line-soft py-3 first:border-t-0" data-slot={label}>
      <h3 className="mb-1.5 text-[11px] font-semibold tracking-[0.08em] text-faint uppercase">{label}</h3>
      {children}
    </div>
  );
}

export function Fait({ fait, detail }: { fait: string; detail: string }) {
  return (
    <>
      <p className="text-[16px] leading-snug font-bold text-ink">{fait}</p>
      {detail && <p className="mt-1 text-[13px] leading-relaxed text-muted">{detail}</p>}
    </>
  );
}

/** V73: the setting's name and file:line, the exact code, then what the row adds, then the check. */
export function SettingRow({ nom, code, cited, onOpenCode, children, lit = false }: {
  nom: string; code: string; cited: Cited; onOpenCode: OpenCode; children: ReactNode; lit?: boolean;
}) {
  // A search landed here (#80): the row is framed in yellow and brought into view.
  const here = useRef<HTMLLIElement>(null);
  useLayoutEffect(() => {
    if (lit) here.current?.scrollIntoView({ block: "center" });
  }, [lit]);
  return (
    <li
      ref={here}
      aria-current={lit ? "true" : undefined}
      className={`flex min-w-0 flex-col gap-1 border-t border-line-soft py-2 first:border-t-0 first:pt-0 ${lit ? "-mx-2 rounded-lg px-2 ring-2 ring-fl-hl" : ""}`}
    >
      <span className="flex items-baseline justify-between gap-3">
        <span className="text-[14px] text-ink">{nom}</span>
        <CodeLink cited={cited} onOpenCode={onOpenCode} short />
      </span>
      {/* The whole path (dry run of #81): « config.py » alone does not say which of the project's config files. */}
      {cited.fichier && <span className="-mt-0.5 font-mono text-[11.5px] text-faint [overflow-wrap:anywhere]">{cited.fichier}</span>}
      <code className="fl-codechip self-start">{code}</code>
      {children}
      <Check cited={cited} />
    </li>
  );
}

export function Items({ list }: { list: Item[] }) {
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

export const Empty = ({ text }: { text: string }) => <p className="text-[13px] text-faint">{text}</p>;

/** V73, V74: ✓ when Umbra found the cited lines in the file; ? when it did not: a hypothesis of the model. */
export function Check({ cited }: { cited: Cited }) {
  return cited.verifie ? (
    <span className="text-[12px] font-medium text-ok" title="Umbra a retrouvé ces lignes dans le fichier">
      ✓ vérifié
    </span>
  ) : (
    <span className="text-[12px] font-medium text-lamp-ink" title="Umbra n'a pas retrouvé ce fichier ou ces lignes : à confirmer dans le code">
      ? hypothèse
    </span>
  );
}

/** A cited place: « tenant_auth.py:33 » in a settings row (V73), « watchdog_ai/…/tenant_auth.py l.25-40 » in Où (V74). */
export function CodeLink({ cited, onOpenCode, short = false }: { cited: Cited; onOpenCode: OpenCode; short?: boolean }) {
  if (!cited.fichier) return null;
  const [a, b] = cited.lignes ?? [0, 0];
  const span = a === b ? `${a}` : `${a}-${b}`;
  const lines = !cited.lignes ? "" : short ? `:${span}` : ` l.${span}`;
  return (
    <button
      type="button"
      onClick={() => onOpenCode(cited.fichier!, cited.lignes)}
      title={`Ouvrir ${cited.fichier}${lines}`}
      aria-label={`${cited.fichier}${lines}`}
      className={`max-w-full min-w-0 text-left font-mono text-[12px] text-fl-service hover:underline [overflow-wrap:anywhere] ${short ? "shrink-0" : ""}`}
    >
      {short ? cited.fichier.split("/").pop() : cited.fichier}
      <span className="whitespace-nowrap">{lines}</span>
    </button>
  );
}

export function SeenList({ seen, onPlay, withMachine = false }: { seen: Seen[]; onPlay: Play; withMachine?: boolean }) {
  if (seen.length === 0) return <Empty text="Aucun trajet ne passe ici." />;
  return (
    <ul className="flex flex-col gap-1.5">
      {seen.map((s) => (
        <li key={`${s.journey}:${s.step}`}>
          {/* V75: a filled button, a small bar on the left; a click plays the journey from this step. */}
          <button type="button" onClick={() => onPlay(s.journey, s.step)} className="flex w-full items-start gap-2 rounded-lg border border-line bg-raised px-3 py-2 text-left text-[13.5px] leading-snug hover:border-fl-data">
            <span className="mt-1.5 h-1 w-3 shrink-0 rounded-full bg-fl-data" aria-hidden="true" />
            <span className="min-w-0">
              {s.nom} · étape {s.step} — {s.action}
              {withMachine && s.where && <span className="block text-[12px] text-faint">sur « {s.where} »</span>}
            </span>
          </button>
        </li>
      ))}
    </ul>
  );
}
