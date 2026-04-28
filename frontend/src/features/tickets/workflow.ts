/**
 * summary:
 *   Mirror of the backend state machine.
 *
 *   CRITIQUE: deliberate redundancy - the frontend enables/disables
 *   buttons based on these rules. But the REAL enforcement is in the
 *   backend (`app/services/workflow.py`). If the two diverge, the
 *   backend wins and the frontend shows an error. Never put these rules
 *   ONLY here.
 */
import type { TicketStatus } from "../../api/types";

export const TRANSITIONS: Record<TicketStatus, TicketStatus[]> = {
  draft: ["open"],
  open: ["triage", "cancelled"],
  triage: ["in_progress", "waiting_on_requester", "resolved", "cancelled"],
  in_progress: ["waiting_on_requester", "waiting_on_third_party", "resolved"],
  waiting_on_requester: ["in_progress", "cancelled"],
  waiting_on_third_party: ["in_progress", "cancelled"],
  resolved: ["closed", "reopened"],
  closed: ["reopened"],
  reopened: ["in_progress", "triage"],
  cancelled: [],
};

export const REASON_REQUIRED: TicketStatus[] = ["resolved", "cancelled"];

/**
 * summary:
 *   Return the list of statuses reachable from the given status.
 * args:
 *   current: current ticket status.
 * return:
 *   Array of allowed next statuses.
 */
export function nextStatuses(current: TicketStatus): TicketStatus[] {
  return TRANSITIONS[current] || [];
}

/**
 * summary:
 *   Whether transitioning to the given status requires a reason.
 * args:
 *   target: target status.
 * return:
 *   True when a reason is mandatory.
 */
export function reasonRequired(target: TicketStatus): boolean {
  return REASON_REQUIRED.includes(target);
}
