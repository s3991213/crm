// What the backend sends (see "Backend API contract" in README.md), and how each reply is shown.
// This file only decides presentation: every decision about records is made by the backend.

export interface Student {
  name: string;
  status?: string;
  course?: string;
  last_contact?: string;
  payment_status?: string;
}

export interface Update {
  update_id: string;
  student_name: string;
  field: string;
  old_value?: string | null;
  new_value?: string | null;
}

export interface RiskRow {
  name: string;
  risk_score: number;
  reasons?: string[];
}

export interface Draft {
  to: string;
  subject: string;
  body: string;
}

export interface Reply {
  type: string;
  text?: string;
  student?: Student;
  update?: Update;
  students?: RiskRow[];
  draft?: Draft;
}

export type ChangeStatus = "pending" | "busy" | "saved" | "cancelled" | "failed";

export type Item =
  | { kind: "staff"; text: string }
  | { kind: "text"; text: string; tone?: "bad" }
  | { kind: "student"; student: Student }
  | { kind: "change"; update: Update; text: string; status: ChangeStatus }
  | { kind: "atRisk"; text: string; students: RiskRow[] }
  | { kind: "draft"; draft: Draft; text: string }
  | { kind: "password"; forced: boolean };

export const CONFIRM_TEXT = "Please check this change. Nothing is saved until you click **Confirm**.";
export const UNCLEAR =
  "I'm not quite sure what you'd like me to do. Could you say it another way? " +
  'For example: *"Show me Priya Sharma\'s record"*.';
export const NO_RISK = "Good news: no students are flagged as at risk right now.";

export function atRiskItem(reply: Reply): Item {
  const students = [...(reply.students ?? [])]
    .sort((a, b) => (b.risk_score ?? 0) - (a.risk_score ?? 0))
    .map((s) => ({ ...s, reasons: (s.reasons ?? []).slice(0, 2) }));
  if (!students.length) return { kind: "text", text: NO_RISK };
  const text = reply.text?.trim() || `${students.length} students may need attention, highest risk first.`;
  return { kind: "atRisk", text, students };
}

/** The items one backend reply adds to the conversation, in order. */
export function toItems(reply: Reply): Item[] {
  const text = (reply.text ?? "").trim();
  const items: Item[] = [];
  if (reply.student) items.push({ kind: "student", student: reply.student });

  if (reply.type === "confirm_update" && reply.update) {
    items.push({ kind: "change", update: reply.update, text: text || CONFIRM_TEXT, status: "pending" });
  } else if (reply.type === "at_risk") {
    items.push(atRiskItem(reply));
  } else if (reply.type === "draft_email" && reply.draft) {
    items.push({ kind: "draft", draft: reply.draft, text: text || "Here's a draft. Edit anything you like, then copy it into your email." });
  } else if (reply.type === "change_password") {
    items.push({ kind: "text", text }, { kind: "password", forced: false });
  } else {
    items.push({ kind: "text", text: text || UNCLEAR });
  }
  return items;
}

/** Risk as a whole percentage: the backend may send 0-1 or 0-100. */
export function riskPercent(score: number): number {
  const n = Number(score) || 0;
  return Math.round(n <= 1 ? n * 100 : n);
}

export function riskLevel(p: number): { label: string; tone: string } {
  if (p >= 70) return { label: "High", tone: "bad" };
  if (p >= 40) return { label: "Medium", tone: "warn" };
  return { label: "Low", tone: "" };
}

export function valueTone(value?: string | null): string {
  const v = String(value ?? "").toLowerCase();
  if (/(overdue|unpaid|late|withdrawn|cancel)/.test(v)) return "bad";
  if (/(partial|pending|due|on hold|review|deferred)/.test(v)) return "warn";
  if (/(paid|active|enrolled|complete|approved)/.test(v)) return "good";
  return "";
}
