import Link from "next/link";
import { formatCount } from "@/lib/format";

/** Disappeared lakes are not drawn on the map; they have their own page. */
export default function GoneLink({ gone }: { gone: number | null }) {
  if (!gone) return null;
  return (
    <Link href="/once-upon-a-kere" className="ink-link hover:text-ink">
      See the {formatCount(gone)} that disappeared
    </Link>
  );
}
