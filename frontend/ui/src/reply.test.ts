import { describe, expect, it } from "vitest";
import { atRiskItem, CONFIRM_TEXT, NO_LEADS, NO_RISK, riskLevel, riskPercent, toItems, UNCLEAR, valueTone } from "./reply";

const liam = { name: "Liam Nguyen", status: "Active", course: "Certificate IV in IT", last_contact: "2026-09-02", payment_status: "Overdue" };

describe("toItems", () => {
  it("puts the student card above the answer", () => {
    expect(toItems({ type: "answer", text: "Here he is.", student: liam }).map((i) => i.kind)).toEqual(["student", "text"]);
  });

  it("shows a staged change as pending, with fixed wording when the text is empty", () => {
    const update = { update_id: "u1", student_name: "Liam Nguyen", field: "Status", old_value: "Active", new_value: "Withdrawn" };
    const [card, change] = toItems({ type: "confirm_update", text: "", student: liam, update });
    expect(card.kind).toBe("student");
    expect(change).toEqual({ kind: "change", update, text: CONFIRM_TEXT, status: "pending" });
  });

  it("asks staff to rephrase for an unknown type or no text", () => {
    expect(toItems({ type: "something_new" })).toEqual([{ kind: "text", text: UNCLEAR }]);
    expect(toItems({ type: "answer", text: "  " })).toEqual([{ kind: "text", text: UNCLEAR }]);
  });

  it("never shows a change card without an update", () => {
    expect(toItems({ type: "confirm_update", text: "Saved!" }).map((i) => i.kind)).toEqual(["text"]);
  });

  it("shows the password form when asked, without involving the backend", () => {
    expect(toItems({ type: "change_password", text: "Sure." }).map((i) => i.kind)).toEqual(["text", "password"]);
  });

  it("shows drafts with their text", () => {
    const draft = { to: "liam@example.com", subject: "Hi", body: "Hello" };
    expect(toItems({ type: "draft_email", text: "Here you go.", draft })).toEqual([{ kind: "draft", draft, text: "Here you go." }]);
  });
});

describe("at-risk", () => {
  it("sorts by risk and keeps two reasons", () => {
    const item = atRiskItem({ type: "at_risk", students: [
      { name: "A", risk_score: 0.4, reasons: ["x"] },
      { name: "B", risk_score: 0.9, reasons: ["1", "2", "3"] },
    ] });
    expect(item.kind === "atRisk" && item.students.map((s) => [s.name, s.reasons])).toEqual([["B", ["1", "2"]], ["A", ["x"]]]);
    expect(item.kind === "atRisk" && item.text).toBe("2 students may need attention, highest risk first.");
  });

  it("says so when nobody is at risk", () => {
    expect(atRiskItem({ type: "at_risk", students: [] })).toEqual({ kind: "text", text: NO_RISK });
  });

  it("accepts scores as 0-1 or 0-100", () => {
    expect(riskPercent(0.84)).toBe(84);
    expect(riskPercent(84)).toBe(84);
    expect(riskLevel(84).label).toBe("High");
    expect(riskLevel(45).label).toBe("High");
    expect(riskLevel(25).label).toBe("Medium");
    expect(riskLevel(10).label).toBe("Low");
  });
});

it("colours values by meaning", () => {
  expect(valueTone("Overdue")).toBe("bad");
  expect(valueTone("Partial")).toBe("warn");
  expect(valueTone("Paid")).toBe("good");
  expect(valueTone("General English")).toBe("");
});

it("shows which policy an answer came from", () => {
  const sources = [{ policy: "Fees, Payment Plans and Refunds Policy", section: "Payment plans" }];
  expect(toItems({ type: "answer", text: "Yes, up to 4 weeks.", sources })).toEqual([
    { kind: "text", text: "Yes, up to 4 weeks.", sources },
  ]);
  expect(toItems({ type: "answer", text: "Hi", sources: [] })).toEqual([{ kind: "text", text: "Hi" }]);
});

it("shows cooling leads as a table, or says there are none", () => {
  const leads = [{ name: "Ji-ho Park", status: "Offer sent", course: "Diploma of Business", days_quiet: 25,
                   reason: "No reply for 25 days after 2 follow-ups" }];
  expect(toItems({ type: "cooling_leads", text: "1 enquiry has gone quiet.", leads })).toEqual([
    { kind: "leads", text: "1 enquiry has gone quiet.", leads },
  ]);
  expect(toItems({ type: "cooling_leads", leads: [] })).toEqual([{ kind: "text", text: NO_LEADS }]);
});

