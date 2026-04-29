"""
summary:
    Business logic for custom field definitions and value validation.
"""
from __future__ import annotations

import re
from datetime import date, datetime
from typing import Any, Optional

from ..extensions import db
from ..models.custom_field import CustomFieldDefinition, ALLOWED_TYPES
from ..repositories import custom_field_repository as cfr
from ..common.errors import ValidationError
from . import audit_service


_KEY_RE = re.compile(r"^[a-z][a-z0-9_]{0,59}$")


def create(
    *,
    tenant_id: str,
    actor_id: str,
    key: str,
    label: str,
    field_type: str,
    is_required: bool = False,
    is_active: bool = True,
    display_order: int = 0,
    config: Optional[dict] = None,
    help_text: Optional[str] = None,
) -> CustomFieldDefinition:
    """
    summary:
        Create a new custom field definition for a tenant.
    args:
        tenant_id: tenant scope.
        actor_id: id of the admin performing the change.
        key: machine key (lowercase, [a-z0-9_], max 60 chars).
        label: human-readable label shown in the UI.
        field_type: one of ALLOWED_TYPES.
        is_required: whether the value is mandatory at ticket
            creation.
        is_active: whether the field is shown in forms.
        display_order: integer used to order fields in forms.
        config: type-specific config dict (see model docstring).
        help_text: optional help text shown next to the field.
    return:
        The persisted CustomFieldDefinition.
    """
    _validate_def(key=key, label=label, field_type=field_type, config=config or {})

    cf = CustomFieldDefinition(
        tenant_id=tenant_id,
        key=key,
        label=label.strip(),
        field_type=field_type,
        is_required=is_required,
        is_active=is_active,
        display_order=display_order,
        config=config or {},
        help_text=(help_text or None),
    )
    db.session.add(cf)
    db.session.flush()
    audit_service.record(
        tenant_id=tenant_id,
        actor_id=actor_id,
        event_type="admin.custom_field.created",
        payload={"id": cf.id, "key": cf.key, "type": cf.field_type},
    )
    db.session.commit()
    return cf


def update(
    *,
    tenant_id: str,
    actor_id: str,
    field_id: str,
    patch: dict[str, Any],
) -> CustomFieldDefinition:
    """
    summary:
        Patch an existing custom field definition. The `key` and
        `field_type` are immutable to keep stored values consistent.
    args:
        tenant_id: tenant scope.
        actor_id: id of the admin performing the change.
        field_id: id of the definition to update.
        patch: dict with editable fields (label, is_required, is_active,
            display_order, config, help_text).
    return:
        The updated CustomFieldDefinition.
    """
    cf = cfr.get(tenant_id, field_id)

    if "key" in patch and patch["key"] != cf.key:
        raise ValidationError("key is immutable", field="key")
    if "field_type" in patch and patch["field_type"] != cf.field_type:
        raise ValidationError("field_type is immutable", field="field_type")

    for attr in ("label", "is_required", "is_active", "display_order", "config", "help_text"):
        if attr in patch:
            setattr(cf, attr, patch[attr])

    _validate_def(key=cf.key, label=cf.label, field_type=cf.field_type, config=cf.config or {})

    audit_service.record(
        tenant_id=tenant_id,
        actor_id=actor_id,
        event_type="admin.custom_field.updated",
        payload={"id": cf.id, "patch_keys": sorted(patch.keys())},
    )
    db.session.commit()
    return cf


def deactivate(*, tenant_id: str, actor_id: str, field_id: str) -> CustomFieldDefinition:
    """
    summary:
        Soft-delete a custom field by setting is_active=False. We never
        physically delete: existing tickets keep their values and we
        keep the audit trail intact.
    args:
        tenant_id: tenant scope.
        actor_id: id of the admin performing the change.
        field_id: id of the definition to deactivate.
    return:
        The updated CustomFieldDefinition.
    """
    cf = cfr.get(tenant_id, field_id)
    cf.is_active = False
    audit_service.record(
        tenant_id=tenant_id,
        actor_id=actor_id,
        event_type="admin.custom_field.deactivated",
        payload={"id": cf.id, "key": cf.key},
    )
    db.session.commit()
    return cf


# ---- Validation helpers ---------------------------------------------------

