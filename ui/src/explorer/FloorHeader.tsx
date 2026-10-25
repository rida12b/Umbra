import type { ProjectModel } from "../api";
import type { Floor } from "./floor";
import { FloorKey } from "./floorParts";

/** The top of the floor and of every room in it (V2-V7, V26): what the project does, the data on the belt, the key. */
export function FloorHeader({ model, floor }: { model: ProjectModel; floor: Floor }) {
  const data = model.donnee?.[0];
  return (
    <header className="flex flex-col gap-1.5 px-6 pt-4 pb-1.5">
      <p className="text-[11px] font-semibold tracking-[0.06em] text-faint uppercase">Ce que fait ce projet, pour qui</p>
      <p className="max-w-[920px] text-[15.5px] leading-normal text-ink">{model.pitch || model.resume}</p>
      <p className="text-[12.5px] leading-relaxed text-muted">
        <strong className="font-semibold text-fl-data">La donnée sur le tapis : </strong>
        {data ? (
          <>
            « {data.nom} »
            {data.dans_le_code && (
              <>
                {" "}· dans le code : <span className="font-mono font-semibold text-ink">{data.dans_le_code}</span>
              </>
            )}
          </>
        ) : floor.journey ? (
          <>
            « {floor.journey.depart || floor.journey.nom} » <span className="fl-mtm">pas encore dans le modèle</span>
          </>
        ) : (
          "aucun chemin de données dans le modèle."
        )}
      </p>
      <FloorKey withCode={!data} outside={floor.items.some((i) => i.shape === "outside")} />
    </header>
  );
}
