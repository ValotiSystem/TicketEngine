/**
 * summary:
 *   Tickets API client.
 */
import { api } from "./client";
import type { Ticket, Comment, Paginated, TicketStatus, TicketPriority } from "./types";

export interface TicketListFilters {
  page?: number;
  page_size?: number;
  status?: TicketStatus;
  assignee_id?: string;
  queue_id?: string;
  q?: string;
  sort?: string;
}

export const ticketsApi = {
  /**
   * summary:
   *   List tickets returning only the data array (pagination meta is
   *   discarded by the generic api() unwrapper). Use listFull when the
   *   pagination block is required.
   * args:
   *   f: optional filter object.
   * return:
   *   Promise resolving to an array of Ticket items.
   */
  list: (f: TicketListFilters = {}) =>
    api<Paginated<Ticket>["data"]>("/tickets", { query: f as Record<string, string | number | undefined> }),

  /**
   * summary:
   *   List tickets and preserve the pagination metadata. Performs a raw
   *   fetch because the generic client unwraps the `data` field.
   * args:
   *   f: optional filter object.
   * return:
   *   Promise resolving to a Paginated<Ticket> response.
   */
  listFull: async (f: TicketListFilters = {}): Promise<Paginated<Ticket>> => {
    const url = new URL("/api/v1/tickets", window.location.origin);
    for (const [k, v] of Object.entries(f)) {
      if (v !== undefined && v !== null && v !== "") url.searchParams.set(k, String(v));
    }
    const { useAuthStore } = await import("../store/auth");
    const token = useAuthStore.getState().accessToken;
    const resp = await fetch(url.toString(), {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    });
    if (!resp.ok) throw new Error("Failed to load tickets");
    const data = await resp.json();
    return { data: data.data, pagination: data.pagination };
  },

  /**
   * summary:
   *   Fetch a single ticket by id.
   * args:
   *   id: ticket id.
   * return:
   *   Promise resolving to a Ticket.
   */
  get: (id: string) => api<Ticket>(`/tickets/${id}`),

  /**
   * summary:
   *   Create a new ticket.
   * args:
   *   payload: title, description, optional priority.
   * return:
   *   Promise resolving to the created Ticket.
   */
  create: (payload: { title: string; description: string; priority?: TicketPriority }) =>
    api<Ticket>("/tickets", { method: "POST", body: payload }),

  /**
   * summary:
   *   Apply a partial update to a ticket.
   * args:
   *   id: ticket id.
   *   payload: subset of editable Ticket fields.
   * return:
   *   Promise resolving to the updated Ticket.
   */
  update: (id: string, payload: Partial<Ticket>) =>
    api<Ticket>(`/tickets/${id}`, { method: "PATCH", body: payload }),

  /**
   * summary:
   *   List comments visible to the current user on a ticket.
   * args:
   *   id: ticket id.
   * return:
   *   Promise resolving to a list of Comment items.
   */
  comments: (id: string) => api<Comment[]>(`/tickets/${id}/comments`),

  /**
   * summary:
   *   Append a comment to a ticket.
   * args:
   *   id: ticket id.
   *   body: comment text.
   *   is_internal: when true, only visible to users with the
   *     ticket.comment_internal permission.
   * return:
   *   Promise resolving to the created Comment.
   */
  addComment: (id: string, body: string, is_internal = false) =>
    api<Comment>(`/tickets/${id}/comments`, { method: "POST", body: { body, is_internal } }),

  /**
   * summary:
   *   Set or clear the assignee of a ticket.
   * args:
   *   id: ticket id.
   *   assignee_id: new assignee id, or null to unassign.
   * return:
   *   Promise resolving to the updated Ticket.
   */
  assign: (id: string, assignee_id: string | null) =>
    api<Ticket>(`/tickets/${id}/assign`, { method: "POST", body: { assignee_id } }),

  /**
   * summary:
   *   Move a ticket to a new status.
   * args:
   *   id: ticket id.
   *   to_status: target status.
   *   reason: optional reason text. Required for resolved/cancelled.
   * return:
   *   Promise resolving to the updated Ticket.
   */
  transition: (id: string, to_status: TicketStatus, reason?: string) =>
    api<Ticket>(`/tickets/${id}/transition`, { method: "POST", body: { to_status, reason } }),
};
