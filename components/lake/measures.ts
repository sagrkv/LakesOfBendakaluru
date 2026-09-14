/** Names and units for water test measures. Technical names only appear in the readings tables. */

const NAMES: Record<string, string> = {
  temperature: "Water temperature",
  waterTemperature: "Water temperature",
  dissolvedOxygen: "Dissolved oxygen",
  ph: "pH",
  conductivity: "Conductivity",
  bod: "BOD",
  cod: "COD",
  nitrate: "Nitrate",
  nitrite: "Nitrite",
  nitrateNitrite: "Nitrate and nitrite",
  fecalColiform: "Faecal coliform",
  totalColiform: "Total coliform",
  fecalStreptococci: "Faecal streptococci",
  turbidity: "Turbidity",
  tds: "Dissolved solids",
  tss: "Suspended solids",
  tkn: "Kjeldahl nitrogen",
  totalKjeldahlNitrogen: "Kjeldahl nitrogen",
  ammoniacalNitrogen: "Ammonia nitrogen",
  freeAmmonia: "Free ammonia",
  totalAlkalinity: "Total alkalinity",
  phenolphthaleinAlkalinity: "Phenolphthalein alkalinity",
  totalHardness: "Total hardness",
  calciumHardness: "Calcium hardness",
  magnesiumHardness: "Magnesium hardness",
  sodiumPercent: "Sodium share",
  sar: "Sodium adsorption ratio",
  orthoPhosphate: "Orthophosphate",
  lightTransparency: "Light transparency",
};

/** Units the state board publishes; used for older tests too, which follow the same standard methods. */
const DEFAULT_UNITS: Record<string, string> = {
  temperature: "°C",
  waterTemperature: "°C",
  dissolvedOxygen: "mg/L",
  conductivity: "µS/cm",
  bod: "mg/L",
  cod: "mg/L",
  nitrate: "mg/L as N",
  nitrateNitrite: "mg/L as N",
  fecalColiform: "MPN/100mL",
  totalColiform: "MPN/100mL",
  turbidity: "NTU",
  tds: "mg/L",
  tss: "mg/L",
  tkn: "mg/L as N",
  lightTransparency: "cm",
};

const UNIT_TEXT: Record<string, string> = { degC: "°C", "uS/cm": "µS/cm" };

export function measureName(key: string): string {
  if (NAMES[key]) return NAMES[key];
  const words = key.replace(/([A-Z])/g, " $1").toLowerCase();
  return words.charAt(0).toUpperCase() + words.slice(1);
}

export function measureUnit(key: string, units?: Record<string, string>): string {
  const unit = units?.[key] ?? DEFAULT_UNITS[key] ?? "";
  return UNIT_TEXT[unit] ?? unit;
}

export function formatReading(n: number): string {
  return n.toLocaleString("en-IN", { maximumFractionDigits: 3 });
}

/** Station names arrive in capitals from some reports. */
export function tidyPlace(text: string): string {
  if (text !== text.toUpperCase()) return text;
  return text.toLowerCase().replace(/(^|\s)\S/g, (c) => c.toUpperCase());
}

const STATISTIC: Record<string, string> = { min: "Lowest", max: "Highest", mean: "Average", avg: "Average" };

export function statisticName(s: string): string {
  return STATISTIC[s.toLowerCase()] ?? s;
}
