import { useEffect, useRef, useState, type FormEvent, type KeyboardEvent } from "react";
import Markdown from "react-markdown";
import { AlertTriangle, ArrowUp, History, LogOut, Mail, Search, SquarePen } from "lucide-react";
import { api, ApiError, newId, type Me } from "./api";
import { AtRiskTable, ChangePassword, ConfirmCard, EmailDraft, StudentCard } from "./cards";
import { atRiskItem, toItems, type ChangeStatus, type Item } from "./reply";
import logo from "./logo.svg";

const AT_RISK_PROMPT = "Show at-risk students";
const STARTERS = [
  { label: "Find a student", icon: Search, prefill: "Find " },
  { label: "Summarise a student's history", icon: History, prefill: "Summarise the history of " },
  { label: AT_RISK_PROMPT, icon: AlertTriangle, send: AT_RISK_PROMPT },
  { label: "Draft a follow-up email", icon: Mail, prefill: "Draft a follow-up email to " },
];

type Entry = Item & { id: string };
const withIds = (items: Item[]): Entry[] => items.map((item) => ({ ...item, id: newId() }));

export default function App() {
  const [me, setMe] = useState<Me | null>(null);
  const [checking, setChecking] = useState(true);
  const [signedOutNote, setSignedOutNote] = useState("");

  useEffect(() => {
    api.me().then(setMe, () => undefined).finally(() => setChecking(false));
  }, []);

  if (checking) return null;
  if (!me) return <Login note={signedOutNote} onSignedIn={(m) => { setSignedOutNote(""); setMe(m); }} />;
  return (
    <Chat
      me={me}
      onPasswordChanged={() => setMe({ ...me, must_change: false })}
      onSignedOut={(note) => { setSignedOutNote(note); setMe(null); }}
    />
  );
}

function Login({ note, onSignedIn }: { note: string; onSignedIn: (me: Me) => void }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      onSignedIn(await api.login(username, password));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong. Please try again.");
      setBusy(false);
    }
  };

  return (
    <main className="login">
      <form className="card login__card" onSubmit={onSubmit}>
        <img src={logo} alt="" className="login__logo" />
        <h1>CRM Assistant</h1>
        <p className="footnote">Sign in with the username your manager gave you.</p>
        {note && <div className="status status--bad">{note}</div>}
        <label className="field">
          <span>Username</span>
          <input id="username" autoComplete="username" autoCapitalize="none" value={username}
                 onChange={(e) => setUsername(e.target.value)} required autoFocus />
        </label>
        <label className="field">
          <span>Password</span>
          <input id="password" type="password" autoComplete="current-password" value={password}
                 onChange={(e) => setPassword(e.target.value)} required />
        </label>
        {error && <div className="status status--bad login__error">{error}</div>}
        <button type="submit" className="btn btn--primary btn--wide" disabled={busy}>{busy ? "Signing in…" : "Sign in"}</button>
      </form>
    </main>
  );
}

function welcome(me: Me): Entry[] {
  if (!me.must_change) return [];
  return withIds([
    { kind: "text", text: `Welcome, ${me.name}! Before you start, please choose your own password. You'll use it from now on instead of the temporary one.` },
    { kind: "password", forced: true },
  ]);
}

