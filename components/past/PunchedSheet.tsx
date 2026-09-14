export type Hole = { id: string; x: number; y: number; r: number };

/**
 * A sheet of ink paper with holes punched through it. Through each hole you see the table,
 * and the sheet's own shadow falls into the hole along its upper-left edge.
 */
export default function PunchedSheet({
  id,
  width,
  height,
  holes,
  dots = [],
  label,
  className = "",
}: {
  /** Unique on the page; names the mask. */
  id: string;
  width: number;
  height: number;
  holes: Hole[];
  dots?: { id: string; x: number; y: number }[];
  label: string;
  className?: string;
}) {
  const mask = `${id}-holes`;
  return (
    <svg
      viewBox={`0 0 ${width} ${height}`}
      role="img"
      aria-label={label}
      className={`lands origin-center sheet-shadow block h-auto ${className}`}
    >
      <defs>
        <mask id={mask} maskUnits="userSpaceOnUse" x="0" y="0" width={width} height={height}>
          <rect width={width} height={height} fill="white" />
          {holes.map((hole) => (
            <circle key={hole.id} cx={hole.x} cy={hole.y} r={hole.r} fill="black" />
          ))}
        </mask>
      </defs>
      <rect width={width} height={height} mask={`url(#${mask})`} className="fill-ink" />
      {dots.length > 0 && (
        <g className="fill-table" opacity={0.3}>
          {dots.map((dot) => (
            <circle key={dot.id} cx={dot.x} cy={dot.y} r={1.4} />
          ))}
        </g>
      )}
    </svg>
  );
}
