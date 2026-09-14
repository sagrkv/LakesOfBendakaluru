import Link from "next/link";
import { formatAcres, WATER_CLASS } from "@/lib/format";
import type { LakeSummary } from "@/lib/lake";
import Swatch from "./Swatch";
import { pctText, placeName, valleyName } from "./words";

type FactProps = { label: string; value?: string; unit?: string; note?: string; missing: string };

function Fact({ label, value, unit, note, missing }: FactProps) {
  return (
    <div className="min-w-0">
      <dt className="label">{label}</dt>
      <dd className="mt-1">
        {value === undefined ? (
          <span className="missing block text-[17px] leading-tight">{missing}</span>
        ) : (
          <>
            <span className="font-serif text-[26px] leading-none lg:text-[36px]">{value}</span>
            {unit ? <span className="label"> {unit}</span> : null}
            {note ? <span className="label mt-1 block text-missing">{note}</span> : null}
          </>
        )}
      </dd>
    </div>
  );
}

/** The lake you tapped: a paper slip on a laptop, the top of the dock on a phone. */
export default function LakeCard({ lake, onClose, floating }: { lake: LakeSummary; onClose: () => void; floating: boolean }) {
  const gone = lake.status !== "exists";
  const place = placeName(lake);
  const valley = valleyName(lake.valley);
  const acres = lake.acres === undefined ? undefined : formatAcres(lake.acres);

  return (
    <section aria-label={lake.name} className={floating ? "slip p-6" : "px-4 pt-2 pb-4"}>
      <div className="flex items-center justify-between gap-3">
        <p className="label flex min-w-0 items-center gap-2">
          <Swatch valley={lake.valley} gone={gone} />
          {gone ? "Disappeared" : (valley ?? <span className="missing">No valley on record</span>)}
        </p>
        <button
          type="button"
          onClick={onClose}
          aria-label="Close"
          className="-mr-3 grid size-11 shrink-0 place-items-center transition-colors duration-150 hover:bg-well active:bg-rule"
        >
          <svg width="14" height="14" viewBox="0 0 14 14" aria-hidden>
            <path d="M1 1l12 12M13 1L1 13" stroke="currentColor" strokeWidth="1.5" />
          </svg>
        </button>
      </div>

      <h2 className="font-serif text-[26px] leading-[0.95] lg:text-[36px]">{lake.name}</h2>
      {lake.nameKannada ? (
        <p lang="kn" className="mt-1 font-kannada text-[17px] leading-[1.2]">
          {lake.nameKannada}
        </p>
      ) : null}
      {place ? <p className="label mt-2 text-missing">{place}</p> : null}

      {gone ? (
        <dl className="mt-4 grid grid-cols-[auto_minmax(0,1fr)] gap-6 border-t border-rule pt-3">
          <Fact label="Size" value={acres} unit="acres" missing="Not on record" />
          <div className="min-w-0">
            <dt className="label">On the site now</dt>
            <dd className="mt-1 text-[17px] leading-tight">
              {lake.nowOccupiedBy ?? <span className="missing">Not on record</span>}
            </dd>
          </div>
        </dl>
      ) : (
        <dl className="mt-4 grid grid-cols-3 gap-3 border-t border-rule pt-3">
          <Fact label="Size" value={acres} unit="acres" missing="Not on record" />
          <Fact
            label="Water class"
            value={lake.waterClass}
            note={lake.waterClass ? WATER_CLASS[lake.waterClass].short : undefined}
            missing="Not tested yet"
          />
          <Fact
            label="Built over"
            value={lake.builtPct === undefined ? undefined : pctText(lake.builtPct)}
            note="2021 satellite"
            missing="Not measured"
          />
        </dl>
      )}

      {lake.campaign ? (
        <p className="label mt-4 inline-block -rotate-2 border-2 border-ink px-2 py-1">Residents are organising here</p>
      ) : null}

      <div className="mt-4">
        <Link href={`/lake/${lake.id}`} className="button-ink text-[28px] lg:text-[38px]">
          Open lake page
        </Link>
      </div>
    </section>
  );
}
