"""
summary:
    Standard response helpers and pagination envelope.
"""
from __future__ import annotations

from flask import jsonify, request


def paginated(items, total: int, schema):
    """
    summary:
        Build a paginated response payload from a list of records.
    args:
        items: collection of model instances for the current page.
        total: total number of records across all pages.
        schema: Marshmallow schema used to serialize each item.
    return:
        Flask JSON response with `data` and `pagination` keys.
    """
    page = int(request.args.get("page", 1))
    page_size = min(int(request.args.get("page_size", 25)), 100)
    return jsonify({
        "data": schema.dump(items, many=True),
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total": total,
            "total_pages": (total + page_size - 1) // page_size if page_size else 1,
        },
    })


def ok(payload):
    """
    summary:
        Wrap an arbitrary payload in the standard `data` envelope.
    args:
        payload: serializable response body.
    return:
        Flask JSON response.
    """
    return jsonify({"data": payload})
