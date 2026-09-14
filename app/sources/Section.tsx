import type { ReactNode } from "react";

/** A headline in the first four columns, its content in the other eight. Stacks on phones. */
export default function Section({ title, intro, children }: { title: string; intro?: string; children: ReactNode }) {
  return (
    <section className="page-x py-16 md:py-26">
      <div className="grid grid-cols-12 gap-x-6">
        <div className="col-span-12 lg:col-span-4">
          <h2 className="font-serif text-[48px] md:text-[64px] leading-[0.95] text-balance">
            <span className="highlight">{title}</span>
          </h2>
          {intro && <p className="mt-6 max-w-[34rem]">{intro}</p>}
        </div>
        <div className="col-span-12 lg:col-span-8 mt-10 lg:mt-0">{children}</div>
      </div>
    </section>
  );
}
