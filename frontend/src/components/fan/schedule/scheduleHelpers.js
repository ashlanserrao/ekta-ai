export const ROUND_ORDER = ["R32", "R16", "QF", "SF", "F"];

const ROUND_LABEL_KEYS = {
  R32: "schedule.roundR32",
  R16: "schedule.roundR16",
  QF: "schedule.roundQF",
  SF: "schedule.roundSF",
  F: "schedule.roundF",
};

// `t` is the translate function from useTranslation() - these are plain
// helpers (not components), so the caller passes it in rather than us
// calling the hook here.
export const roundLabel = (code, t) => (ROUND_LABEL_KEYS[code] ? t(ROUND_LABEL_KEYS[code]) : code);

export const teamLabel = (team, t) => (team ? `${team.flag} ${team.name}` : t("schedule.tbd"));

// Formats the scoreline for display, including a penalty-shootout suffix
// when a knockout match was drawn after normal time (matches the
// "2 – 2 (4–3 pens)" convention already used elsewhere in the app).
export const formatScore = (match) => {
  if (match.scoreA == null || match.scoreB == null) return null;
  let s = `${match.scoreA} – ${match.scoreB}`;
  if (match.penalties) s += ` (${match.penalties.a}–${match.penalties.b} pens)`;
  return s;
};

export const statusText = (status, t) => {
  if (status === "live") return t("schedule.statusLive");
  if (status === "completed") return t("schedule.statusFullTime");
  if (status === "tbd") return t("schedule.statusAwaitingQualifiers");
  return t("schedule.statusUpcoming");
};
