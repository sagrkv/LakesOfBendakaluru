import Link from "next/link";

/** "Lakes of Bendakaluru" on sun-yellow paper, so it stands out on the table, a satellite view or a sheet. */
export default function Wordmark({ href, className = "" }: { href?: string; className?: string }) {
  if (!href) return <p className={`wordmark ${className}`}>Lakes of Bendakaluru</p>;
  return (
    <Link href={href} className={`wordmark ${className}`}>
      Lakes of Bendakaluru
    </Link>
  );
}
