import type { ProjectModel } from "../api";
import { stepLabel } from "../arch/story.ts";

// Ctrl K with the reader's own words (#80): one index per model of everything a reader may name — rooms, machines,
// their settings, the « Je veux changer… » intentions, journey steps and special cases, functions, files, doubts.
// A machine also carries its `termes` (« nom du client » = « X-Tenant-ID »), so a plain word reaches the code word.
// Pure, tested on the real models (searchIndex.test.ts).

export type Target =
  | { kind: "machine"; bloc: string; machine: string; row: string | null } // its plate, a settings row lit
  | { kind: "room"; bloc: string }
  | { kind: "projet"; row: string } // the project's settings plate
  | { kind: "etape"; journey: string; step: number }
  | { kind: "code"; path: string; lines: [number, number] | null }
  | { kind: "usine" };

export type Kind = "changer" | "machine" | "reglage" | "etape" | "code" | "doute";
export const GROUP_TITLE: Record<Kind, string> = {
  changer: "Je veux changer…",
  machine: "Pièces et machines",
  reglage: "Réglages",
  etape: "Étapes des trajets",
  code: "Fonctions et fichiers",
  doute: "Doutes de l'étude",
};
const ORDER: Kind[] = ["changer", "machine", "reglage", "etape", "code", "doute"];

export interface Result {
  key: string;
  kind: Kind;
  label: string;
  detail: string; // the code, the plain sentence, the path
  address: string; // « Porte d'entrée du service › Contrôle du nom du client › Réglage … »
  note: string | null;
  target: Target;
}
interface Entry extends Result {
  name: string[]; // the words of its name: a match there ranks first
  terms: string[]; // its plain/code word pairs: a match there ranks next
  body: string[]; // everything else a reader may type
}
export interface Group {
  kind: Kind;
  title: string;
  results: Result[];
}

/** Accents and capitals do not count: « ÉCRAN » is « ecran ». */
export const plain = (text: string) => text.normalize("NFD").replace(/\p{Diacritic}/gu, "").toLowerCase();
const words = (text: string) => plain(text).split(/[^a-z0-9]+/).filter(Boolean);

