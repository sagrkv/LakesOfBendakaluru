import type { Resolved } from "./types";

const lowerFirst = (text: string) => (/^[A-Z][a-z]/.test(text) ? text[0].toLowerCase() + text.slice(1) : text);

/** Records known to exist that nobody can open yet, each with what stands in the way. */
export default function NotPublic({ sources }: { sources: Resolved[] }) {
  const closed = sources.filter((source) => source.status === "not-public");
  if (closed.length === 0) return null;

  return (
    <ul className="mt-6 grid gap-x-6 gap-y-6 sm:grid-cols-2 lg:grid-cols-3">
      {closed.map((source) => (
        <li key={source.id} className="border-t border-rule pt-3">
          <p className={`label ${source.from === undefined ? "missing" : "text-missing tabular-nums"}`}>
            {source.from === undefined ? "No year on record" : source.when}
          </p>
          <p className="mt-1 font-medium">{source.title}</p>
          {source.holder ? <p className="label font-normal">{source.holder}</p> : null}
          <p className="mt-2">Not public: {lowerFirst(source.access ?? "no copy can be found")}.</p>
          {source.links.map((link) => (
            <a
              key={link.href + link.label}
              href={link.href}
              target="_blank"
              rel="noreferrer noopener"
              className="mt-1 inline-block label ink-link"
            >
              {link.label}
              <span className="sr-only"> (opens in a new tab)</span>
            </a>
          ))}
        </li>
      ))}
    </ul>
  );
}
