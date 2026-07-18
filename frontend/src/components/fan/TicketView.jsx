import React, { useMemo } from "react";
import { MapPin } from "lucide-react";

export default function TicketView({ profile }) {
  const p = profile || {};

  const ticket = useMemo(() => {
    const rand = (n) => Math.floor(Math.random() * n);
    const sections = ["102", "105", "204", "305"];
    const home = p.favoriteTeam && p.favoriteTeam !== "—" ? p.favoriteTeam : "Argentina";
    const away = home === "Brazil" ? "France" : "Brazil";
    return {
      home,
      away,
      section: sections[rand(sections.length)],
      row: String.fromCharCode(65 + rand(20)),
      seat: 1 + rand(40),
      gate: p.homeGate || "Gate 1",
      id: "WC26-" + (100000 + rand(900000)),
      category: "Category 1",
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [p.favoriteTeam, p.homeGate]);

  const holder = p.fullName || "Guest Fan";

  return (
    <div className="fan-view">
      <div className="view-heading">
        <h1>My Ticket</h1>
        <p>Your match-day pass. Present the QR code at your gate.</p>
      </div>

      <div className="ticket">
        <div className="ticket-main">
          <div className="ticket-top">
            <div className="ticket-badge">EKTA 26</div>
            <span className="ticket-comp">FIFA World Cup 2026</span>
          </div>

          <div className="ticket-match">
            <div className="ticket-team">
              <span className="ticket-team-name">{ticket.home}</span>
            </div>
            <span className="ticket-vs">VS</span>
            <div className="ticket-team">
              <span className="ticket-team-name">{ticket.away}</span>
            </div>
          </div>

          <div className="ticket-stage-row">
            <span className="ticket-stage">The Final</span>
            <span className="ticket-datetime">Sun, Jul 19 2026 · 15:00</span>
          </div>

          <div className="ticket-venue"><MapPin size={14} style={{ verticalAlign: "-2px", marginRight: "0.3rem" }} />MetLife Stadium, New Jersey</div>

          <div className="ticket-holder">
            <div>
              <span className="ticket-label">Ticket Holder</span>
              <span className="ticket-value">{holder}</span>
            </div>
            <div>
              <span className="ticket-label">Category</span>
              <span className="ticket-value">{ticket.category}</span>
            </div>
          </div>
        </div>

        <div className="ticket-stub">
          <div className="ticket-stub-grid">
            <div><span className="ticket-label">Gate</span><span className="ticket-value big">{ticket.gate.replace("Gate ", "")}</span></div>
            <div><span className="ticket-label">Section</span><span className="ticket-value big">{ticket.section}</span></div>
            <div><span className="ticket-label">Row</span><span className="ticket-value big">{ticket.row}</span></div>
            <div><span className="ticket-label">Seat</span><span className="ticket-value big">{ticket.seat}</span></div>
          </div>
          <div className="ticket-barcode" aria-hidden="true">
            {Array.from({ length: 40 }).map((_, i) => (
              <span key={i} style={{ width: (i % 3 === 0 ? 3 : i % 2 === 0 ? 1 : 2) + "px" }} />
            ))}
          </div>
          <div className="ticket-id">{ticket.id}</div>
        </div>
      </div>
    </div>
  );
}
