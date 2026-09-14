import Link from "next/link";

/** The wordmark and the way back to the map, above an inner page. */
export default function PageTop() {
  return (
    <header className="page-x pt-3 md:pt-6 flex items-baseline justify-between gap-6">
      <Link href="/" className="py-3 font-serif italic text-[28px] leading-none">
        Lakes of Bendakaluru
      </Link>
      <Link href="/map" className="py-3 label ink-link">
        See all lakes
      </Link>
    </header>
  );
}
