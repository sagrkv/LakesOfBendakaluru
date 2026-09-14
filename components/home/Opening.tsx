import Link from "next/link";
import type { CSSProperties } from "react";
import { paperFor } from "@/lib/valleys";
import Facts from "./Facts";
import { SLOT } from "./fit";
import type { Opener } from "./opener";
import ShowAnother from "./ShowAnother";
import Stage from "./Stage";
import Wordmark from "@/components/Wordmark";

/**
 * The opening screen: one lake cut out and filling the page, facts pasted on top.
 * The name sits at the foot of a slot as tall as the tallest possible name,
 * so the room and the buttons stay in the same place whichever lake comes up.
 */
export default function Opening({ opener }: { opener: Opener }) {
  const { lake, summary, fit } = opener;
  const valley = summary.valley ?? lake.water?.valley;
  const paper = paperFor(valley);
  const slot = { "--slot": `${SLOT.laptop}px`, "--slot-p": `${SLOT.phone}px` } as CSSProperties;

  return (
    <section
      aria-labelledby="lake-name"
      className="page-x relative isolate min-h-svh overflow-clip pt-4 pb-16 md:pt-10 md:pb-26"
    >
      <div className="xl:grid xl:grid-cols-[640px_minmax(0,1fr)] xl:items-start xl:gap-x-10">
        <div>
          <Wordmark />
          <div className="mt-10 flex h-(--slot-p) items-end md:mt-16 md:h-(--slot)" style={slot}>
            <Stage
              key={lake.id}
              id={lake.id}
              name={lake.name}
              nameKannada={lake.nameKannada}
              sheet={lake.sheet}
              valley={valley}
              paper={paper}
              fit={fit}
            />
          </div>
          <div className="mt-10 flex flex-wrap items-center gap-3 md:gap-4">
            <Link href="/map" className="button-ink text-[28px] md:text-[38px]">
              See all lakes
            </Link>
            <ShowAnother current={lake.name} />
          </div>
          {fit.fullName ? (
            <p key={lake.id} className="slip label mt-6 inline-block max-w-[290px] px-3 pt-2 pb-2.5 md:max-w-[640px]">
              The full name, {fit.fullName}, does not fit on the page.
            </p>
          ) : null}
        </div>
        <Facts key={lake.id} opener={opener} paper={paper} className="mt-16 xl:mt-0" />
      </div>
    </section>
  );
}