def _validate_def(*, key: str, label: str, field_type: str, config: dict) -> None:
    """
    summary:
        Validate the static shape of a custom field definition.
    args:
        key: machine key.
        label: human label.
        field_type: type string.
        config: per-type config dict.
    return:
        None. Raises ValidationError on the first problem found.
    """
    if not _KEY_RE.match(key or ""):
        raise ValidationError("key must match ^[a-z][a-z0-9_]{0,59}$", field="key")
    if not (label and label.strip()):
        raise ValidationError("label is required", field="label")
    if field_type not in ALLOWED_TYPES:
        raise ValidationError(f"field_type must be one of {ALLOWED_TYPES}", field="field_type")
    if field_type in ("select", "multiselect"):
        opts = (config or {}).get("options")
        if not isinstance(opts, list) or not opts or not all(isinstance(o, str) and o for o in opts):
            raise ValidationError("config.options must be a non-empty list of strings", field="config")


def validate_values(definitions: list[CustomFieldDefinition], values: dict[str, Any]) -> dict[str, Any]:
    """
    summary:
        Validate ticket-side custom field values against the active
        definitions for a tenant. Unknown keys are dropped. Required
        fields without a value raise ValidationError.
    args:
        definitions: list of active CustomFieldDefinition for the tenant.
        values: dict provided by the client.
    return:
        Dict of cleaned values keyed by definition.key.
    """
    by_key = {d.key: d for d in definitions}
    cleaned: dict[str, Any] = {}

    for key, raw in (values or {}).items():
        if key not in by_key:
            # Silently drop unknown keys: tolerant on writes, strict on reads.
            continue
        cleaned[key] = _coerce(by_key[key], raw)

    for d in definitions:
        if d.is_required and (cleaned.get(d.key) in (None, "", [])):
            raise ValidationError(f"custom field '{d.key}' is required", field=f"custom_fields.{d.key}")

    return cleaned


def _coerce(d: CustomFieldDefinition, value: Any) -> Any:
    """
    summary:
        Coerce + validate a single custom field value against its
        definition.
    args:
        d: CustomFieldDefinition.
        value: raw value from the client.
    return:
        The normalized value to store.
    """
    if value is None:
        return None
    cfg = d.config or {}
    t = d.field_type

    if t in ("text", "longtext", "url", "email"):
        s = str(value).strip()
        max_len = int(cfg.get("max_length", 10000))
        if len(s) > max_len:
            raise ValidationError(f"{d.key}: max length {max_len}", field=f"custom_fields.{d.key}")
        if t == "email" and "@" not in s:
            raise ValidationError(f"{d.key}: invalid email", field=f"custom_fields.{d.key}")
        if t == "url" and not (s.startswith("http://") or s.startswith("https://")):
            raise ValidationError(f"{d.key}: must start with http(s)://", field=f"custom_fields.{d.key}")
        regex = cfg.get("regex")
        if regex and not re.match(regex, s):
            raise ValidationError(f"{d.key}: does not match pattern", field=f"custom_fields.{d.key}")
        return s

    if t == "number":
        try:
            n = float(value)
        except (TypeError, ValueError):
            raise ValidationError(f"{d.key}: not a number", field=f"custom_fields.{d.key}")
        if "min" in cfg and n < float(cfg["min"]):
            raise ValidationError(f"{d.key}: below min {cfg['min']}", field=f"custom_fields.{d.key}")
        if "max" in cfg and n > float(cfg["max"]):
            raise ValidationError(f"{d.key}: above max {cfg['max']}", field=f"custom_fields.{d.key}")
        return n

    if t == "bool":
        return bool(value) if not isinstance(value, str) else value.lower() in ("1", "true", "yes", "on")

    if t == "date":
        if isinstance(value, (date, datetime)):
            return value.isoformat()
        try:
            return date.fromisoformat(str(value)[:10]).isoformat()
        except ValueError:
            raise ValidationError(f"{d.key}: invalid ISO date", field=f"custom_fields.{d.key}")

    if t == "select":
        opts = cfg.get("options", [])
        if value not in opts:
            raise ValidationError(f"{d.key}: must be one of {opts}", field=f"custom_fields.{d.key}")
        return value

    if t == "multiselect":
        opts = set(cfg.get("options", []))
        if not isinstance(value, list) or not all(v in opts for v in value):
            raise ValidationError(f"{d.key}: invalid options", field=f"custom_fields.{d.key}")
        return value

    return value
