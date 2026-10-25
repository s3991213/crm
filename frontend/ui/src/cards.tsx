import { useState, type FormEvent } from "react";
import {
  ArrowRight, CalendarClock, Check, CheckCircle2, CircleAlert, CircleX, Clock, Copy, GraduationCap, KeyRound,
  Loader2, Wallet, X,
} from "lucide-react";
import { api, ApiError } from "./api";
import { riskLevel, riskPercent, valueTone, type ChangeStatus, type Draft, type RiskRow, type Student, type Update } from "./reply";

function Pill({ value }: { value: string }) {
  const tone = valueTone(value);
  return <span className={`pill${tone ? ` pill--${tone}` : ""}`}>{value}</span>;
}

export function StudentCard({ student }: { student: Student }) {
  const { name, status, course, last_contact, payment_status } = student;
  return (
    <div className="card">
      <div className="card__head">
        <div className="avatar" aria-hidden="true">{(name || "?").trim().charAt(0).toUpperCase()}</div>
        <div className="card__title">
          <div className="card__name">{name || "Unknown student"}</div>
          {status && <Pill value={status} />}
        </div>
      </div>
      <dl className="facts">
        <div className="fact">
          <dt><GraduationCap size={16} /> Course</dt>
          <dd>{course || "Not recorded"}</dd>
        </div>
        <div className="fact">
          <dt><CalendarClock size={16} /> Last contact</dt>
          <dd>{last_contact || "No contact yet"}</dd>
        </div>
        <div className="fact">
          <dt><Wallet size={16} /> Payment</dt>
          <dd>{payment_status ? <Pill value={payment_status} /> : "Not recorded"}</dd>
        </div>
      </dl>
    </div>
  );
}

