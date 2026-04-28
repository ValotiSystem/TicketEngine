/**
 * summary:
 *   Badge component that renders a label for a ticket priority.
 */
import type { TicketPriority } from "../../api/types";

const LABELS: Record<TicketPriority, string> = {
  low: "Low",
  normal: "Normal",
  high: "High",
  urgent: "Urgent",
};

export function PriorityBadge({ priority }: { priority: TicketPriority }) {
  return <span className={`badge badge-priority-${priority}`}>{LABELS[priority]}</span>;
}
