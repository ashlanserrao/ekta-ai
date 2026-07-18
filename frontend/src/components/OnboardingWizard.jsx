import React, { useState, useEffect } from "react";
import { User, Goal, Ticket, Shield, Briefcase, Wrench, MapPin, CheckCircle2, AlertTriangle, X, ChevronDown } from "lucide-react";
import { staffLogin } from "../lib/api";

const FAN_STEPS = [
  {
    title: "About you", icon: User,
    fields: [
      { name: "fullName", label: "Full name", type: "text", required: true, placeholder: "Alex Morgan" },
      { name: "email", label: "Email", type: "email", placeholder: "alex@example.com" },
      { name: "city", label: "City", type: "text", placeholder: "Toronto" },
    ],
  },
  {
    title: "Your preferences", icon: Goal,
    fields: [
      { name: "favoriteTeam", label: "Favorite team", type: "text", placeholder: "Canada" },
      { name: "drink", label: "Drink preference", type: "select", options: ["No preference", "Water", "Soft drink", "Coffee", "Beer (21+)"] },
      { name: "dietary", label: "Dietary preference", type: "select", options: ["None", "Vegetarian", "Non-Vegetarian", "Vegan", "Gluten-Free", "Dairy-Free", "Nut Allergy"] },
    ],
  },
  {
    title: "Match-day setup", icon: Ticket,
    fields: [
      { name: "homeGate", label: "Home gate", type: "select", options: ["Gate 1", "Gate 2", "Gate 3", "Gate 4"] },
      { name: "language", label: "Preferred language", type: "select", options: ["English", "Español", "Français"] },
      { name: "accessibility", label: "I need step-free / accessible routes", type: "checkbox" },
    ],
  },
];

const STAFF_STEPS = [
  {
    title: "About you", icon: Briefcase,
    fields: [
      { name: "fullName", label: "Full name", type: "text", required: true, placeholder: "Sam Rivera" },
      { name: "staffId", label: "Staff ID", type: "text", placeholder: "OPS-1024" },
      { name: "email", label: "Work email", type: "email", placeholder: "sam@stadium.ops" },
    ],
  },
  {
    title: "Role details", icon: Wrench,
    fields: [
      { name: "department", label: "Department", type: "select", options: ["Operations", "Security", "Medical", "Guest Services", "Transport"] },
      { name: "jobTitle", label: "Job title", type: "text", placeholder: "Shift Supervisor" },
      { name: "shift", label: "Shift", type: "select", options: ["Morning", "Evening", "Night"] },
    ],
  },
  {
    title: "Assignment", icon: MapPin,
    fields: [
      { name: "zone", label: "Assigned zone", type: "select", options: ["Zone-A", "Zone-B", "Zone-C", "Zone-D", "Zone-VIP"] },
      { name: "gate", label: "Assigned gate", type: "select", options: ["Gate 1", "Gate 2", "Gate 3", "Gate 4"] },
      { name: "callSign", label: "Radio call sign", type: "text", placeholder: "Falcon-3" },
    ],
  },
];

const DRAFT_KEY = "ekta_onboarding_draft";
const readDraft = () => {
  try { return JSON.parse(sessionStorage.getItem(DRAFT_KEY) || "null"); } catch { return null; }
};

function Field({ field, value, onChange }) {
  if (field.type === "checkbox") {
    return (
      <label className="wizard-checkbox">
        <input type="checkbox" checked={!!value} onChange={(e) => onChange(e.target.checked)} />
        {field.label}
      </label>
    );
  }
  if (field.type === "select") {
    return (
      <div className="wizard-field">
        <label className="field-label">{field.label}</label>
        <span className="select-wrapper">
          <select className="form-select field-input" value={value ?? field.options[0]} onChange={(e) => onChange(e.target.value)}>
            {field.options.map((o) => <option key={o} value={o}>{o}</option>)}
          </select>
          <ChevronDown size={16} className="select-chevron" aria-hidden="true" />
        </span>
      </div>
    );
  }
  return (
    <div className="wizard-field">
      <label className="field-label">{field.label}{field.required ? " *" : ""}</label>
      <input
        type={field.type === "email" ? "email" : "text"}
        className="chat-input field-input"
        value={value ?? ""}
        placeholder={field.placeholder || ""}
        onChange={(e) => onChange(e.target.value)}
      />
    </div>
  );
}

