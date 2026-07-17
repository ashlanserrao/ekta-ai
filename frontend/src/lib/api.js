export const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000";

/**
 * Exchange the demo staff passcode for a signed JWT so the staff dashboard's
 * protected endpoints (alerts, copilot, chat) work. The landing-page login uses
 * a simple test/test gate for UX; this obtains the real token behind it.
 */
export async function staffLogin() {
  const passcode = import.meta.env.VITE_STAFF_PASSCODE || "fifa2026";
  const res = await fetch(`${API_BASE}/api/v1/auth/staff/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ passcode }),
  });
  if (!res.ok) {
    throw new Error("Staff authentication failed");
  }
  const data = await res.json();
  return data.token;
}