function Chat({ me, onPasswordChanged, onSignedOut }:
  { me: Me; onPasswordChanged: () => void; onSignedOut: (note: string) => void }) {
  const [entries, setEntries] = useState<Entry[]>(() => welcome(me));
  const [conversation, setConversation] = useState(newId);
  const [draft, setDraft] = useState("");
  const [busy, setBusy] = useState(false);
  const input = useRef<HTMLTextAreaElement>(null);
  const bottom = useRef<HTMLDivElement>(null);
  const locked = me.must_change;

  useEffect(() => { bottom.current?.scrollIntoView({ behavior: "smooth", block: "end" }); }, [entries, busy]);

  const add = (items: Item[]) => setEntries((prev) => [...prev, ...withIds(items)]);
  const setStatus = (id: string, status: ChangeStatus) =>
    setEntries((prev) => prev.map((e) => (e.id === id && e.kind === "change" ? { ...e, status } : e)));

  const failed = (err: unknown) => {
    if (err instanceof ApiError && err.status === 401) return onSignedOut(err.message);
    add([{ kind: "text", tone: "bad", text: err instanceof Error ? err.message : "Something went wrong. Please try again." }]);
  };

  const send = async (text: string) => {
    text = text.trim();
    if (!text || busy || locked) return;
    setDraft("");
    add([{ kind: "staff", text }]);
    setBusy(true);
    try {
      if (text.toLowerCase() === AT_RISK_PROMPT.toLowerCase()) add([atRiskItem(await api.atRisk())]);
      else add(toItems(await api.chat(text, conversation)));
    } catch (err) {
      failed(err);
    } finally {
      setBusy(false);
      input.current?.focus();
    }
  };

  const resolve = async (id: string, updateId: string, confirmed: boolean) => {
    setStatus(id, "busy"); // the buttons go first, so a second click can't save twice
    try {
      const result = await api.resolve(updateId, confirmed);
      setStatus(id, confirmed ? "saved" : "cancelled");
      add([{ kind: "text", text: result.text }]);
    } catch (err) {
      setStatus(id, "failed");
      failed(err);
    }
  };

  const signOut = async () => {
    await api.logout().catch(() => undefined);
    onSignedOut("");
  };

  const newChat = () => {
    setEntries(welcome(me));
    setConversation(newId());
    setDraft("");
    input.current?.focus();
  };

  const onKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) {
      e.preventDefault();
      send(draft);
    }
  };

  const render = (e: Entry) => {
    switch (e.kind) {
      case "staff":
        return <div className="bubble">{e.text}</div>;
      case "text":
        return <div className={`reply${e.tone ? ` reply--${e.tone}` : ""}`}><Markdown>{e.text}</Markdown></div>;
      case "student":
        return <StudentCard student={e.student} />;
      case "change":
        return (
          <>
            <div className="reply"><Markdown>{e.text}</Markdown></div>
            <ConfirmCard update={e.update} status={e.status} onResolve={(ok) => resolve(e.id, e.update.update_id, ok)} />
          </>
        );
      case "atRisk":
        return (
          <>
            <div className="reply"><Markdown>{e.text}</Markdown></div>
            <AtRiskTable students={e.students} onPick={send} disabled={busy} />
          </>
        );
      case "draft":
        return (
          <>
            <div className="reply"><Markdown>{e.text}</Markdown><p><em>Nothing has been sent.</em></p></div>
            <EmailDraft draft={e.draft} />
          </>
        );
      case "password":
        return (
          <ChangePassword forced={e.forced} onDone={() => {
            if (e.forced) {
              onPasswordChanged();
              add([{ kind: "text", text: 'All set. How can I help? Try something like *"Find Liam Nguyen"* or *"Show at-risk students"*.' }]);
            }
          }} />
        );
    }
  };

  return (
    <div className="app">
      <header className="top">
        <button type="button" className="icon-btn" onClick={newChat} title="New chat" aria-label="New chat"><SquarePen size={20} /></button>
        <div className="top__brand"><img src={logo} alt="" /> CRM Assistant</div>
        <div className="top__user">
          <span className="top__name">{me.name}</span>
          <button type="button" className="icon-btn" onClick={signOut} title="Sign out" aria-label="Sign out"><LogOut size={18} /></button>
        </div>
      </header>

      <main className="thread" aria-live="polite">
        {entries.length === 0 && (
          <div className="empty">
            <img src={logo} alt="" className="empty__logo" />
            <h1>Hi {me.name.split(" ")[0]}, what do you need?</h1>
            <div className="starters">
              {STARTERS.map((s) => (
                <button key={s.label} type="button" className="starter" onClick={() => {
                  if (s.send) send(s.send);
                  else { setDraft(s.prefill ?? ""); input.current?.focus(); }
                }}>
                  <s.icon size={18} /> {s.label}
                </button>
              ))}
            </div>
          </div>
        )}
        {entries.map((e) => (
          <div key={e.id} className={e.kind === "staff" ? "row row--staff" : "row"}>{render(e)}</div>
        ))}
        {busy && <div className="row"><div className="reply reply--working">Working on it…</div></div>}
        <div ref={bottom} />
      </main>

      <form className="composer" onSubmit={(e) => { e.preventDefault(); send(draft); }}>
        <textarea
          id="chat-input" ref={input} rows={2} value={draft} disabled={locked}
          placeholder={locked ? "Choose your password above first" : "Type your message here…"}
          onChange={(e) => setDraft(e.target.value)} onKeyDown={onKeyDown}
        />
        <button type="submit" className="send" disabled={busy || locked || !draft.trim()} aria-label="Send"><ArrowUp size={18} /></button>
      </form>
    </div>
  );
}
