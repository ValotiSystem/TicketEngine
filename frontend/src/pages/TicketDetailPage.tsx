/**
 * summary:
 *   Ticket detail page: header, available state transitions, comments
 *   timeline and a composer that supports public and internal comments.
 */
import { useState } from "react";
import { useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ticketsApi } from "../api/tickets";
import { useAuthStore } from "../store/auth";
import { StatusBadge } from "../features/tickets/StatusBadge";
import { PriorityBadge } from "../features/tickets/PriorityBadge";
import { nextStatuses, reasonRequired } from "../features/tickets/workflow";
import type { TicketStatus } from "../api/types";
import { ApiException } from "../api/client";

export function TicketDetailPage() {
  const { id = "" } = useParams();
  const qc = useQueryClient();
  const hasPermission = useAuthStore((s) => s.hasPermission);

  const { data: ticket, error } = useQuery({
    queryKey: ["ticket", id],
    queryFn: () => ticketsApi.get(id),
  });

  const { data: comments = [] } = useQuery({
    queryKey: ["ticket", id, "comments"],
    queryFn: () => ticketsApi.comments(id),
    enabled: !!ticket,
  });

  const [body, setBody] = useState("");
  const [internal, setInternal] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  const addComment = useMutation({
    mutationFn: () => ticketsApi.addComment(id, body, internal),
    onSuccess: () => {
      setBody("");
      qc.invalidateQueries({ queryKey: ["ticket", id, "comments"] });
    },
    onError: (e) => setActionError(e instanceof ApiException ? e.payload.message : "Error"),
  });

  const transition = useMutation({
    mutationFn: (vars: { to: TicketStatus; reason?: string }) =>
      ticketsApi.transition(id, vars.to, vars.reason),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["ticket", id] }),
    onError: (e) => setActionError(e instanceof ApiException ? e.payload.message : "Error"),
  });

  if (error) return <div className="error">Error: {(error as Error).message}</div>;
  if (!ticket) return <div className="card">Loading...</div>;

  const transitions = nextStatuses(ticket.status);
  const canTransition = hasPermission("ticket.transition");
  const canCommentInternal = hasPermission("ticket.comment_internal");

  /**
   * summary:
   *   Trigger a status transition. When a reason is required by the
   *   state machine, prompt the user before submitting.
   * args:
   *   to: target status.
   * return:
   *   void.
   */
  function doTransition(to: TicketStatus) {
    let reason: string | undefined;
    if (reasonRequired(to)) {
      reason = window.prompt(`Reason for "${to}":`) || undefined;
      if (!reason) return;
    }
    setActionError(null);
    transition.mutate({ to, reason });
  }

  return (
    <div>
      <div className="card">
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <h2 style={{ margin: 0 }}>#{ticket.number} — {ticket.title}</h2>
          <StatusBadge status={ticket.status} />
          <PriorityBadge priority={ticket.priority} />
        </div>
        <p style={{ whiteSpace: "pre-wrap", marginTop: 16 }}>{ticket.description}</p>
        <div style={{ fontSize: 13, color: "#6b7280" }}>
          Created {new Date(ticket.created_at).toLocaleString()}
          {ticket.resolved_at && ` · Resolved ${new Date(ticket.resolved_at).toLocaleString()}`}
        </div>
      </div>

      {actionError && <div className="error">{actionError}</div>}

      {canTransition && transitions.length > 0 && (
        <div className="card">
          <strong>Change status:</strong>{" "}
          {transitions.map((t) => (
            <button
              key={t}
              className="btn"
              style={{ marginRight: 8 }}
              disabled={transition.isPending}
              onClick={() => doTransition(t)}
            >
              → {t}
            </button>
          ))}
        </div>
      )}

      <div className="card">
        <h3>Comments</h3>
        {comments.map((c) => (
          <div key={c.id} className={`comment${c.is_internal ? " internal" : ""}`}>
            <div className="meta">
              {new Date(c.created_at).toLocaleString()}
              {c.is_internal && <strong> · INTERNAL</strong>}
            </div>
            <div style={{ whiteSpace: "pre-wrap" }}>{c.body}</div>
          </div>
        ))}
        {!comments.length && <div style={{ color: "#6b7280" }}>No comments</div>}

        <div style={{ marginTop: 16 }}>
          <textarea
            className="textarea"
            placeholder="Write a comment..."
            value={body}
            onChange={(e) => setBody(e.target.value)}
          />
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: 8 }}>
            {canCommentInternal && (
              <label>
                <input type="checkbox" checked={internal} onChange={(e) => setInternal(e.target.checked)} /> Internal comment
              </label>
            )}
            <button
              className="btn"
              disabled={!body.trim() || addComment.isPending}
              onClick={() => addComment.mutate()}
            >
              {addComment.isPending ? "Sending..." : "Send"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
