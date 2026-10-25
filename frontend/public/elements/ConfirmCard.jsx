import { ArrowRight, CheckCircle2, CircleAlert, CircleX, Clock } from "lucide-react";

const STATUS = {
  pending: { icon: Clock, text: "Waiting for you to confirm", cls: "crm-status crm-status--pending" },
  saved: { icon: CheckCircle2, text: "Saved", cls: "crm-status crm-status--good" },
  cancelled: { icon: CircleX, text: "Cancelled, nothing changed", cls: "crm-status" },
  failed: { icon: CircleAlert, text: "Not saved, something went wrong", cls: "crm-status crm-status--bad" },
};

export default function ConfirmCard() {
  const { student_name, field, old_value, new_value, status } = props;
  const s = STATUS[status] || STATUS.pending;
  const Icon = s.icon;
  const empty = (v) => (v === null || v === undefined || v === "" ? "(blank)" : String(v));

  return (
    <div className={`crm-card crm-confirm ${status === "pending" ? "crm-confirm--pending" : ""}`}>
      <div className="crm-confirm__row">
        <span className="crm-confirm__key">Student</span>
        <span className="crm-confirm__val">{student_name}</span>
      </div>
      <div className="crm-confirm__row">
        <span className="crm-confirm__key">Field</span>
        <span className="crm-confirm__val">{field}</span>
      </div>
      <div className="crm-change">
        <span className="crm-change__old">{empty(old_value)}</span>
        <ArrowRight size={18} className="crm-change__arrow" />
        <span className="crm-change__new">{empty(new_value)}</span>
      </div>
      <div className={s.cls}>
        <Icon size={16} /> {s.text}
      </div>
    </div>
  );
}
