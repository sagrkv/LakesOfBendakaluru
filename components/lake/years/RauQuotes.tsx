import type { Rau1986 } from "@/lib/lake";

const QUOTES = [
  { key: "condition", name: "Condition" },
  { key: "landUse", name: "Land use the 1984 development plan proposed" },
  { key: "recommendation", name: "What the committee recommended" },
] as const;

/** The committee's own words, quoted as the scan reads, with its reading errors. */
export default function RauQuotes({ rau }: { rau: Rau1986 }) {
  const quotes = QUOTES.flatMap((quote) => {
    const text = rau[quote.key]?.trim();
    return text ? [{ ...quote, text }] : [];
  });
  if (!quotes.length) return null;

  return (
    <div className="mt-4">
      <dl className="grid gap-y-3">
        {quotes.map((quote) => (
          <div key={quote.key}>
            <dt className="label">{quote.name}</dt>
            <dd className="max-w-[65ch]">&ldquo;{quote.text}&rdquo;</dd>
          </div>
        ))}
      </dl>
      <p className="label mt-3 font-normal">Quoted from a scan of the report, so the words may carry reading errors</p>
    </div>
  );
}
