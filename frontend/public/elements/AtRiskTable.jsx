function percent(score) {
  const n = Number(score) || 0;
  return Math.round(n <= 1 ? n * 100 : n);
}

function level(p) {
  if (p >= 70) return { label: "High", cls: "crm-pill crm-pill--bad" };
  if (p >= 40) return { label: "Medium", cls: "crm-pill crm-pill--warn" };
  return { label: "Low", cls: "crm-pill" };
}

export default function AtRiskTable() {
  const students = props.students || [];
  return (
    <div className="crm-card crm-card--flush">
      <table className="crm-table">
        <thead>
          <tr>
            <th>Student</th>
            <th>Risk</th>
            <th>Main reasons</th>
          </tr>
        </thead>
        <tbody>
          {students.map((s, i) => {
            const p = percent(s.risk_score);
            const lv = level(p);
            return (
              <tr key={i}>
                <td data-label="Student">
                  <button
                    type="button"
                    className="crm-link"
                    title={`Summarise ${s.name}'s history`}
                    onClick={() => sendUserMessage(`Summarise ${s.name}'s history`)}
                  >
                    {s.name}
                  </button>
                </td>
                <td data-label="Risk">
                  <div className="crm-risk">
                    <span className={lv.cls}>{lv.label}</span>
                    <span className="crm-risk__num">{p}%</span>
                  </div>
                </td>
                <td data-label="Main reasons">
                  <ul className="crm-reasons">
                    {(s.reasons || []).map((r, j) => (
                      <li key={j}>{r}</li>
                    ))}
                  </ul>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
      <p className="crm-footnote">Tap a name to see a summary of that student.</p>
    </div>
  );
}
