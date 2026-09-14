import type { Status } from "./types";
import styles from "./timeline.module.css";

const LOOK: Record<Status, string> = {
  "on-site": styles.onSite,
  found: styles.found,
  "not-public": styles.notPublic,
};

/** The paper a mark is made of: pasted for on the site, traced for found, torn out for not public. */
export default function Piece({ status, className = "" }: { status: Status; className?: string }) {
  return <span aria-hidden className={`${styles.piece} ${LOOK[status]} ${className}`} />;
}
