/** What the first paint shows while the map's browser code starts. */
export default function MapFallback() {
  return (
    <div className="fixed inset-0 grid place-items-center bg-table">
      <div className="text-center">
        <p className="font-serif text-[28px] leading-none italic">Lakes of Bendakaluru</p>
        <p className="label mt-3 text-missing">Laying out the lakes…</p>
      </div>
    </div>
  );
}
