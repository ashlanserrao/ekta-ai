import { describe, it, expect } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { LanguageProvider } from "./LanguageContext";
import FanApp from "../components/fan/FanApp";
import StaffApp from "../components/staff/StaffApp";

const profile = {
  fullName: "Alex Morgan", email: "alex@ex.com", city: "Toronto",
  favoriteTeam: "Brazil", homeGate: "Gate 2", drink: "Water",
  dietary: "None", language: "Español", accessibility: true,
};

describe("LanguageProvider", () => {
  it("renders the Fan Portal nav and headings in Spanish when wrapped with lang='es'", () => {
    render(
      <LanguageProvider lang="es">
        <FanApp
          gates={[]} zones={[]} profile={profile}
          onLogout={() => {}} highContrast={false} largeText={false}
          setHighContrast={() => {}} setLargeText={() => {}}
        />
      </LanguageProvider>
    );
    expect(screen.getByRole("button", { name: /Mapa del Estadio en Vivo/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Mi Entrada/i })).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /Perfil/i }));
    expect(screen.getByRole("heading", { name: /Perfil/i })).toBeInTheDocument();
    expect(screen.getByText(/Correo electrónico/i)).toBeInTheDocument();
  });

  it("renders the Staff Portal nav in French when wrapped with lang='fr'", () => {
    render(
      <LanguageProvider lang="fr">
        <StaffApp
          zones={[]} alerts={[]} gates={[]} token="t"
          onLogout={() => {}} highContrast={false} largeText={false}
          setHighContrast={() => {}} setLargeText={() => {}}
        />
      </LanguageProvider>
    );
    expect(screen.getByRole("button", { name: /Copilote des Opérations/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Affluence en Direct/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Se Déconnecter/i })).toBeInTheDocument();
  });

  it("falls back to English for an unrecognized language code", () => {
    render(
      <LanguageProvider lang="de">
        <FanApp
          gates={[]} zones={[]} profile={profile}
          onLogout={() => {}} highContrast={false} largeText={false}
          setHighContrast={() => {}} setLargeText={() => {}}
        />
      </LanguageProvider>
    );
    expect(screen.getByRole("button", { name: /Live Stadium Map/i })).toBeInTheDocument();
  });

  it("renders in English when no LanguageProvider wraps the component at all", () => {
    render(
      <FanApp
        gates={[]} zones={[]} profile={{ ...profile, language: "English" }}
        onLogout={() => {}} highContrast={false} largeText={false}
        setHighContrast={() => {}} setLargeText={() => {}}
      />
    );
    expect(screen.getByRole("button", { name: /Live Stadium Map/i })).toBeInTheDocument();
  });
});
