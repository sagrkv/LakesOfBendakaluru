import Link from "next/link";
import type { CSSProperties } from "react";
import { tiltFor } from "@/components/paper/Slip";
import Piece from "./Piece";
import styles from "./timeline.module.css";
import type { Resolved } from "./types";
import { kindName, statusName } from "./words";

/** The slip for the chosen mark: what the record tells us, what it covers, and a way to open it. */
export default function DetailSlip({ source, onClose }: { source: Resolved | null; onClose: () => void }) {
  const style = { "--tilt": `${tiltFor(source?.id ?? "timeline-empty") / 2}deg` } as CSSProperties;

  return (
    <div id="timeline-slip" className={`slip ${styles.slip} ${source ? "" : "max-xl:hidden"}`} style={style}>
      {source ? (
        <div key={source.id} className="pastes p-4 md:p-6">
          <div className="flex items-baseline justify-between gap-4">
            <p className="label text-missing">
              {kindName(source.kind)}, {source.from === undefined ? "no year on record" : source.when}
            </p>
            <button type="button" onClick={onClose} className="xl:hidden -my-3 py-3 label ink-link cursor-pointer">
              Close
            </button>
          </div>
          <h3 className="mt-2 font-serif text-[26px] md:text-[36px] leading-none text-balance">{source.title}</h3>
          {source.holder ? (
            <p className="mt-2 label font-normal">{source.holder}</p>
          ) : (
            <p className="mt-2 label missing">No holder on record</p>
          )}

          <p className="mt-4">{source.tells}</p>

          <dl className="mt-4 grid grid-cols-[auto_1fr] gap-x-4 gap-y-1 label font-normal">
            <dt className="text-missing">Covers</dt>
            <dd>{source.coverage}</dd>
            <dt className="text-missing">Licence</dt>
            <dd>{source.licence}</dd>
            <dt className="text-missing">Status</dt>
            <dd className="flex items-center gap-2">
              <Piece status={source.status} className="w-2.5! h-4! shrink-0" />
              {statusName(source.status)}
              {source.access && <span className="text-missing">. {source.access}</span>}
            </dd>
          </dl>

          {source.links.length > 0 ? (
            <ul className="mt-4 space-y-1">
              {source.links.map((link) => (
                <li key={link.href + link.label}>
                  <a href={link.href} target="_blank" rel="noreferrer noopener" className="ink-link">
                    {link.label}
                    <span className="sr-only"> (opens in a new tab)</span>
                  </a>
                </li>
              ))}
            </ul>
          ) : (
            <p className="mt-4 missing">No public link to it yet.</p>
          )}
          {source.sourcesAnchor && (
            <Link href={`/sources#${source.sourcesAnchor}`} className="mt-1 inline-block label ink-link text-missing hover:text-ink">
              See it in sources and credits
            </Link>
          )}
        </div>
      ) : (
        <div className="p-4 md:p-6">
          <h3 className="font-serif text-[26px] md:text-[36px] leading-none">Choose a mark</h3>
          <p className="mt-4 max-w-[30rem]">
            Each mark is one record of the lakes. Choose one to read what it tells us and open it. With a keyboard,
            the arrow keys move through time.
          </p>
        </div>
      )}
    </div>
  );
}
