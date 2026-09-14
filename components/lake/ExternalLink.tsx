import type { ReactNode } from "react";

/** A link that leaves the site. Opens in a new tab so the lake page stays where it was. */
export default function ExternalLink({ href, children }: { href: string; children: ReactNode }) {
  return (
    <a href={href} target="_blank" rel="noreferrer noopener" className="ink-link break-words">
      {children}
    </a>
  );
}
