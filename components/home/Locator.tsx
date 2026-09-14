import type { City } from "./opener";

/** Every lake in the city as a dot, this one circled. */
export default function Locator({
  city,
  xy,
  name,
  sheetColor,
  className = "",
}: {
  city: City;
  xy?: [number, number];
  name: string;
  sheetColor: string;
  className?: string;
}) {
  const ring = city.width * 0.075;
  return (
    <svg
      viewBox={`0 0 ${city.width} ${city.height}`}
      role="img"
      aria-label={xy ? `Every lake in the city as a dot, with ${name} circled` : "Every lake in the city as a dot"}
      className={className}
    >
      <path d={city.dots} className="stroke-ink" strokeOpacity={0.4} strokeWidth={city.width * 0.007} strokeLinecap="round" />
      {xy ? (
        <g className="stroke-ink" strokeWidth={2}>
          <circle cx={xy[0]} cy={xy[1]} r={ring} fill="none" vectorEffect="non-scaling-stroke" />
          <circle cx={xy[0]} cy={xy[1]} r={ring * 0.36} fill={sheetColor} vectorEffect="non-scaling-stroke" />
        </g>
      ) : null}
    </svg>
  );
}
