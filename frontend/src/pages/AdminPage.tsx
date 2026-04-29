/**
 * summary:
 *   Admin page for tenant configuration. Currently exposes the custom
 *   field definitions list with create / edit / deactivate operations.
 */
import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { adminApi, type CustomFieldCreate } from "../api/admin";
import type { CustomFieldDef, CustomFieldType } from "../api/types";
import { ApiException } from "../api/client";

const TYPES: CustomFieldType[] = [
  "text", "longtext", "number", "bool", "date", "select", "multiselect", "url", "email",
];

export function AdminPage() {
  const qc = useQueryClient();
  const { data: defs = [], isLoading } = useQuery({
    queryKey: ["admin", "custom-fields"],
    queryFn: adminApi.listCustomFields,
  });

  const [editing, setEditing] = useState<CustomFieldDef | null>(null);
  const [creating, setCreating] = useState(false);

  function refresh() {
    qc.invalidateQueries({ queryKey: ["admin", "custom-fields"] });
  }

  return (
    <div>
      <div className="card" style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div>
          <h2 style={{ margin: 0 }}>Administration</h2>
          <div style={{ color: "#6b7280", fontSize: 14 }}>Customize the ticket structure for your tenant.</div>
        </div>
        <button className="btn" onClick={() => { setCreating(true); setEditing(null); }}>+ New custom field</button>
      </div>

      {isLoading && <div className="card">Loading...</div>}

      {creating && (
        <CustomFieldEditor
          onClose={() => setCreating(false)}
          onSaved={() => { setCreating(false); refresh(); }}
        />
      )}

      {editing && (
        <CustomFieldEditor
          existing={editing}
          onClose={() => setEditing(null)}
          onSaved={() => { setEditing(null); refresh(); }}
        />
      )}

      <div className="card" style={{ padding: 0 }}>
        <table>
          <thead>
            <tr>
              <th>Order</th>
              <th>Key</th>
              <th>Label</th>
              <th>Type</th>
              <th>Required</th>
              <th>Active</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {defs.map((d) => (
              <tr key={d.id}>
                <td>{d.display_order}</td>
                <td><code>{d.key}</code></td>
                <td>{d.label}</td>
                <td>{d.field_type}</td>
                <td>{d.is_required ? "yes" : "—"}</td>
                <td>{d.is_active ? "yes" : "no"}</td>
                <td>
                  <button className="btn btn-secondary" style={{ marginRight: 8 }} onClick={() => { setEditing(d); setCreating(false); }}>Edit</button>
                  {d.is_active && (
                    <DeactivateButton id={d.id} onDone={refresh} />
                  )}
                </td>
              </tr>
            ))}
            {!defs.length && !isLoading && (
              <tr><td colSpan={7} style={{ textAlign: "center", padding: 20 }}>No custom fields defined yet.</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function DeactivateButton({ id, onDone }: { id: string; onDone: () => void }) {
  const m = useMutation({
    mutationFn: () => adminApi.deactivateCustomField(id),
    onSuccess: onDone,
  });
  return (
    <button
      className="btn btn-danger"
      disabled={m.isPending}
      onClick={() => { if (confirm("Deactivate this field? Existing ticket values are preserved.")) m.mutate(); }}
    >
      {m.isPending ? "..." : "Deactivate"}
    </button>
  );
}

interface EditorProps {
  existing?: CustomFieldDef;
  onClose: () => void;
  onSaved: () => void;
}

function CustomFieldEditor({ existing, onClose, onSaved }: EditorProps) {
  const [key, setKey] = useState(existing?.key || "");
  const [label, setLabel] = useState(existing?.label || "");
  const [fieldType, setFieldType] = useState<CustomFieldType>(existing?.field_type || "text");
  const [isRequired, setIsRequired] = useState(existing?.is_required || false);
  const [isActive, setIsActive] = useState(existing?.is_active ?? true);
  const [displayOrder, setDisplayOrder] = useState(existing?.display_order || 0);
  const [optionsRaw, setOptionsRaw] = useState(
    Array.isArray((existing?.config as { options?: string[] })?.options)
      ? ((existing!.config as { options: string[] }).options).join(", ")
      : ""
  );
  const [helpText, setHelpText] = useState(existing?.help_text || "");
  const [error, setError] = useState<string | null>(null);

  const needsOptions = useMemo(() => fieldType === "select" || fieldType === "multiselect", [fieldType]);

  const create = useMutation({
    mutationFn: (payload: CustomFieldCreate) => adminApi.createCustomField(payload),
    onSuccess: onSaved,
    onError: (e) => setError(e instanceof ApiException ? e.payload.message : "Error"),
  });
  const update = useMutation({
    mutationFn: (patch: Partial<CustomFieldCreate>) => adminApi.updateCustomField(existing!.id, patch),
    onSuccess: onSaved,
    onError: (e) => setError(e instanceof ApiException ? e.payload.message : "Error"),
  });

  function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    const config: Record<string, unknown> = {};
    if (needsOptions) {
      config.options = optionsRaw.split(",").map((s) => s.trim()).filter(Boolean);
    }
    if (existing) {
      update.mutate({
        label, is_required: isRequired, is_active: isActive,
        display_order: displayOrder, config, help_text: helpText || null,
      });
    } else {
      create.mutate({
        key, label, field_type: fieldType, is_required: isRequired, is_active: isActive,
        display_order: displayOrder, config, help_text: helpText || null,
      });
    }
  }

  const busy = create.isPending || update.isPending;

  return (
    <div className="card">
      <h3 style={{ marginTop: 0 }}>{existing ? `Edit: ${existing.key}` : "New custom field"}</h3>
      <form onSubmit={submit}>
        {error && <div className="error">{error}</div>}
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
          <div className="field">
            <label>Key (immutable)</label>
            <input
              className="input"
              value={key}
              onChange={(e) => setKey(e.target.value)}
              disabled={!!existing}
              placeholder="e.g. severity_level"
              required
            />
          </div>
          <div className="field">
            <label>Type (immutable)</label>
            <select
              className="select"
              value={fieldType}
              onChange={(e) => setFieldType(e.target.value as CustomFieldType)}
              disabled={!!existing}
            >
              {TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
            </select>
          </div>
        </div>
        <div className="field">
          <label>Label</label>
          <input className="input" value={label} onChange={(e) => setLabel(e.target.value)} required />
        </div>
        {needsOptions && (
          <div className="field">
            <label>Options (comma-separated)</label>
            <input className="input" value={optionsRaw} onChange={(e) => setOptionsRaw(e.target.value)} placeholder="low, medium, high" />
          </div>
        )}
        <div className="field">
          <label>Help text</label>
          <input className="input" value={helpText} onChange={(e) => setHelpText(e.target.value)} />
        </div>
        <div style={{ display: "flex", gap: 16, alignItems: "center" }}>
          <label><input type="checkbox" checked={isRequired} onChange={(e) => setIsRequired(e.target.checked)} /> Required</label>
          <label><input type="checkbox" checked={isActive} onChange={(e) => setIsActive(e.target.checked)} /> Active</label>
          <div className="field" style={{ marginBottom: 0, width: 120 }}>
            <label>Order</label>
            <input className="input" type="number" value={displayOrder} onChange={(e) => setDisplayOrder(Number(e.target.value))} />
          </div>
          <div style={{ marginLeft: "auto", display: "flex", gap: 8 }}>
            <button type="button" className="btn btn-secondary" onClick={onClose}>Cancel</button>
            <button type="submit" className="btn" disabled={busy}>{busy ? "Saving..." : "Save"}</button>
          </div>
        </div>
      </form>
    </div>
  );
}
