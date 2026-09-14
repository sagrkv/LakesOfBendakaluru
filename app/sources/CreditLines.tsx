import { notStated } from "./catalog";
import type { Credit } from "./required";

export default function CreditLines({ credits }: { credits: Credit[] }) {
  return (
    <ul>
      {credits.map((credit) => (
        <li
          key={credit.anchor}
          className="scroll-mt-6 grid gap-x-6 gap-y-2 border-t border-rule py-6 first:border-t-0 first:pt-0 lg:grid-cols-8"
        >
          <h3 className="lg:col-span-3 font-serif text-[26px] md:text-[36px] leading-none">{credit.name}</h3>
          <div className="lg:col-span-5">
            {credit.lines.map((line) => (
              <p key={line}>{line}</p>
            ))}
            <p className="mt-2 label font-normal text-missing">
              {credit.purpose && <>Used for {credit.purpose[0].toLowerCase() + credit.purpose.slice(1)}. </>}
              {notStated(credit.license) ? <span className="italic">Licence not stated. </span> : <>Licence: {credit.license}. </>}
              <a href={`#${credit.anchor}`} className="ink-link hover:text-ink">
                See the full entry
              </a>
            </p>
          </div>
        </li>
      ))}
    </ul>
  );
}
