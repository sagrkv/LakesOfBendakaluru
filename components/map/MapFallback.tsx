import Wordmark from "@/components/Wordmark";

/** What the first paint shows while the map's browser code starts. */
export default function MapFallback() {
  return (
    <div className="fixed inset-0 grid place-items-center bg-table">
      <div className="text-center">
        <Wordmark />
        <p className="label mt-4 text-missing">Laying out the lakes…</p>
      </div>
    </div>
  );
}
