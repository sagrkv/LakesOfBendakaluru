import Link from "next/link";
import SiteFooter from "@/components/SiteFooter";
import PageTop from "@/components/PageTop";
import PunchedSheet from "@/components/past/PunchedSheet";

export default function NotFound() {
  return (
    <>
      <title>Not on any list - Lakes of Bendakaluru</title>
      <PageTop />
      <main className="page-x pt-10 md:pt-16 pb-16 md:pb-26">
        <div className="grid grid-cols-12 gap-x-6 gap-y-10 items-center">
          <div className="col-span-12 md:col-span-7 lg:col-span-6">
            <h1 className="font-serif text-[64px] md:text-[96px] leading-[0.86] text-balance">
              This lake is not on any list we have
            </h1>
            <p className="mt-6 max-w-[34rem]">
              The address may be mistyped, or the lake may be listed under another name. Every lake we know of is on
              the map.
            </p>
            <div className="mt-10 flex flex-wrap items-center gap-x-6 gap-y-4">
              <Link href="/map" className="button-ink text-[28px] md:text-[38px]">
                See all lakes
              </Link>
              <Link href="/" className="py-3 ink-link">
                Go to the home page
              </Link>
            </div>
          </div>
          <div className="col-span-12 md:col-span-5 lg:col-start-8 order-first md:order-none">
            <PunchedSheet
              id="not-found"
              width={400}
              height={300}
              holes={[{ id: "missing", x: 236, y: 140, r: 72 }]}
              label="A sheet of dark paper with one hole in it."
              className="w-2/3 md:w-full"
            />
          </div>
        </div>
      </main>
      <SiteFooter />
    </>
  );
}