export default function OnboardingWizard({ onClose, onComplete }) {
  const draft = readDraft();
  const [role, setRole] = useState(draft?.role ?? null); // 'fan' | 'staff'
  const [step, setStep] = useState(draft?.step ?? 0);
  const [form, setForm] = useState(draft?.form ?? {});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const steps = role === "staff" ? STAFF_STEPS : FAN_STEPS;
  const totalScreens = steps.length + 1; // + review
  const isReview = step === steps.length;
  const StepIcon = !isReview ? steps[step].icon : null;
  const set = (k, v) => setForm((f) => ({ ...f, [k]: v }));

  // Persist the in-progress draft so a stray click or reload never loses typed data.
  useEffect(() => {
    if (!role) { sessionStorage.removeItem(DRAFT_KEY); return; }
    sessionStorage.setItem(DRAFT_KEY, JSON.stringify({ role, step, form }));
  }, [role, step, form]);

  // The browser Back button is the only way to step backward through the wizard —
  // each forward step pushes a history entry, and popstate replays the prior one.
  useEffect(() => {
    window.history.pushState({ screen: "onboarding", role, step }, "");
    const handlePopState = (e) => {
      const state = e.state;
      if (state && state.screen === "onboarding") {
        setRole(state.role);
        setStep(state.step);
        setError("");
      } else {
        onClose();
      }
    };
    window.addEventListener("popstate", handlePopState);
    return () => window.removeEventListener("popstate", handlePopState);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const chooseRole = (r) => {
    setRole(r); setStep(0); setForm({}); setError("");
    window.history.pushState({ screen: "onboarding", role: r, step: 0 }, "");
  };

  const next = () => {
    const current = steps[step];
    if (current?.fields) {
      const missing = current.fields.find((f) => f.required && !String(form[f.name] || "").trim());
      if (missing) { setError(`${missing.label} is required.`); return; }
    }
    setError("");
    const newStep = Math.min(step + 1, steps.length);
    setStep(newStep);
    window.history.pushState({ screen: "onboarding", role, step: newStep }, "");
  };

  const goBack = () => { setError(""); window.history.back(); };

  const handleClose = () => {
    sessionStorage.removeItem(DRAFT_KEY);
    onClose();
  };

  const finish = async () => {
    setLoading(true);
    setError("");
    try {
      const profile = { role, ...form, createdAt: new Date().toISOString() };
      localStorage.setItem(`ekta_${role}_profile`, JSON.stringify(profile));
      sessionStorage.removeItem(DRAFT_KEY);
      if (role === "staff") {
        const token = await staffLogin();
        onComplete({ mode: "staff", profile, token });
      } else {
        onComplete({ mode: "fan", profile });
      }
    } catch {
      setError("Could not reach the operations backend. Please ensure it is running.");
      setLoading(false);
    }
  };

  return (
    <div className="modal-overlay" role="dialog" aria-modal="true" aria-label="Get started">
      <div className="modal-card wizard-card glass-panel" onClick={(e) => e.stopPropagation()}>
        <button className="modal-close" onClick={handleClose} aria-label="Close"><X size={20} /></button>

        {!role ? (
          <div className="role-picker">
            <h2 className="modal-title">Get Started</h2>
            <p className="modal-sub">Create your account. Who are you joining as?</p>
            <div className="role-options">
              <button className="role-option" onClick={() => chooseRole("fan")}>
                <span className="role-icon"><Ticket size={26} /></span>
                <span className="role-name">I'm a Fan</span>
                <span className="role-desc">Navigation, accessible routes, and multilingual match-day help.</span>
              </button>
              <button className="role-option" onClick={() => chooseRole("staff")}>
                <span className="role-icon"><Shield size={26} /></span>
                <span className="role-name">I'm Staff</span>
                <span className="role-desc">Live crowd intelligence, alerts, and the Operations Copilot.</span>
              </button>
            </div>
          </div>
        ) : (
          <>
            <div className="wizard-progress">
              {Array.from({ length: totalScreens }).map((_, i) => (
                <span key={i} className={`wizard-dot ${i === step ? "active" : ""} ${i < step ? "done" : ""}`} />
              ))}
            </div>

            {!isReview ? (
              <>
                <h2 className="modal-title">
                  <StepIcon size={20} style={{ verticalAlign: "-4px", marginRight: "0.4rem" }} />
                  {steps[step].title}
                </h2>
                <p className="modal-sub">Step {step + 1} of {totalScreens} · {role === "staff" ? "Staff" : "Fan"} setup</p>
                <div className="wizard-body">
                  {steps[step].fields.map((f) => (
                    <Field key={f.name} field={f} value={form[f.name]} onChange={(v) => set(f.name, v)} />
                  ))}
                </div>
              </>
            ) : (
              <>
                <h2 className="modal-title">
                  <CheckCircle2 size={20} style={{ verticalAlign: "-4px", marginRight: "0.4rem" }} />
                  Review & confirm
                </h2>
                <p className="modal-sub">Step {totalScreens} of {totalScreens} · confirm your details</p>
                <div className="wizard-review">
                  {steps.flatMap((s) => s.fields).map((f) => (
                    <div key={f.name} className="review-row">
                      <span className="review-key">{f.label}</span>
                      <span className="review-val">
                        {f.type === "checkbox" ? (form[f.name] ? "Yes" : "No") : (form[f.name] || "—")}
                      </span>
                    </div>
                  ))}
                </div>
              </>
            )}

            {error && <div className="form-error"><AlertTriangle size={14} style={{ verticalAlign: "-2px", marginRight: "0.3rem" }} />{error}</div>}

            <div className="wizard-actions">
              <button className="btn-secondary" onClick={goBack} disabled={loading}>
                {step === 0 ? "Back" : "Previous"}
              </button>
              {!isReview ? (
                <button className="btn-primary" onClick={next} disabled={loading}>Continue</button>
              ) : (
                <button className="btn-primary" onClick={finish} disabled={loading}>
                  {loading ? "Creating…" : `Create account & enter`}
                </button>
              )}
            </div>
          </>
        )}
      </div>
    </div>
  );
}
