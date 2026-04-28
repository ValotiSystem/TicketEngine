/**
 * summary:
 *   New ticket form page. On success redirects to the ticket detail
 *   view.
 */
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { ticketsApi } from "../api/tickets";
import type { TicketPriority } from "../api/types";
import { ApiException } from "../api/client";

export function NewTicketPage() {
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [priority, setPriority] = useState<TicketPriority>("normal");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const nav = useNavigate();

  /**
   * summary:
   *   Handle form submission to create a new ticket.
   * args:
   *   e: form submit event.
   * return:
   *   Promise that resolves once the request has finished.
   */
  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const t = await ticketsApi.create({ title, description, priority });
      nav(`/tickets/${t.id}`);
    } catch (e) {
      setError(e instanceof ApiException ? e.payload.message : "Error");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="card" style={{ maxWidth: 720 }}>
      <h2 style={{ marginTop: 0 }}>New ticket</h2>
      <form onSubmit={submit}>
        {error && <div className="error">{error}</div>}
        <div className="field">
          <label>Title</label>
          <input className="input" value={title} onChange={(e) => setTitle(e.target.value)} required />
        </div>
        <div className="field">
          <label>Description</label>
          <textarea className="textarea" value={description} onChange={(e) => setDescription(e.target.value)} required />
        </div>
        <div className="field" style={{ maxWidth: 200 }}>
          <label>Priority</label>
          <select className="select" value={priority} onChange={(e) => setPriority(e.target.value as TicketPriority)}>
            <option value="low">Low</option>
            <option value="normal">Normal</option>
            <option value="high">High</option>
            <option value="urgent">Urgent</option>
          </select>
        </div>
        <button className="btn" disabled={loading} type="submit">
          {loading ? "Creating..." : "Create ticket"}
        </button>
      </form>
    </div>
  );
}
