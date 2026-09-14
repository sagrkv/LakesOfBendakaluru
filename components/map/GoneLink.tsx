import Link from "next/link";
import { formatCount } from "@/lib/format";

/** Lakes that are not drawn on the map have their own pages: the ones that disappeared, and the ones no map draws. */
export default function GoneLink({ gone, missing }: { gone: number | null; missing: number | null }) {
  if (!gone && !missing) return null;
  return (
    <>
      See{" "}
      {gone ? (
        <Link href="/once-upon-a-kere" className="ink-link hover:text-ink">
          the {formatCount(gone)} that disappeared
        </Link>
      ) : null}
      {gone && missing ? " and " : null}
      {missing ? (
        <Link href="/missing-lakes" className="ink-link hover:text-ink">
          the {formatCount(missing)} no map draws
        </Link>
      ) : null}
      .
    </>
  );
}
