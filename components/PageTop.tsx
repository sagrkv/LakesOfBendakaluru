import Link from "next/link";
import Wordmark from "./Wordmark";

/** The wordmark and the way back to the map, above an inner page. */
export default function PageTop() {
  return (
    <header className="page-x pt-4 md:pt-6 flex items-center justify-between gap-6">
      <Wordmark href="/" />
      <Link href="/map" className="py-3 label ink-link">
        See all lakes
      </Link>
    </header>
  );
}
