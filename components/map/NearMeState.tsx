import type { NearMe } from "./useNearMe";

/** Near me before there is a location: ask, wait, or say why it failed and how to fix it. */
export default function NearMeState({ state, onLocate, edge }: { state: NearMe; onLocate: () => void; edge: string }) {
  if (state.status === "locating") {
    return (
      <p role="status" className={`${edge} py-6 text-[17px]`}>
        Finding where you are…
      </p>
    );
  }

  const failed = state.status === "denied" || state.status === "unavailable";
  const copy =
    state.status === "denied"
      ? "Location is blocked for this site. Allow it in your browser’s site settings, then try again."
      : state.status === "unavailable"
        ? "Your device could not say where you are. Check that location is turned on, then try again."
        : "See the lakes closest to where you are. Your location stays on your device.";

  return (
    <div className={`${edge} py-6`} role={failed ? "alert" : undefined}>
      <p className="max-w-[45ch] text-[17px]">{copy}</p>
      <button type="button" onClick={onLocate} className="button-ink mt-4 text-[28px] lg:text-[38px]">
        {failed ? "Try again" : "Use my location"}
      </button>
    </div>
  );
}
