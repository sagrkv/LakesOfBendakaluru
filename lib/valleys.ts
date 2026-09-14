/**
 * The paper a lake is cut from is the colour of the valley its water runs down.
 * The named sheets are the valleys with the most lakes; smaller basins share one sheet.
 * Text colours are the ones that pass 3:1 on the sheet for large text (docs/brand/direction.md).
 */

export type Paper = { sheet: string; text: string; label: string };

const CREAM = "#F6EEDB";
const INK = "#1B1A17";

const NAMED: Record<string, Paper> = {
  "Koramangala-Challaghatta": { sheet: "#F2502B", text: CREAM, label: "Koramangala-Challaghatta" },
  Hebbal: { sheet: "#FFC933", text: INK, label: "Hebbal" },
  Vrishabhavathi: { sheet: "#2FA35B", text: INK, label: "Vrishabhavathi" },
  "Dakshina Pinakini": { sheet: "#F59AC0", text: INK, label: "Dakshina Pinakini" },
  Suvarnamukhi: { sheet: "#7B4BD1", text: CREAM, label: "Suvarnamukhi" },
  Arkavathi: { sheet: "#FF8A1F", text: INK, label: "Arkavathi" },
};

export const OTHER_VALLEYS: Paper = { sheet: "#11A3B5", text: INK, label: "Other valleys" };
export const NO_VALLEY: Paper = { sheet: "#1F48D6", text: CREAM, label: "No valley on record" };

/** Every sheet in legend order. */
export const PAPERS: Paper[] = [...Object.values(NAMED), OTHER_VALLEYS, NO_VALLEY];

export function paperFor(valley: string | undefined): Paper {
  if (!valley) return NO_VALLEY;
  return NAMED[valley] ?? OTHER_VALLEYS;
}

/** A MapLibre expression that colours a feature by its `valley` property. */
export function valleyColorExpression(): unknown[] {
  return [
    "match",
    ["coalesce", ["get", "valley"], ""],
    ...Object.entries(NAMED).flatMap(([name, paper]) => [name, paper.sheet]),
    "",
    NO_VALLEY.sheet,
    OTHER_VALLEYS.sheet,
  ];
}
