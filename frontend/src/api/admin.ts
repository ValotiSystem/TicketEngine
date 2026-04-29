/**
 * summary:
 *   Admin API client for tenant configuration.
 */
import { api } from "./client";
import type { CustomFieldDef, CustomFieldType } from "./types";

export interface CustomFieldCreate {
  key: string;
  label: string;
  field_type: CustomFieldType;
  is_required?: boolean;
  is_active?: boolean;
  display_order?: number;
  config?: Record<string, unknown>;
  help_text?: string | null;
}

export const adminApi = {
  /**
   * summary:
   *   List every custom field definition for the current tenant.
   * args:
   *   none.
   * return:
   *   Promise resolving to an array of CustomFieldDef items.
   */
  listCustomFields: () => api<CustomFieldDef[]>("/admin/custom-fields"),

  /**
   * summary:
   *   Create a new custom field definition.
   * args:
   *   payload: definition payload.
   * return:
   *   Promise resolving to the created CustomFieldDef.
   */
  createCustomField: (payload: CustomFieldCreate) =>
    api<CustomFieldDef>("/admin/custom-fields", { method: "POST", body: payload }),

  /**
   * summary:
   *   Patch an existing custom field definition.
   * args:
   *   id: definition id.
   *   patch: partial fields to update.
   * return:
   *   Promise resolving to the updated CustomFieldDef.
   */
  updateCustomField: (id: string, patch: Partial<CustomFieldCreate>) =>
    api<CustomFieldDef>(`/admin/custom-fields/${id}`, { method: "PATCH", body: patch }),

  /**
   * summary:
   *   Soft-delete (deactivate) a custom field definition.
   * args:
   *   id: definition id.
   * return:
   *   Promise resolving to the updated CustomFieldDef.
   */
  deactivateCustomField: (id: string) =>
    api<CustomFieldDef>(`/admin/custom-fields/${id}`, { method: "DELETE" }),
};

/**
 * summary:
 *   Fetch active custom fields for the ticket form (read scope, not admin).
 * args:
 *   none.
 * return:
 *   Promise resolving to an array of CustomFieldDef items.
 */
export const ticketCustomFields = () => api<CustomFieldDef[]>("/tickets/custom-fields");
