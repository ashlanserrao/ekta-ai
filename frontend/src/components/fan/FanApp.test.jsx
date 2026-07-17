import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import FanApp from "./FanApp";

const profile = {
  fullName: "Alex Morgan", email: "alex@ex.com", city: "Toronto",
  favoriteTeam: "Brazil", homeGate: "Gate 2", drink: "Water",
  dietary: "None", language: "English", accessibility: true,
};

const renderApp = (over = {}) =>
  render(
    <FanApp
      gates={[]} zones={[]} profile={profile}
      onLogout={over.onLogout || (() => {})}
      highContrast={false} largeText={false}
      setHighContrast={() => {}} setLargeText={() => {}}
    />
  );

describe("FanApp", () => {
  it("renders the sidebar nav and the map view by default", () => {
    renderApp();
    expect(screen.getByRole("button", { name: /Live Stadium Map/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Stats/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /My Ticket/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Match Schedule/i })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /Stadium Live Map/i })).toBeInTheDocument();
  });

  it("shows the collapsed chat launcher and opens the chat on click", async () => {
    renderApp();
    expect(screen.getByText(/Ask me anything/i)).toBeInTheDocument();
    fireEvent.click(screen.getByLabelText(/Open assistant/i));
    expect(await screen.findByText(/Welcome to the World Cup 2026/i)).toBeInTheDocument();
  });

  it("navigates to My Ticket and shows the holder's details", () => {
    renderApp();
    fireEvent.click(screen.getByRole("button", { name: /My Ticket/i }));
    expect(screen.getByText("Alex Morgan")).toBeInTheDocument();
    expect(screen.getByText(/MetLife Stadium/i)).toBeInTheDocument();
  });

  it("logs out when Log Out is clicked", () => {
    const onLogout = vi.fn();
    renderApp({ onLogout });
    fireEvent.click(screen.getByRole("button", { name: /Log Out/i }));
    expect(onLogout).toHaveBeenCalled();
  });
});
