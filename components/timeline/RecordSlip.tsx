import Link from "next/link";
import type { CSSProperties } from "react";
import { tiltFor } from "@/components/paper/Slip";
import type { Resolved } from "./types";
import { kindOf } from "./words";

function fileSize(bytes: number): string {
  return bytes >= 1_000_000 ? `${(bytes / 1_000_000).toFixed(1)} MB` : `${Math.max(1, Math.round(bytes / 1000))} KB`;
}

function External({ href, children }: { href: string; children: string }) {
  return (
    <a href={href} target="_blank" rel="noreferrer noopener" className="ink-link">
      {children}
      <span className="sr-only"> (opens in a new tab)</span>
    </a>
  );
}

/** One record hung on the line, in the paper of its kind: what it is, what it tells us about a lake, our copy and the original. */
export default function RecordSlip({ source }: { source: Resolved }) {
  const kind = kindOf(source.kind);
  const style = { "--paper": kind.paper, "--tilt": `${tiltFor(source.id) / 3}deg` } as CSSProperties;

  return (
    <article id={source.id} aria-labelledby={`${source.id}-title`} className="relative scroll-mt-6" style={style}>
      {/* The record's mark on the line, centred on the line column to the left. */}
      <span
        aria-hidden
        className="absolute top-6 -left-[37px] size-[18px] rotate-12 border-2 border-ink lg:-left-[45px]"
        style={{ background: kind.paper }}
      />
      <div className="slip slip-tint p-4 md:p-6">
        <p className="label flex items-center gap-2">
          <span aria-hidden className="size-2.5 shrink-0 border border-ink" style={{ background: kind.paper }} />
          {kind.one}, {source.when.charAt(0).toLowerCase() + source.when.slice(1)}
        </p>
        <h3 id={`${source.id}-title`} className="mt-2 font-serif text-[26px] leading-none text-balance md:text-[36px]">
          {source.title}
        </h3>
        {source.holder ? <p className="label mt-2 font-normal">{source.holder}</p> : null}

        <p className="mt-4 max-w-[60ch]">{source.tells}</p>

        <dl className="label mt-4 grid grid-cols-[auto_minmax(0,1fr)] gap-x-4 gap-y-1 font-normal">
          <dt className="text-missing">Covers</dt>
          <dd>{source.coverage}</dd>
          <dt className="text-missing">Licence</dt>
          <dd>{source.licence}</dd>
        </dl>

        {source.copies.length || source.links.length ? (
          <div className="mt-5 grid gap-x-10 gap-y-4 border-t border-ink/15 pt-4 sm:grid-cols-2">
            {source.copies.length ? (
              <div>
                <p className="label text-missing">Our copy</p>
                <ul className="mt-1 space-y-1">
                  {source.copies.map((copy) => (
                    <li key={copy.href}>
                      <a href={copy.href} className="ink-link font-medium">
                        {copy.label}
                      </a>{" "}
                      <span className="label font-normal whitespace-nowrap text-missing">
                        {copy.format}, {fileSize(copy.bytes)}
                      </span>
                    </li>
                  ))}
                </ul>
              </div>
            ) : null}
            {source.links.length ? (
              <div>
                <p className="label text-missing">The original</p>
                <ul className="mt-1 space-y-1">
                  {source.links.map((link) => (
                    <li key={link.href + link.label}>
                      <External href={link.href}>{link.label}</External>
                    </li>
                  ))}
                </ul>
              </div>
            ) : null}
          </div>
        ) : null}

        {source.sourcesAnchor ? (
          <Link
            href={`/sources#${source.sourcesAnchor}`}
            prefetch={false}
            className="label ink-link mt-4 inline-block font-normal text-missing hover:text-ink"
          >
            See it in sources and credits
          </Link>
        ) : null}
      </div>
    </article>
  );
}
