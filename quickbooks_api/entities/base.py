"""Base service class for QBO entity operations."""

from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from quickbooks_api.client import QuickBooksClient


class BaseService:
    """Base class providing CRUD + query operations for a QBO entity."""

    entity_name: str = ""  # Override in subclasses, e.g. "Customer"
    entity_url: str = ""   # Override in subclasses, e.g. "/customer"

    def __init__(self, client: QuickBooksClient):
        self.client = client

    def get(self, entity_id: str | int) -> dict:
        """Read a single entity by ID."""
        resp = self.client.get(f"{self.entity_url}/{entity_id}")
        return resp.get(self.entity_name, resp)

    def create(self, data: dict) -> dict:
        """Create a new entity."""
        resp = self.client.post(self.entity_url, json_data=data)
        return resp.get(self.entity_name, resp)

    def update(self, data: dict) -> dict:
        """Update an existing entity. Must include Id and SyncToken."""
        resp = self.client.post(self.entity_url, json_data=data)
        return resp.get(self.entity_name, resp)

    def delete(self, entity_id: str | int, sync_token: str) -> dict:
        """Delete an entity by ID (for entities that support delete)."""
        data = {"Id": str(entity_id), "SyncToken": sync_token}
        return self.client.delete(self.entity_url, json_data=data)

    def query(
        self,
        where: str = "",
        order_by: str = "",
        start_position: int = 1,
        max_results: int = 100,
        columns: str = "*",
    ) -> list[dict]:
        """Query entities with optional WHERE, ORDER BY, and pagination."""
        q = f"SELECT {columns} FROM {self.entity_name}"
        if where:
            q += f" WHERE {where}"
        if order_by:
            q += f" ORDERBY {order_by}"
        q += f" STARTPOSITION {start_position} MAXRESULTS {max_results}"
        return self.client.query(q)

    def count(self, where: str = "") -> int:
        """Count entities matching an optional WHERE clause."""
        return self.client.query_count(self.entity_name, where)

    def get_all(self, where: str = "", batch_size: int = 100) -> list[dict]:
        """Fetch all entities with automatic pagination."""
        results = []
        start = 1
        while True:
            batch = self.query(where=where, start_position=start, max_results=batch_size)
            if not batch:
                break
            results.extend(batch)
            if len(batch) < batch_size:
                break
            start += batch_size
        return results
