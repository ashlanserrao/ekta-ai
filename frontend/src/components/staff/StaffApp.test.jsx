import { describe, it, expect, beforeEach, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import StaffApp from "./StaffApp";

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

const renderApp = (over = {}) =>
  render(
    <StaffApp
      zones={zones} alerts={alerts} gates={gates} token="t"
      onLogout={over.onLogout || (() => {})}
      highContrast={false} largeText={false}
      setHighContrast={() => {}} setLargeText={() => {}}
    />
  );

describe("StaffApp", () => {
  beforeEach(() => {
    global.fetch = vi.fn(() =>
      Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve(copilotReport) })
    );
  });

  it("renders the sidebar nav and the Operations Copilot view by default", async () => {
    renderApp();
    expect(screen.getByRole("button", { name: /Operations Copilot/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Live Crowd/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Stadium Live Map/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Live Alerts/i })).toBeInTheDocument();
    expect(await screen.findByText(/primary pressure point and rising/i)).toBeInTheDocument();
  });

  it("navigates to Live Crowd and shows density cards", () => {
    renderApp();
    fireEvent.click(screen.getByRole("button", { name: /Live Crowd/i }));
    expect(screen.getByText(/Live Crowd Densities/i)).toBeInTheDocument();
    expect(screen.getByText(/7200 \/ 8000/)).toBeInTheDocument();
  });

  it("navigates to Live Alerts and shows the alert log", () => {
    renderApp();
    fireEvent.click(screen.getByRole("button", { name: /Live Alerts/i }));
    expect(screen.getByText(/Critical crowd surge/i)).toBeInTheDocument();
  });

  it("shows the collapsed chat launcher and opens the Decision Support Console on click", async () => {
    renderApp();
    fireEvent.click(screen.getByLabelText(/Open Staff Decision Support Console/i));
    expect(await screen.findByText(/Operations Intelligence Portal Active/i)).toBeInTheDocument();
  });

  it("logs out when Log Out is clicked", () => {
    const onLogout = vi.fn();
    renderApp({ onLogout });
    fireEvent.click(screen.getByRole("button", { name: /Log Out/i }));
    expect(onLogout).toHaveBeenCalled();
  });
});
