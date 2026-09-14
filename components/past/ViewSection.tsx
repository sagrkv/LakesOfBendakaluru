import type { ReactNode } from "react";

/** A page-level view: the headline and a short note on the left, bars on the right, two columns wide. */
export default function ViewSection({
  id,
  title,
  note,
  children,
}: {
  id: string;
  title: string;
  note: ReactNode;
  children: ReactNode;
}) {
  return (
    <section aria-labelledby={`${id}-title`} className="page-x pb-16 md:pb-26">
      <div className="grid grid-cols-12 gap-x-6 gap-y-10">
        <div className="col-span-12 lg:col-span-4">
          <h2 id={`${id}-title`} className="font-serif text-[48px] md:text-[64px] leading-[0.95] text-balance">
            <span className="highlight">{title}</span>
          </h2>
          <div className="mt-6 max-w-[34rem] space-y-4">{note}</div>
        </div>
        <div className="col-span-12 lg:col-span-8 grid sm:grid-cols-2 gap-x-6 gap-y-10 content-start">{children}</div>
      </div>
    </section>
  );
}
