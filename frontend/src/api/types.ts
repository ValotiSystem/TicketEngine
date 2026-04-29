/**
 * summary:
 *   Types shared with the backend.
 *
 *   CRITIQUE: in a serious team these types should be generated from the
 *   backend OpenAPI spec (e.g. openapi-typescript) to avoid drift. The
 *   scaffold writes them by hand.
 */

export type TicketStatus =
  | "draft" | "open" | "triage" | "in_progress"
  | "waiting_on_requester" | "waiting_on_third_party"
  | "resolved" | "closed" | "reopened" | "cancelled";

export type TicketPriority = "low" | "normal" | "high" | "urgent";

export type CustomFieldType =
  | "text" | "longtext" | "number" | "bool" | "date"
  | "select" | "multiselect" | "url" | "email";

export interface CustomFieldDef {
  id: string;
  key: string;
  label: string;
  field_type: CustomFieldType;
  is_required: boolean;
  is_active: boolean;
  display_order: number;
  config: Record<string, unknown>;
  help_text: string | null;
  created_at: string;
  updated_at: string;
}

export interface Ticket {
  id: string;
  number: number;
  title: string;
  description: string;
  status: TicketStatus;
  priority: TicketPriority;
  requester_id: string;
  assignee_id: string | null;
  queue_id: string | null;
  category_id: string | null;
  custom_fields: Record<string, unknown>;
  created_at: string;
  updated_at: string;
  resolved_at: string | null;
  closed_at: string | null;
  due_at: string | null;
  sla_breach_at: string | null;
}

export interface Comment {
  id: string;
  ticket_id: string;
  author_id: string;
  body: string;
  is_internal: boolean;
  created_at: string;
}

export interface Me {
  id: string;
  email: string;
  full_name: string;
  tenant_id: string;
  permissions: string[];
}

export interface Pagination {
  page: number;
  page_size: number;
  total: number;
  total_pages: number;
}

export interface Paginated<T> {
  data: T[];
  pagination: Pagination;
}

export interface ApiError {
  code: string;
  message: string;
  field?: string;
  request_id?: string;
}
