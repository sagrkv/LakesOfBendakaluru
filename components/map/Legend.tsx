import { PAPERS } from "@/lib/valleys";
import Swatch from "./Swatch";

export default function Legend({ columns }: { columns: 1 | 2 }) {
  return (
    <div>
      <p className="label text-missing">Paper colour is the valley the lake’s water runs down.</p>
      <ul className={`mt-2 grid gap-x-4 gap-y-1 ${columns === 2 ? "grid-cols-2" : "grid-cols-1"}`}>
        {PAPERS.map((paper) => (
          <li key={paper.label} className="label flex items-center gap-2">
            <Swatch sheet={paper.sheet} />
            {paper.label}
          </li>
        ))}
        <li className="label flex items-center gap-2">
          <span aria-hidden className="inline-block h-0 w-3 shrink-0 border-t-2 border-ink" />
          Bengaluru Urban and North districts
        </li>
        <li className="label flex items-center gap-2">
          <span aria-hidden className="inline-block h-0 w-3 shrink-0 border-t-2 border-dashed border-ink" />
          Greater Bengaluru city limit
        </li>
      </ul>
    </div>
  );
}
