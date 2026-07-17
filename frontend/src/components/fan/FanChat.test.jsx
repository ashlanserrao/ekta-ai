import { describe, it, expect, beforeEach, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import FanChat from "./FanChat";

const fakeStreamResponse = () => ({
  ok: true,
  status: 200,
  body: { getReader: () => ({ read: () => Promise.resolve({ done: true, value: undefined }) }) },
});

describe("FanChat", () => {
  beforeEach(() => {
    global.fetch = vi.fn(() => Promise.resolve(fakeStreamResponse()));
  });

  it("shows the welcome message and three prompt chips when empty", () => {
    render(<FanChat onRoute={() => {}} />);
    expect(screen.getByText(/Welcome to the World Cup 2026/i)).toBeInTheDocument();
    expect(screen.getByText(/Wheelchair route from Gate 2/i)).toBeInTheDocument();
    expect(screen.getByText(/accessible restrooms/i)).toBeInTheDocument();
    expect(screen.getByText(/halal food/i)).toBeInTheDocument();
  });

  it("localizes prompt chips and placeholder to French", () => {
    render(<FanChat onRoute={() => {}} />);
    fireEvent.change(screen.getByLabelText(/Select Assistant Language/i), { target: { value: "fr" } });
    expect(screen.getByText(/toilettes accessibles/i)).toBeInTheDocument();
    expect(screen.getByPlaceholderText(/Écrivez un message/i)).toBeInTheDocument();
  });

  it("sends the chip text (emoji stripped) and hides the chips after sending", async () => {
    render(<FanChat onRoute={() => {}} />);
    fireEvent.click(screen.getByText(/Wheelchair route from Gate 2/i));

    expect(await screen.findByText("Wheelchair route from Gate 2 to Section 204")).toBeInTheDocument();
    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/v1/chat/fan"),
      expect.objectContaining({ method: "POST" })
    );
    expect(screen.queryByText(/accessible restrooms/i)).not.toBeInTheDocument();
  });
});
