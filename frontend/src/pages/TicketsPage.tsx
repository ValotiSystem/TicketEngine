/**
 * summary:
 *   Tickets listing page with text search, status filter and pagination.
 */
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { ticketsApi } from "../api/tickets";
import { StatusBadge } from "../features/tickets/StatusBadge";
import { PriorityBadge } from "../features/tickets/PriorityBadge";
import type { TicketStatus } from "../api/types";

export function TicketsPage() {
  const [q, setQ] = useState("");
  const [status, setStatus] = useState<TicketStatus | "">("");
  const [page, setPage] = useState(1);

  const { data, isLoading, error } = useQuery({
    queryKey: ["tickets", { q, status, page }],
    queryFn: () => ticketsApi.listFull({ q, status: (status || undefined) as TicketStatus | undefined, page, page_size: 25 }),
  });

  return (
    <div>
      <div className="card" style={{ display: "flex", gap: 12, alignItems: "end" }}>
        <div className="field" style={{ flex: 1, marginBottom: 0 }}>
          <label>Search</label>
          <input className="input" value={q} onChange={(e) => { setQ(e.target.value); setPage(1); }} placeholder="Title or description" />
        </div>
        <div className="field" style={{ width: 220, marginBottom: 0 }}>
          <label>Status</label>
          <select className="select" value={status} onChange={(e) => { setStatus(e.target.value as TicketStatus | ""); setPage(1); }}>
            <option value="">All</option>
            <option value="open">Open</option>
            <option value="triage">Triage</option>
            <option value="in_progress">In progress</option>
            <option value="waiting_on_requester">Waiting on requester</option>
            <option value="waiting_on_third_party">Waiting on third party</option>
            <option value="resolved">Resolved</option>
            <option value="closed">Closed</option>
          </select>
        </div>
        <Link to="/tickets/new" className="btn">+ New</Link>
      </div>

      {isLoading && <div className="card">Loading...</div>}
      {error && <div className="error">Failed to load tickets</div>}

      {data && (
        <div className="card" style={{ padding: 0 }}>
          <table>
            <thead>
              <tr>
                <th>#</th>
                <th>Title</th>
                <th>Status</th>
                <th>Priority</th>
                <th>Created</th>
              </tr>
            </thead>
            <tbody>
              {data.data.map((t) => (
                <tr key={t.id}>
                  <td>{t.number}</td>
                  <td><Link to={`/tickets/${t.id}`}>{t.title}</Link></td>
                  <td><StatusBadge status={t.status} /></td>
                  <td><PriorityBadge priority={t.priority} /></td>
                  <td>{new Date(t.created_at).toLocaleString()}</td>
                </tr>
              ))}
              {!data.data.length && (
                <tr><td colSpan={5} style={{ textAlign: "center", padding: 20 }}>No tickets</td></tr>
              )}
            </tbody>
          </table>
          <div style={{ padding: 12, display: "flex", justifyContent: "space-between" }}>
            <span>{data.pagination.total} total — page {data.pagination.page}/{data.pagination.total_pages}</span>
            <div style={{ display: "flex", gap: 8 }}>
              <button className="btn btn-secondary" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>‹</button>
              <button className="btn btn-secondary" disabled={page >= data.pagination.total_pages} onClick={() => setPage((p) => p + 1)}>›</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
