/**
 * summary:
 *   Badge component that renders a localized label for a ticket status.
 */
import type { TicketStatus } from "../../api/types";

const LABELS: Record<TicketStatus, string> = {
  draft: "Draft",
  open: "Open",
  triage: "Triage",
  in_progress: "In progress",
  waiting_on_requester: "Waiting on requester",
  waiting_on_third_party: "Waiting on third party",
  resolved: "Resolved",
  closed: "Closed",
  reopened: "Reopened",
  cancelled: "Cancelled",
};

export function StatusBadge({ status }: { status: TicketStatus }) {
  return <span className={`badge badge-status-${status}`}>{LABELS[status]}</span>;
}
