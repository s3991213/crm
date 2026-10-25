import { CalendarClock, GraduationCap, Wallet } from "lucide-react";

function tone(value) {
  const v = String(value || "").toLowerCase();
  if (/(overdue|unpaid|late|withdrawn|cancel)/.test(v)) return "crm-pill crm-pill--bad";
  if (/(partial|pending|due|on hold|review)/.test(v)) return "crm-pill crm-pill--warn";
  if (/(paid|active|enrolled|complete|approved)/.test(v)) return "crm-pill crm-pill--good";
  return "crm-pill";
}

export default function StudentCard() {
  const { name, status, course, last_contact, payment_status } = props;
  return (
    <div className="crm-card">
      <div className="crm-card__head">
        <div className="crm-avatar" aria-hidden="true">
          {String(name || "?").trim().charAt(0).toUpperCase()}
        </div>
        <div className="crm-card__title">
          <div className="crm-card__name">{name || "Unknown student"}</div>
          {status && <span className={tone(status)}>{status}</span>}
        </div>
      </div>
      <dl className="crm-facts">
        <div className="crm-fact">
          <dt><GraduationCap size={16} /> Course</dt>
          <dd>{course || "Not recorded"}</dd>
        </div>
        <div className="crm-fact">
          <dt><CalendarClock size={16} /> Last contact</dt>
          <dd>{last_contact || "No contact yet"}</dd>
        </div>
        <div className="crm-fact">
          <dt><Wallet size={16} /> Payment</dt>
          <dd>{payment_status ? <span className={tone(payment_status)}>{payment_status}</span> : "Not recorded"}</dd>
        </div>
      </dl>
    </div>
  );
}
