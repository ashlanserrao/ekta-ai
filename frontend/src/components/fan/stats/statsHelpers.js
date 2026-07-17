export const initials = (name) =>
  (name || "").split(" ").map((w) => w[0]).slice(0, 2).join("").toUpperCase();

// .status-badge's classes are severity-named (low/medium/high = green/amber/red),
// so a "good" rating maps to the "low" (green) class — this helper is the single
// place that translates rating -> severity class.
export const ratingBadgeClass = (rating) => {
  if (rating >= 85) return "low";
  if (rating >= 70) return "medium";
  return "high";
};

export const formBadgeClass = (result) => {
  if (result === "W") return "low";
  if (result === "D") return "medium";
  return "high";
};

export const sortByKey = (rows, getValue, dir) => {
  const sorted = [...rows].sort((a, b) => {
    const av = getValue(a);
    const bv = getValue(b);
    if (typeof av === "string") return av.localeCompare(bv);
    return (av ?? 0) - (bv ?? 0);
  });
  return dir === "asc" ? sorted : sorted.reverse();
};
