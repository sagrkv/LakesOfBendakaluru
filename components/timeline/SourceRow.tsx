import Link from "next/link";
import styles from "./list.module.css";
import Piece from "./Piece";
import type { Resolved } from "./types";
import { kindName, statusName } from "./words";

/** One record in the reading list: when, what, what it tells us, and how to open it. */
export default function SourceRow({ source }: { source: Resolved }) {
  return (
    <li className={styles.row}>
      <div className={styles.when}>
        <span className={source.from === undefined ? "missing" : "tabular-nums"}>{source.when}</span>
        <span className={`${styles.small} ${styles.quiet}`}>{kindName(source.kind)}</span>
      </div>

      <div className={styles.what}>
        <span className="font-medium">{source.title}</span>
        <span className={`${styles.small} ${source.holder ? "" : "missing"}`}>
          {source.holder ?? "No holder on record"}
        </span>
      </div>

      <div className={`${styles.small} ${styles.facts}`}>
        <span>{source.tells}</span>
        <span className={styles.quiet}>Covers: {source.coverage}.</span>
        <span className={styles.quiet}>Licence: {source.licence}.</span>
      </div>

      <div className={`${styles.small} ${styles.open}`}>
        <span className={styles.status}>
          <Piece status={source.status} className={styles.swatch} />
          {statusName(source.status)}
        </span>
        {source.access && <span className={styles.quiet}>{source.access}.</span>}
        {source.links.map((link) => (
          <a key={link.href + link.label} href={link.href} target="_blank" rel="noreferrer noopener" className="ink-link">
            {link.label}
            <span className="sr-only"> (opens in a new tab)</span>
          </a>
        ))}
        {source.links.length === 0 && <span className="missing">No public link to it yet</span>}
        {source.sourcesAnchor && (
          <Link href={`/sources#${source.sourcesAnchor}`} prefetch={false} className={`ink-link ${styles.quiet}`}>
            See it in sources and credits
          </Link>
        )}
      </div>
    </li>
  );
}
