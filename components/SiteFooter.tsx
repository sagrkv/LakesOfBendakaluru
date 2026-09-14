import Link from "next/link";
import { PAPERS } from "@/lib/valleys";
import MadeBy from "./MadeBy";
import Wordmark from "./Wordmark";

/** The credit lines the data licences require, on every page. Full list on /sources. */
export default function SiteFooter() {
  return (
    <footer className="bg-night text-table [&_:focus-visible]:outline-table">
      {/* One strip of every valley's paper, the colours the lakes are cut from. */}
      <div aria-hidden className="flex h-3 border-y-2 border-ink">
        {PAPERS.map((paper) => (
          <span key={paper.label} className="flex-1" style={{ background: paper.sheet }} />
        ))}
      </div>
      <div className="page-x py-10">
        <div className="flex flex-wrap items-center justify-between gap-x-10 gap-y-6">
          <div>
            <Wordmark href="/" />
            <MadeBy className="mt-4 [&_a]:text-sun" />
          </div>
          <nav className="flex flex-wrap gap-x-6 gap-y-2 label">
            <Link href="/map" className="ink-link">
              See all lakes
            </Link>
            <Link href="/once-upon-a-kere" className="ink-link">
              Once upon a kere
            </Link>
            <Link href="/missing-lakes" className="ink-link">
              Missing lakes
            </Link>
            <Link href="/timeline" className="ink-link">
              Timeline
            </Link>
            <Link href="/sources" className="ink-link">
              Sources and credits
            </Link>
          </nav>
        </div>
        <p className="mt-8 label font-normal text-table/80 max-w-3xl">
          Lake outlines: ATREE-CSEI, CC BY. Map data: © OpenStreetMap contributors, ODbL. Water history: EC JRC Global
          Surface Water. Satellite: Copernicus Sentinel-2. Land cover: ESA WorldCover 2021. Water quality: Karnataka
          State Pollution Control Board. Lake inventory: EMPRI 2018.
        </p>
      </div>
    </footer>
  );
}
