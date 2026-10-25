import { useState } from "react";
import { Button } from "@/components/ui/button";
import { CheckCircle2, CircleAlert, KeyRound } from "lucide-react";

export default function ChangePassword() {
  const forced = !!props.forced;
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState(false);

  if (done) {
    return (
      <div className="crm-card">
        <div className="crm-status crm-status--good">
          <CheckCircle2 size={16} /> Password changed. Use your new password next time you sign in.
        </div>
      </div>
    );
  }

  const onSubmit = async (e) => {
    e.preventDefault();
    setError("");
    if (next.length < 8) return setError("Please use at least 8 characters.");
    if (next !== confirm) return setError("The two new passwords don't match.");
    setBusy(true);
    try {
      const res = await callAction({
        name: "change_password",
        payload: { current, new: next, confirm },
      });
      const result = (res && res.response) || {};
      if (result.ok) setDone(true);
      else setError(result.error || "Something went wrong. Please try again.");
    } catch (err) {
      setError("Something went wrong. Please try again.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <form className="crm-card crm-password" onSubmit={onSubmit}>
      <div className="crm-draft__label">
        <KeyRound size={14} /> {forced ? "Choose your password" : "Change password"}
      </div>
      {!forced && (
        <label className="crm-field">
          <span>Current password</span>
          <input type="password" autoComplete="current-password" value={current}
                 onChange={(e) => setCurrent(e.target.value)} required />
        </label>
      )}
      <label className="crm-field">
        <span>New password (at least 8 characters)</span>
        <input type="password" autoComplete="new-password" value={next}
               onChange={(e) => setNext(e.target.value)} required />
      </label>
      <label className="crm-field">
        <span>Type the new password again</span>
        <input type="password" autoComplete="new-password" value={confirm}
               onChange={(e) => setConfirm(e.target.value)} required />
      </label>
      {error && (
        <div className="crm-status crm-status--bad crm-password__error">
          <CircleAlert size={16} /> {error}
        </div>
      )}
      <Button type="submit" className="crm-btn" disabled={busy}>
        {busy ? "Saving…" : "Save password"}
      </Button>
    </form>
  );
}
