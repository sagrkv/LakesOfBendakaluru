import type { ReactNode } from "react";

/**
 * A group of facts about one side of a lake. When the record holds nothing for it,
 * the section is one grey line stating the gap, so the page shows what is missing too.
 */
export default function Section({
  id,
  title,
  missing,
  empty,
  children,
}: {
  id: string;
  title: string;
  missing: string;
  empty: boolean;
  children?: ReactNode;
}) {
  return (
    <section id={id} aria-labelledby={`${id}-title`} className="scroll-mt-6 pt-16 md:pt-[104px]">
      <h2 id={`${id}-title`} className="max-w-[18ch] font-serif text-[40px] md:text-[64px] leading-[0.95]">
        {title}
      </h2>
      {empty ? (
        <p className="missing mt-4 md:mt-6">{missing}</p>
      ) : (
        <div className="mt-6 md:mt-10 grid items-start gap-6 sm:grid-cols-2 xl:grid-cols-3">{children}</div>
      )}
    </section>
  );
}
