import { KANNADA, SERIF } from "./metrics";

/**
 * Fits a lake's name inside the largest open area of its sheet (docs/brand/direction.md, "Opening screen").
 * Laptop: the room is 640 px wide and the name is set between 96 and 190 px.
 * Phone: the whole drawing is scaled so the room is 290 px, and the name scales with it.
 * The Kannada name is a quarter of the name size, never below 19 px so it stays large text on the sheet.
 */

export const ROOM_PX = 640;
export const ROOM_PX_PHONE = 290;
const PHONE = ROOM_PX_PHONE / ROOM_PX;

export const NAME_MIN = 96;
export const NAME_MAX = 190;
const MAX_LINES = 2;

export const NAME_LEADING = 0.86;
export const KANNADA_LEADING = 1.2;
/** Gap above the Kannada name, as a share of the name size. Clears the descenders, which hang 0.125 em below the last line. */
export const KANNADA_GAP = 0.16;
const DESCENDER = 0.125;
const KANNADA_FLOOR = 19;
/** Kerning is not measured, so lines keep 2% of the room free. */
const WIDTH_MARGIN = 0.98;

export type NameFit = {
  lines: string[];
  /** Name size in px on a laptop; the phone size is this times ROOM_PX_PHONE / ROOM_PX. */
  size: number;
  /** Widest line in px on a laptop. */
  width: number;
  /** Height of the name and Kannada name together, in px. */
  height: { laptop: number; phone: number };
  /** Set when the full name did not fit and a shorter form is shown. */
  fullName?: string;
};

function em(text: string, table: Map<string, number>, fallback: number): number {
  let total = 0;
  for (const char of text) total += table.get(char) ?? fallback;
  return total / 1000;
}

export const serifEm = (text: string) => em(text, SERIF, 600);
export const kannadaEm = (text: string) => em(text, KANNADA, 1000);

export function kannadaSize(nameSize: number, phone: boolean): number {
  return phone ? Math.max((nameSize * PHONE) / 4, KANNADA_FLOOR) : nameSize / 4;
}

function blockHeight(size: number, lines: number, hasKannada: boolean, phone: boolean): number {
  const s = phone ? size * PHONE : size;
  const name = lines * NAME_LEADING * s;
  if (!hasKannada) return name + DESCENDER * s;
  return name + KANNADA_GAP * s + KANNADA_LEADING * kannadaSize(size, phone);
}

/** The tallest block any name can make, so the slot under the buttons never moves. */
export const SLOT = {
  laptop: Math.ceil(blockHeight(NAME_MAX, MAX_LINES, true, false)),
  phone: Math.ceil(blockHeight(NAME_MAX, MAX_LINES, true, true)),
};

/** Every way to set the name in one or two lines, each with its widest line in em. */
function layouts(name: string): { lines: string[]; em: number }[] {
  const words = name.split(/\s+/).filter(Boolean);
  const options = [{ lines: [words.join(" ")], em: serifEm(words.join(" ")) }];
  if (MAX_LINES > 1) {
    for (let i = 1; i < words.length; i++) {
      const lines = [words.slice(0, i).join(" "), words.slice(i).join(" ")];
      options.push({ lines, em: Math.max(...lines.map(serifEm)) });
    }
  }
  return options;
}

function fitExactly(name: string, room: { w: number; h: number }, kannada?: string): NameFit | undefined {
  const heightLaptop = (room.h / room.w) * ROOM_PX;
  const heightPhone = heightLaptop * PHONE;
  const usable = ROOM_PX * WIDTH_MARGIN;
  const knEm = kannada ? kannadaEm(kannada) : 0;
  let best: NameFit | undefined;

  for (const option of layouts(name)) {
    const n = option.lines.length;
    // Largest whole px size this layout allows by width, then step down until it fits the height too.
    let size = Math.min(NAME_MAX, Math.floor(usable / option.em));
    for (; size >= NAME_MIN; size--) {
      const tallEnough =
        blockHeight(size, n, Boolean(kannada), false) <= heightLaptop &&
        blockHeight(size, n, Boolean(kannada), true) <= heightPhone;
      const kannadaFits =
        !kannada ||
        (knEm * kannadaSize(size, false) <= usable && knEm * kannadaSize(size, true) <= usable * PHONE);
      if (tallEnough && kannadaFits) break;
    }
    if (size < NAME_MIN) continue;
    // Bigger wins; at the same size fewer lines win because they come first.
    if (!best || size > best.size) {
      best = {
        lines: option.lines,
        size,
        width: option.em * size,
        height: {
          laptop: blockHeight(size, n, Boolean(kannada), false),
          phone: blockHeight(size, n, Boolean(kannada), true),
        },
      };
    }
  }
  return best;
}

/**
 * The full name if it fits; otherwise the name before its first slash, comma or bracket,
 * with the full name kept so the page can say it does not fit. Undefined when neither fits.
 */
export function fitName(name: string, room: { w: number; h: number }, kannada?: string): NameFit | undefined {
  const full = fitExactly(name, room, kannada);
  if (full) return full;
  const short = name.split(/\s*[/,(]\s*/)[0].trim();
  if (!short || short === name) return undefined;
  const fit = fitExactly(short, room, kannada);
  return fit && { ...fit, fullName: name };
}
