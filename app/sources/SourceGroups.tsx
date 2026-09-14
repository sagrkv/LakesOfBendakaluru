import type { Source } from "@/lib/lake";
import { formatAsOf, notStated, purposeOf, type SourceGroup } from "./catalog";

function Licence({ license }: { license?: string }) {
  if (notStated(license)) return <span className="italic">Licence {license ?? "not stated"}.</span>;
  return <>Licence: {license}.</>;
}

function Entry({ source, shared }: { source: Source; shared: boolean }) {
  const purpose = purposeOf(source.key);
  const asOf = formatAsOf(source.asOf);
  return (
    <li id={source.key} className="scroll-mt-6 -mx-2 px-2 py-3 target:bg-well">
      {source.url ? (
        <a href={source.url} target="_blank" rel="noreferrer noopener" className="ink-link">
          {source.title}
          <span className="sr-only"> (opens in a new tab)</span>
        </a>
      ) : (
        <span>{source.title}</span>
      )}
      <p className="mt-1 label font-normal text-missing">
        {purpose && <>Used for {purpose[0].toLowerCase() + purpose.slice(1)}. </>}
        {asOf ? <>As of {asOf}.</> : <span className="italic">Date not stated.</span>}
        {!shared && (
          <>
            {" "}
            <Licence license={source.license} />
          </>
        )}
      </p>
      {!shared && source.credit && <p className="label font-normal text-missing">Credit: {source.credit}</p>}
    </li>
  );
}

/** Every source, under its publisher. Groups whose sources share a licence and credit show them once. */
export default function SourceGroups({ groups }: { groups: SourceGroup[] }) {
  return (
    <div>
      {groups.map((group) => {
        const first = group.sources[0];
        return (
          <section key={group.publisher} className="border-t border-rule pt-6 pb-10 first:border-t-0 first:pt-0">
            {notStated(group.publisher) ? (
              <h3 className="missing">Publisher {group.publisher}</h3>
            ) : (
              <h3 className="font-medium">{group.publisher}</h3>
            )}
            {group.shared && (
              <p className="mt-1 label font-normal text-missing">
                <Licence license={first.license} />
                {first.credit && <> Credit: {first.credit}</>}
              </p>
            )}
            <ul className={`mt-2 grid gap-x-6 ${group.shared && group.sources.length >= 4 ? "md:grid-cols-2" : ""}`}>
              {group.sources.map((source) => (
                <Entry key={source.key} source={source} shared={group.shared} />
              ))}
            </ul>
          </section>
        );
      })}
    </div>
  );
}
