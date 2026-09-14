import type { Source } from "@/lib/lake";

/**
 * "See source" after a fact. Resolve the key on the server with getSource() and pass the result;
 * a key with no citation renders nothing rather than a dead link.
 */
export default function SourceLink({ source, className = "" }: { source?: Source; className?: string }) {
  if (!source) return null;
  const title = [source.credit ?? source.title, source.asOf].filter(Boolean).join(", ");
  const href = source.url ?? `/sources#${source.key}`;
  return (
    <a
      href={href}
      target={source.url ? "_blank" : undefined}
      rel={source.url ? "noreferrer noopener" : undefined}
      title={title}
      className={`label ink-link text-missing hover:text-ink ${className}`}
    >
      See source
    </a>
  );
}
