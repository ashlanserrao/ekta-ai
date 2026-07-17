import { describe, it, expect, beforeEach, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import FanAssistant from "./FanAssistant";

// A fake streaming fetch response that closes immediately.
const fakeStreamResponse = () => ({
  ok: true,
  status: 200,
  body: {
    getReader: () => ({
      read: () => Promise.resolve({ done: true, value: undefined }),
    }),
  },
});

describe("FanAssistant", () => {
  beforeEach(() => {
    global.fetch = vi.fn(() => Promise.resolve(fakeStreamResponse()));
  });

  it("shows the welcome message and three prompt chips when empty", () => {
    render(<FanAssistant gates={[]} zones={[]} />);
    expect(screen.getByText(/Welcome to the World Cup 2026/i)).toBeInTheDocument();
    expect(screen.getByText(/Wheelchair route from Gate 2/i)).toBeInTheDocument();
    expect(screen.getByText(/accessible restrooms/i)).toBeInTheDocument();
    expect(screen.getByText(/halal food/i)).toBeInTheDocument();
  });

  it("localizes prompt chips and placeholder to French", () => {
    render(<FanAssistant gates={[]} zones={[]} />);
    fireEvent.change(screen.getByLabelText(/Select Assistant Language/i), {
      target: { value: "fr" },
    });
    expect(screen.getByText(/toilettes accessibles/i)).toBeInTheDocument();
    expect(screen.getByPlaceholderText(/Écrivez un message/i)).toBeInTheDocument();
  });

  it("sends the chip text (emoji stripped) and hides the chips after sending", async () => {
    render(<FanAssistant gates={[]} zones={[]} />);
    fireEvent.click(screen.getByText(/Wheelchair route from Gate 2/i));

    // The user message appears without the leading emoji...
    expect(
      await screen.findByText("Wheelchair route from Gate 2 to Section 204")
    ).toBeInTheDocument();
    // ...and it POSTs to the fan chat endpoint.
    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/v1/chat/fan"),
      expect.objectContaining({ method: "POST" })
    );
    // Chips are gone once a conversation has started.
    expect(screen.queryByText(/accessible restrooms/i)).not.toBeInTheDocument();
  });
});
