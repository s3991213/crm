import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Check, Copy } from "lucide-react";

function copyText(text) {
  if (navigator.clipboard && window.isSecureContext) {
    return navigator.clipboard.writeText(text);
  }
  // Fallback for plain-http office networks, where the clipboard API is blocked.
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

export default function EmailDraft() {
  const [to, setTo] = useState(props.to || "");
  const [subject, setSubject] = useState(props.subject || "");
  const [body, setBody] = useState(props.body || "");
  const [copied, setCopied] = useState(false);

  const onCopy = async () => {
    const text = subject ? `Subject: ${subject}\n\n${body}` : body;
    await copyText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="crm-card">
      <div className="crm-draft__label">Draft email · not sent</div>
      <label className="crm-field">
        <span>To</span>
        <input value={to} onChange={(e) => setTo(e.target.value)} />
      </label>
      <label className="crm-field">
        <span>Subject</span>
        <input value={subject} onChange={(e) => setSubject(e.target.value)} />
      </label>
      <label className="crm-field">
        <span>Message</span>
        <textarea rows={10} value={body} onChange={(e) => setBody(e.target.value)} />
      </label>
      <div className="crm-draft__actions">
        <Button onClick={onCopy} className="crm-btn">
          {copied ? <Check size={16} /> : <Copy size={16} />}
          {copied ? "Copied" : "Copy"}
        </Button>
        <span className="crm-footnote">Paste it into your email program to send.</span>
      </div>
    </div>
  );
}
