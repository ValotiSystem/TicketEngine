/**
 * summary:
 *   Dynamic form section that renders inputs for the tenant's active
 *   custom field definitions and bubbles values up via onChange.
 */
import type { CustomFieldDef } from "../../api/types";

interface Props {
  defs: CustomFieldDef[];
  values: Record<string, unknown>;
  onChange: (next: Record<string, unknown>) => void;
}

/**
 * summary:
 *   Render the controlled custom-field form section.
 * args:
 *   defs: active custom field definitions in display order.
 *   values: current values keyed by definition.key.
 *   onChange: callback invoked with the next values dict.
 * return:
 *   React element (or null if there are no fields).
 */
export function CustomFieldsForm({ defs, values, onChange }: Props) {
  if (!defs.length) return null;

  function set(key: string, v: unknown) {
    onChange({ ...values, [key]: v });
  }

  return (
    <div className="card" style={{ background: "#fafafa" }}>
      <h3 style={{ marginTop: 0, fontSize: 16 }}>Additional fields</h3>
      {defs.map((d) => (
        <div className="field" key={d.id}>
          <label>
            {d.label}
            {d.is_required && <span style={{ color: "#dc2626" }}> *</span>}
          </label>
          {renderInput(d, values[d.key], (v) => set(d.key, v))}
          {d.help_text && (
            <div style={{ fontSize: 12, color: "#6b7280", marginTop: 4 }}>{d.help_text}</div>
          )}
        </div>
      ))}
    </div>
  );
}

function renderInput(d: CustomFieldDef, value: unknown, onChange: (v: unknown) => void) {
  const cfg = d.config || {};
  switch (d.field_type) {
    case "text":
    case "url":
    case "email":
      return (
        <input
          className="input"
          type={d.field_type === "email" ? "email" : d.field_type === "url" ? "url" : "text"}
          value={(value as string) || ""}
          onChange={(e) => onChange(e.target.value)}
          required={d.is_required}
        />
      );
    case "longtext":
      return (
        <textarea
          className="textarea"
          value={(value as string) || ""}
          onChange={(e) => onChange(e.target.value)}
          required={d.is_required}
        />
      );
    case "number":
      return (
        <input
          className="input"
          type="number"
          value={value === undefined || value === null ? "" : String(value)}
          min={cfg.min as number | undefined}
          max={cfg.max as number | undefined}
          onChange={(e) => onChange(e.target.value === "" ? null : Number(e.target.value))}
          required={d.is_required}
        />
      );
    case "bool":
      return (
        <label>
          <input
            type="checkbox"
            checked={Boolean(value)}
            onChange={(e) => onChange(e.target.checked)}
          />{" "}
          {d.label}
        </label>
      );
    case "date":
      return (
        <input
          className="input"
          type="date"
          value={(value as string) || ""}
          onChange={(e) => onChange(e.target.value)}
          required={d.is_required}
        />
      );
    case "select": {
      const opts = (cfg.options as string[]) || [];
      return (
        <select
          className="select"
          value={(value as string) || ""}
          onChange={(e) => onChange(e.target.value || null)}
          required={d.is_required}
        >
          <option value="">—</option>
          {opts.map((o) => <option key={o} value={o}>{o}</option>)}
        </select>
      );
    }
    case "multiselect": {
      const opts = (cfg.options as string[]) || [];
      const arr = Array.isArray(value) ? (value as string[]) : [];
      return (
        <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
          {opts.map((o) => {
            const checked = arr.includes(o);
            return (
              <label key={o} style={{ display: "inline-flex", gap: 4 }}>
                <input
                  type="checkbox"
                  checked={checked}
                  onChange={(e) => {
                    onChange(
                      e.target.checked
                        ? [...arr, o]
                        : arr.filter((x) => x !== o)
                    );
                  }}
                />
                {o}
              </label>
            );
          })}
        </div>
      );
    }
    default:
      return <input className="input" disabled value={String(value ?? "")} />;
  }
}
