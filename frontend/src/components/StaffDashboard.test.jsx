import { describe, it, expect, beforeEach, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import StaffDashboard from "./StaffDashboard";

const zones = [
  { id: "Zone-C", name: "South Concourse C", type: "zone", capacity: 8000, current_crowd: 7200, density: 0.9 },
];
const gates = [
  { id: "Gate-3", name: "Gate 3 (South)", status: "open", congestion_level: "high", zone_id: "Zone-C" },
];
const alerts = [
  { id: "Zone-C", severity: "critical", message: "Critical crowd surge at South Concourse C.", recommended_action: "Halt inflow at Gate 3." },
];

const copilotReport = {
  provider: "groq",
  horizon_minutes: 5,
  summary: "South Concourse C is the primary pressure point and rising.",
  recommendations: [
    { priority: "high", zone: "South Concourse C", action: "Halt inflow at Gate 3 and open overflow routing." },
  ],
  risks: [
    { zone_id: "Zone-C", zone_name: "South Concourse C", current_density: 0.9, projected_density: 0.96, trend: "rising", eta_minutes: 2.4, feeding_gates: ["Gate 3 (South)"] },
  ],
};

describe("StaffDashboard", () => {
  beforeEach(() => {
    global.fetch = vi.fn(() =>
      Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve(copilotReport) })
    );
  });

  it("renders density cards and operational alerts", () => {
    render(<StaffDashboard zones={zones} alerts={alerts} gates={gates} token="t" onLogout={() => {}} />);
    expect(screen.getByText(/Live Crowd Densities/i)).toBeInTheDocument();
    expect(screen.getByText(/7200 \/ 8000/)).toBeInTheDocument();
    expect(screen.getByText(/Critical crowd surge/i)).toBeInTheDocument();
  });

  it("fetches and renders the Operations Copilot forecast and recommendations", async () => {
    render(<StaffDashboard zones={zones} alerts={alerts} gates={gates} token="t" onLogout={() => {}} />);

    expect(screen.getByRole("heading", { name: /Operations Copilot/i })).toBeInTheDocument();
    // Summary + recommendation arrive from the polled /copilot endpoint
    expect(await screen.findByText(/primary pressure point and rising/i)).toBeInTheDocument();
    expect(screen.getByText(/open overflow routing/i)).toBeInTheDocument();

    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/v1/staff/copilot"),
      expect.objectContaining({ headers: expect.objectContaining({ Authorization: "Bearer t" }) })
    );
  });
});
