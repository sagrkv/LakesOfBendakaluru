import Link from "next/link";

/** The credit lines the data licences require, on every page. Full list on /sources. */
export default function SiteFooter() {
  return (
    <footer className="page-x py-10 border-t border-rule">
      <div className="flex flex-wrap items-baseline justify-between gap-x-10 gap-y-4">
        <Link href="/" className="font-serif italic text-[28px] leading-none">
          Lakes of Bendakaluru
        </Link>
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
      <p className="mt-6 label text-missing max-w-3xl">
        Lake outlines: ATREE-CSEI, CC BY. Map data: © OpenStreetMap contributors, ODbL. Water history: EC JRC Global
        Surface Water. Satellite: Copernicus Sentinel-2. Land cover: ESA WorldCover 2021. Water quality: Karnataka
        State Pollution Control Board. Lake inventory: EMPRI 2018.
      </p>
    </footer>
  );
}