export function AtRiskTable({ students, onPick, disabled }:
  { students: RiskRow[]; onPick: (name: string) => void; disabled: boolean }) {
  return (
    <div className="card card--flush">
      <table className="table">
        <thead>
          <tr><th>Student</th><th>Risk</th><th>Main reasons</th></tr>
        </thead>
        <tbody>
          {students.map((s) => {
            const p = riskPercent(s.risk_score);
            const lv = riskLevel(p);
            return (
              <tr key={s.name}>
                <td data-label="Student">
                  <button type="button" className="link" disabled={disabled} title={`Summarise ${s.name}'s history`}
                          onClick={() => onPick(`Summarise ${s.name}'s history`)}>
                    {s.name}
                  </button>
                </td>
                <td data-label="Risk">
                  <div className="risk">
                    <span className={`pill${lv.tone ? ` pill--${lv.tone}` : ""}`}>{lv.label}</span>
                    <span className="risk__num">{p}%</span>
                  </div>
                </td>
                <td data-label="Main reasons">
                  <ul className="reasons">{(s.reasons ?? []).map((r) => <li key={r}>{r}</li>)}</ul>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
      <p className="footnote">Tap a name to see a summary of that student.</p>
    </div>
  );
}

function copyText(text: string): Promise<void> {
  if (navigator.clipboard && window.isSecureContext) return navigator.clipboard.writeText(text);
  // Plain-http office networks block the clipboard API, so fall back to the old way.
  const area = document.createElement("textarea");
  area.value = text;
  area.style.position = "fixed";
  area.style.opacity = "0";
  document.body.appendChild(area);
  area.select();
  document.execCommand("copy");
  document.body.removeChild(area);
  return Promise.resolve();
}

export function EmailDraft({ draft }: { draft: Draft }) {
  const [to, setTo] = useState(draft.to);
  const [subject, setSubject] = useState(draft.subject);
  const [body, setBody] = useState(draft.body);
  const [copied, setCopied] = useState(false);

  const onCopy = async () => {
    await copyText(subject ? `Subject: ${subject}\n\n${body}` : body);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="card">
      <div className="label">Draft email · not sent</div>
      <label className="field"><span>To</span><input value={to} onChange={(e) => setTo(e.target.value)} /></label>
      <label className="field"><span>Subject</span><input value={subject} onChange={(e) => setSubject(e.target.value)} /></label>
      <label className="field">
        <span>Message</span>
        <textarea rows={10} value={body} onChange={(e) => setBody(e.target.value)} />
      </label>
      <div className="actions">
        <button type="button" className="btn btn--primary" onClick={onCopy}>
          {copied ? <Check size={16} /> : <Copy size={16} />} {copied ? "Copied" : "Copy"}
        </button>
        <span className="footnote">Paste it into your email program to send.</span>
      </div>
    </div>
  );
}

const STATUS = {
  pending: { icon: Clock, text: "Waiting for you to confirm", tone: "pending" },
  busy: { icon: Loader2, text: "Working on it…", tone: "pending" },
  saved: { icon: CheckCircle2, text: "Saved", tone: "good" },
  cancelled: { icon: CircleX, text: "Cancelled, nothing changed", tone: "" },
  failed: { icon: CircleAlert, text: "Not saved", tone: "bad" },
};

export function ConfirmCard({ update, status, onResolve }:
  { update: Update; status: ChangeStatus; onResolve: (confirmed: boolean) => void }) {
  const s = STATUS[status];
  const Icon = s.icon;
  const shown = (v?: string | null) => (v === null || v === undefined || v === "" ? "(blank)" : String(v));
  return (
    <div className={`card confirm${status === "pending" ? " confirm--pending" : ""}`}>
      <div className="confirm__row"><span className="confirm__key">Student</span><span className="confirm__val">{update.student_name}</span></div>
      <div className="confirm__row"><span className="confirm__key">Field</span><span className="confirm__val">{update.field}</span></div>
      <div className="change">
        <span className="change__old">{shown(update.old_value)}</span>
        <ArrowRight size={18} className="change__arrow" />
        <span className="change__new">{shown(update.new_value)}</span>
      </div>
      {status === "pending" ? (
        <div className="actions">
          <button type="button" className="btn btn--primary" onClick={() => onResolve(true)}><Check size={16} /> Confirm</button>
          <button type="button" className="btn" onClick={() => onResolve(false)}><X size={16} /> Cancel</button>
        </div>
      ) : (
        <div className={`status${s.tone ? ` status--${s.tone}` : ""}`}>
          <Icon size={16} className={status === "busy" ? "spin" : undefined} /> {s.text}
        </div>
      )}
    </div>
  );
}

export function ChangePassword({ forced, onDone }: { forced: boolean; onDone: () => void }) {
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState(false);

  if (done) {
    return (
      <div className="card">
        <div className="status status--good"><CheckCircle2 size={16} /> Password changed. Use your new password next time you sign in.</div>
      </div>
    );
  }

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError("");
    if (next.length < 8) return setError("Please use at least 8 characters.");
    if (next !== confirm) return setError("The two new passwords don't match.");
    setBusy(true);
    try {
      await api.changePassword(forced ? null : current, next, confirm);
      setDone(true);
      onDone();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong. Please try again.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <form className="card password" onSubmit={onSubmit}>
      <div className="label"><KeyRound size={14} /> {forced ? "Choose your password" : "Change password"}</div>
      {!forced && (
        <label className="field">
          <span>Current password</span>
          <input type="password" autoComplete="current-password" value={current} onChange={(e) => setCurrent(e.target.value)} required />
        </label>
      )}
      <label className="field">
        <span>New password (at least 8 characters)</span>
        <input type="password" autoComplete="new-password" value={next} onChange={(e) => setNext(e.target.value)} required />
      </label>
      <label className="field">
        <span>Type the new password again</span>
        <input type="password" autoComplete="new-password" value={confirm} onChange={(e) => setConfirm(e.target.value)} required />
      </label>
      {error && <div className="status status--bad password__error"><CircleAlert size={16} /> {error}</div>}
      <button type="submit" className="btn btn--primary" disabled={busy}>{busy ? "Saving…" : "Save password"}</button>
    </form>
  );
}
