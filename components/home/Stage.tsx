import Link from "next/link";
import type { CSSProperties } from "react";
import Cutout from "@/components/paper/Cutout";
import type { Sheet } from "@/lib/lake";
import type { Paper } from "@/lib/valleys";
import {
  KANNADA_GAP,
  KANNADA_LEADING,
  NAME_LEADING,
  ROOM_PX,
  ROOM_PX_PHONE,
  kannadaEm,
  kannadaSize,
  type NameFit,
} from "./fit";
import styles from "./home.module.css";

const px = (n: number) => `${Math.round(n * 100) / 100}px`;

/** Where the sheet sits and scales for one screen size, in CSS px relative to the name block. */
function placement(sheet: Sheet, roomPx: number, blockHeight: number) {
  const k = roomPx / sheet.room.w;
  const roomTop = (blockHeight - sheet.room.h * k) / 2;
  return {
    k,
    left: -sheet.room.x * k,
    top: roomTop - sheet.room.y * k,
    width: sheet.w * k,
    height: sheet.h * k,
    // The room's centre, so the sheet settles around the name instead of drifting under it.
    origin: `${px((sheet.room.x + sheet.room.w / 2) * k)} ${px((sheet.room.y + sheet.room.h / 2) * k)}`,
  };
}

/**
 * The end-to-end measure, drawn in the sheet's text colour so the dots pass 3:1 on it.
 * It breaks around the name block so it never runs through the letters.
 */
function Span({
  sheet,
  k,
  block,
  id,
  color,
  className,
}: {
  sheet: Sheet;
  k: number;
  block: { width: number; height: number };
  id: string;
  color: string;
  className: string;
}) {
  const { span, room } = sheet;
  const pad = 16 / k;
  const w = block.width / k + 2 * pad;
  const h = block.height / k + 2 * pad;
  const x = room.x - pad;
  const y = room.y + (room.h - block.height / k) / 2 - pad;
  const hole = `M${-sheet.w} ${-sheet.h}H${2 * sheet.w}V${2 * sheet.h}H${-sheet.w}Z M${x} ${y}h${w}v${h}h${-w}Z`;

  return (
    <g className={className}>
      <clipPath id={id}>
        <path d={hole} clipRule="evenodd" />
      </clipPath>
      <g clipPath={`url(#${id})`} fill={color} stroke={color}>
        <line
          x1={span.x1}
          y1={span.y1}
          x2={span.x2}
          y2={span.y2}
          strokeWidth={3 / k}
          strokeLinecap="round"
          strokeDasharray={`0 ${9 / k}`}
          fill="none"
        />
        <circle cx={span.x1} cy={span.y1} r={5 / k} stroke="none" />
        <circle cx={span.x2} cy={span.y2} r={5 / k} stroke="none" />
      </g>
    </g>
  );
}

/**
 * The lake cut out at its real outline, scaled so its largest open area is 640 px wide on a laptop
 * and 290 px on a phone, with the fitted name set inside that area. The sheet runs off the page.
 */
export default function Stage({
  id,
  name,
  nameKannada,
  sheet,
  valley,
  paper,
  fit,
}: {
  id: string;
  name: string;
  nameKannada?: string;
  sheet: Sheet;
  valley?: string;
  paper: Paper;
  fit: NameFit;
}) {
  const laptop = placement(sheet, ROOM_PX, fit.height.laptop);
  const phone = placement(sheet, ROOM_PX_PHONE, fit.height.phone);
  const phoneScale = ROOM_PX_PHONE / ROOM_PX;
  const knEm = nameKannada ? kannadaEm(nameKannada) : 0;
  const blockWidth = (kSize: number, nameScale: number) => Math.max(fit.width * nameScale, knEm * kSize);

  const vars = {
    "--block": px(fit.height.laptop),
    "--block-p": px(fit.height.phone),
    "--name": px(fit.size),
    "--name-p": px(fit.size * phoneScale),
    "--kn": px(kannadaSize(fit.size, false)),
    "--kn-p": px(kannadaSize(fit.size, true)),
    "--kn-gap": px(fit.size * KANNADA_GAP),
    "--kn-gap-p": px(fit.size * phoneScale * KANNADA_GAP),
    "--sx": px(laptop.left),
    "--sy": px(laptop.top),
    "--sw": px(laptop.width),
    "--sh": px(laptop.height),
    "--so": laptop.origin,
    "--sx-p": px(phone.left),
    "--sy-p": px(phone.top),
    "--sw-p": px(phone.width),
    "--sh-p": px(phone.height),
    "--so-p": phone.origin,
  } as CSSProperties;

  // Sheet and measure share one box so they settle together around the room.
  const box =
    "absolute -z-10 max-w-none left-(--sx-p) top-(--sy-p) w-(--sw-p) h-(--sh-p) [transform-origin:var(--so-p)] md:left-(--sx) md:top-(--sy) md:w-(--sw) md:h-(--sh) md:[transform-origin:var(--so)]";

  return (
    <div className="relative w-[290px] h-(--block-p) md:w-[640px] md:h-(--block)" style={vars}>
      <Cutout sheet={sheet} valley={valley} lands aria-hidden="true" className={box} />
      <svg
        viewBox={`0 0 ${sheet.w} ${sheet.h}`}
        overflow="visible"
        aria-hidden="true"
        className={`${box} ${styles.print}`}
      >
        <Span
          sheet={sheet}
          k={phone.k}
          block={{ width: blockWidth(kannadaSize(fit.size, true), phoneScale), height: fit.height.phone }}
          id={`${id}-span-phone`}
          color={paper.text}
          className="md:hidden"
        />
        <Span
          sheet={sheet}
          k={laptop.k}
          block={{ width: blockWidth(kannadaSize(fit.size, false), 1), height: fit.height.laptop }}
          id={`${id}-span`}
          color={paper.text}
          className="hidden md:inline"
        />
      </svg>

      <div className={`absolute inset-0 origin-center ${styles.print}`} style={{ color: paper.text }}>
        <h1
          id="lake-name"
          className="font-serif font-normal [font-size:var(--name-p)] md:[font-size:var(--name)]"
          style={{ lineHeight: NAME_LEADING }}
        >
          <Link
            href={`/lake/${id}`}
            // Inline so the focus ring takes the sheet's text colour; the global ring is ink.
            style={{ outlineColor: paper.text }}
            className="block w-fit decoration-[0.04em] underline-offset-[0.08em] hover:underline active:translate-y-0.5"
          >
            {fit.lines.map((line, i) => (
              <span key={i} className="block whitespace-nowrap">
                {line}
                {i < fit.lines.length - 1 ? " " : null}
              </span>
            ))}
            {fit.fullName ? <span className="sr-only">, full name {name}</span> : null}
          </Link>
        </h1>
        {nameKannada ? (
          <p
            lang="kn"
            className="font-kannada font-semibold whitespace-nowrap [font-size:var(--kn-p)] [margin-top:var(--kn-gap-p)] md:[font-size:var(--kn)] md:[margin-top:var(--kn-gap)]"
            style={{ lineHeight: KANNADA_LEADING }}
          >
            {nameKannada}
          </p>
        ) : null}
      </div>
    </div>
  );
}