export function buildIndex(model: ProjectModel): Entry[] {
  const bloc = new Map(model.blocs.map((b) => [b.id, b]));
  const comp = new Map(model.composants.map((c) => [c.id, c]));
  const roomOf = (id: string) => bloc.get(comp.get(id)?.bloc ?? "")?.nom ?? "";
  const entries: Entry[] = [];
  const add = (e: Omit<Entry, "name" | "terms" | "body" | "note"> & { name: string; terms?: string; body?: string; note?: string | null }) =>
    entries.push({ ...e, note: e.note ?? null, name: words(e.name), terms: words(e.terms ?? ""), body: words(e.body ?? "") });

  for (const b of model.blocs)
    add({ key: `bloc:${b.id}`, kind: "machine", label: b.nom, detail: b.en_bref || b.role, address: `L'usine › ${b.nom}`, target: { kind: "room", bloc: b.id }, name: b.nom, body: b.en_bref || b.role });
  for (const c of model.composants) {
    const at = `${roomOf(c.id)} › ${c.nom}`;
    const machine = (row: string | null): Target => ({ kind: "machine", bloc: c.bloc, machine: c.id, row });
    const terms = (c.termes ?? []).map((t) => `${t.simple} ${t.code}`).join(" ");
    // Not its `role`: written for a developer, it names the code's shared words (« tenant_id ») in every machine, and a
    // search for one would list them all. Its plain words and its terms carry the reader's vocabulary.
    add({ key: `composant:${c.id}`, kind: "machine", label: c.nom, detail: c.en_bref || c.role, address: at, target: machine(null), name: c.nom, terms, body: c.en_bref || c.role });
    for (const r of c.reglages ?? [])
      add({ key: `reglage:${c.id}:${r.code}`, kind: "reglage", label: r.nom, detail: r.code, address: `${at} › Réglage`, target: machine(r.code), name: r.nom, terms, body: `${r.code} ${r.valeur} ${r.effet}` });
    for (const e of c.expose)
      add({ key: `fonction:${c.id}:${e.quoi}`, kind: "code", label: e.quoi, detail: e.fichier ?? "", address: at, target: { kind: "code", path: e.fichier ?? "", lines: e.lignes }, name: e.quoi, body: e.fichier ?? "" });
    for (const f of c.fichiers)
      add({ key: `fichier:${f}`, kind: "code", label: f.split("/").pop() || f, detail: f, address: at, target: { kind: "code", path: f, lines: null }, name: f, body: model.modules[f] ?? "" });
  }
  for (const r of model.reglages_projet ?? [])
    add({ key: `projet:${r.code}`, kind: "reglage", label: r.nom, detail: r.code, address: "L'usine › Réglages du projet", note: r.lu_par_le_code === "non" ? "lu par le code : non" : null, target: { kind: "projet", row: r.code }, name: r.nom, body: `${r.code} ${r.valeur} ${r.fichier ?? ""}` });
  for (const l of model.pour_changer ?? []) {
    const c = comp.get(l.composant);
    if (!c) continue; // an intention on a machine the model does not have: nowhere to land
    const terms = (c.termes ?? []).map((t) => `${t.simple} ${t.code}`).join(" ");
    add({ key: `changer:${l.intention}`, kind: "changer", label: l.intention, detail: l.reglage, address: `${roomOf(c.id)} › ${c.nom}`, target: { kind: "machine", bloc: c.bloc, machine: c.id, row: l.reglage }, name: l.intention, terms });
  }
  for (const j of model.parcours) {
    add({ key: `trajet:${j.id}`, kind: "etape", label: j.nom, detail: j.depart || j.declencheur, address: `Trajet · ${j.etapes.length} étapes`, target: { kind: "etape", journey: j.id, step: 1 }, name: j.nom });
    j.etapes.forEach((s, i) =>
      add({ key: `etape:${j.id}:${i + 1}`, kind: "etape", label: stepLabel(s), detail: s.simple || s.texte, address: `${j.nom} › étape ${i + 1}`, target: { kind: "etape", journey: j.id, step: i + 1 }, name: stepLabel(s), body: `${s.simple ?? ""} ${s.texte}` }),
    );
    (j.branches ?? []).forEach((b, k) =>
      add({
        key: `cas:${j.id}:${k}`, kind: "etape", label: `Si ${b.quand_simple || b.quand}`, detail: b.alors_simple || b.alors, address: `${j.nom} › cas particulier`,
        target: { kind: "etape", journey: j.id, step: b.etape && b.etape >= 1 && b.etape <= j.etapes.length ? b.etape : 1 }, name: b.quand_simple || b.quand, body: `${b.quand} ${b.alors} ${b.alors_simple ?? ""}`,
      }),
    );
  }
  model.incertitudes.forEach((d, i) => add({ key: `doute:${i}`, kind: "doute", label: d, detail: "", address: "Ce que l'étude n'a pas pu confirmer", target: { kind: "usine" }, name: d }));
  return entries;
}

/** Every word typed must start a word of the entry. Name first, then its terms, then the rest; groups in a fixed order. */
export function searchIndex(index: Entry[], query: string): Group[] {
  const wanted = words(query);
  if (wanted.join("").length < 2) return [];
  const hits = (list: string[]) => wanted.every((w) => list.some((t) => t.startsWith(w)));
  const scored = index.flatMap((e) => {
    const score = hits(e.name) ? 3 : hits([...e.name, ...e.terms]) ? 2 : hits([...e.name, ...e.terms, ...e.body]) ? 1 : 0;
    return score ? [{ e, score }] : [];
  });
  return ORDER.flatMap((kind) => {
    const results = scored
      .filter(({ e }) => e.kind === kind)
      .sort((a, b) => b.score - a.score)
      .map(({ e: { name: _n, terms: _t, body: _b, ...result } }) => result);
    return results.length ? [{ kind, title: GROUP_TITLE[kind], results }] : [];
  });
}
