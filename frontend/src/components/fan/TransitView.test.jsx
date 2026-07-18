import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen } from "@testing-library/react";
import TransitView from "./TransitView";

const transitPayload = {
  lines: [
    {
      id: "Line-M1", name: "Metro Line 1", mode: "metro", destination: "Downtown Central",
      headway_minutes: 5, capacity_per_departure: 900, current_load: 0.55, status: "on_time",
      minutes_to_next: 3.2, crowding: "medium", co2_saved_kg_per_trip: 2.4,
    },
    {
      id: "BRT-3", name: "Bus Rapid Transit 3", mode: "bus", destination: "University District",
      headway_minutes: 6, capacity_per_departure: 120, current_load: 0.4, status: "delayed",
      minutes_to_next: 1.5, crowding: "medium", co2_saved_kg_per_trip: 1.6,
    },
  ],
  advisory: {
    generated_at: 1, provider: "mock",
    summary: "Metro Line 1 toward Downtown Central is your best way home right now.",
    tips: ["Taking the metro saves about 2.4 kg of CO2 per person on this trip."],
  },
  egress_capacity_per_minute: 120,
  timestamp: 1,
};

describe("TransitView", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn(() =>
      Promise.resolve({ ok: true, json: () => Promise.resolve(transitPayload) })
    ));
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("shows a loading state before data arrives", () => {
    vi.stubGlobal("fetch", vi.fn(() => new Promise(() => {})));
    render(<TransitView />);
    expect(screen.getByText(/Connecting to live transit feed/i)).toBeInTheDocument();
  });

  it("renders lines, the AI advisory, and the sustainability nudge", async () => {
    render(<TransitView />);
    expect(await screen.findByText("Metro Line 1")).toBeInTheDocument();
    expect(screen.getByText("Bus Rapid Transit 3")).toBeInTheDocument();
    expect(screen.getByText(/best way home right now/i)).toBeInTheDocument();
    expect(screen.getByText(/2.4 kg of CO2/i)).toBeInTheDocument();
    expect(screen.getByText(/Delayed/i)).toBeInTheDocument();
    expect(screen.getByText(/120 passengers \/ minute/i)).toBeInTheDocument();
  });
});
