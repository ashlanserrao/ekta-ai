export const ROUND_ORDER = ["R32", "R16", "QF", "SF", "F"];

const ROUND_LABELS = {
  R32: "Round of 32",
  R16: "Round of 16",
  QF: "Quarter-Final",
  SF: "Semi-Final",
  F: "Final",
};

export const roundLabel = (code) => ROUND_LABELS[code] || code;

export const teamLabel = (team) => (team ? `${team.flag} ${team.name}` : "TBD");

// Formats the scoreline for display, including a penalty-shootout suffix
// when a knockout match was drawn after normal time (matches the
// "2 – 2 (4–3 pens)" convention already used elsewhere in the app).
export const formatScore = (match) => {
  if (match.scoreA == null || match.scoreB == null) return null;
  let s = `${match.scoreA} – ${match.scoreB}`;
  if (match.penalties) s += ` (${match.penalties.a}–${match.penalties.b} pens)`;
  return s;
};

export const statusText = (status) => {
  if (status === "live") return "Live now";
  if (status === "completed") return "Full-time";
  if (status === "tbd") return "Awaiting qualifiers";
  return "Upcoming";
};
