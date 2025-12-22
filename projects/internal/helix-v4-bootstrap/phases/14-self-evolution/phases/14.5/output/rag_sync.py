"""
RAG Sync module for HELIX v4 Self-Evolution System.

This module handles synchronization of RAG (Retrieval-Augmented Generation) data
between the production Qdrant instance and the test Qdrant instance.

The sync workflow:
1. Connect to both production and test Qdrant instances
2. List all collections in production
3. For each collection, copy the vectors and metadata to test
4. Verify the sync was successful

This ensures the test system has realistic embeddings for proper testing
of any RAG-related functionality.
"""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

import httpx


class SyncStatus(str, Enum):
    """Status of a sync operation."""

    PENDING = "pending"
    CONNECTING = "connecting"
    SYNCING = "syncing"
    VERIFYING = "verifying"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class CollectionSyncResult:
    """Result of syncing a single collection."""

    collection_name: str
    success: bool
    points_synced: int = 0
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "collection_name": self.collection_name,
            "success": self.success,
            "points_synced": self.points_synced,
            "error": self.error,
        }


@dataclass
class SyncResult:
    """Result of a complete RAG sync operation."""

    success: bool
    status: SyncStatus
    message: str
    collections_synced: list[CollectionSyncResult] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    started_at: datetime = field(default_factory=datetime.now)
    completed_at: datetime | None = None

    @property
    def total_points_synced(self) -> int:
        """Total number of points synced across all collections."""
        return sum(c.points_synced for c in self.collections_synced)

    @property
    def successful_collections(self) -> int:
        """Number of successfully synced collections."""
        return sum(1 for c in self.collections_synced if c.success)

    @property
    def failed_collections(self) -> int:
        """Number of failed collections."""
        return sum(1 for c in self.collections_synced if not c.success)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "success": self.success,
            "status": self.status.value,
            "message": self.message,
            "total_points_synced": self.total_points_synced,
            "successful_collections": self.successful_collections,
            "failed_collections": self.failed_collections,
            "collections": [c.to_dict() for c in self.collections_synced],
            "errors": self.errors,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }


class RAGSync:
    """
    Synchronizes Qdrant embeddings from production to test system.

    The RAG sync ensures that the test system has the same embedding data
    as production, allowing for realistic testing of RAG-based features.

    Attributes:
        production_qdrant_url: URL of the production Qdrant instance.
        test_qdrant_url: URL of the test Qdrant instance.
        timeout: HTTP timeout in seconds.
        batch_size: Number of points to sync in each batch.
    """

    def __init__(
        self,
        production_qdrant_url: str | None = None,
        test_qdrant_url: str | None = None,
        timeout: float = 60.0,
        batch_size: int = 100,
    ) -> None:
        """
        Initialize the RAG sync.

        Args:
            production_qdrant_url: URL of production Qdrant. Defaults to http://localhost:6333.
            test_qdrant_url: URL of test Qdrant. Defaults to http://localhost:6335.
            timeout: HTTP timeout in seconds.
            batch_size: Number of points to sync per batch.
        """
        self.production_qdrant_url = production_qdrant_url or "http://localhost:6333"
        self.test_qdrant_url = test_qdrant_url or "http://localhost:6335"
        self.timeout = timeout
        self.batch_size = batch_size

    async def _check_qdrant_health(self, url: str) -> bool:
        """
        Check if a Qdrant instance is healthy.

        Args:
            url: The Qdrant base URL.

        Returns:
            True if healthy, False otherwise.
        """
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{url}/healthz")
                return response.status_code == 200
        except Exception:
            return False

    async def _list_collections(self, url: str) -> list[str]:
        """
        List all collections in a Qdrant instance.

        Args:
            url: The Qdrant base URL.

        Returns:
            List of collection names.
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(f"{url}/collections")
                if response.status_code == 200:
                    data = response.json()
                    collections = data.get("result", {}).get("collections", [])
                    return [c.get("name") for c in collections if c.get("name")]
                return []
        except Exception:
            return []

    async def _get_collection_info(self, url: str, collection_name: str) -> dict | None:
        """
        Get information about a collection.

        Args:
            url: The Qdrant base URL.
            collection_name: Name of the collection.

        Returns:
            Collection info dict or None if not found.
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(f"{url}/collections/{collection_name}")
                if response.status_code == 200:
                    return response.json().get("result")
                return None
        except Exception:
            return None

    async def _create_collection(
        self,
        url: str,
        collection_name: str,
        vector_config: dict,
    ) -> bool:
        """
        Create a collection in Qdrant.

        Args:
            url: The Qdrant base URL.
            collection_name: Name of the collection to create.
            vector_config: Vector configuration from source collection.

        Returns:
            True if created successfully, False otherwise.
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                # First, try to delete existing collection
                await client.delete(f"{url}/collections/{collection_name}")

                # Create the collection with the same config
                payload = {"vectors": vector_config}
                response = await client.put(
                    f"{url}/collections/{collection_name}",
                    json=payload,
                )
                return response.status_code in (200, 201)
        except Exception:
            return False

    async def _get_points_batch(
        self,
        url: str,
        collection_name: str,
        offset: int | None,
        limit: int,
    ) -> tuple[list[dict], int | None]:
        """
        Get a batch of points from a collection.

        Args:
            url: The Qdrant base URL.
            collection_name: Name of the collection.
            offset: Offset point ID (None for first batch).
            limit: Number of points to retrieve.

        Returns:
            Tuple of (points list, next_offset).
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                payload: dict[str, Any] = {
                    "limit": limit,
                    "with_payload": True,
                    "with_vector": True,
                }
                if offset is not None:
                    payload["offset"] = offset

                response = await client.post(
                    f"{url}/collections/{collection_name}/points/scroll",
                    json=payload,
                )

                if response.status_code == 200:
                    result = response.json().get("result", {})
                    points = result.get("points", [])
                    next_offset = result.get("next_page_offset")
                    return points, next_offset

                return [], None
        except Exception:
            return [], None

    async def _upsert_points(
        self,
        url: str,
        collection_name: str,
        points: list[dict],
    ) -> bool:
        """
        Upsert points into a collection.

        Args:
            url: The Qdrant base URL.
            collection_name: Name of the collection.
            points: List of points to upsert.

        Returns:
            True if successful, False otherwise.
        """
        if not points:
            return True

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                payload = {"points": points}
                response = await client.put(
                    f"{url}/collections/{collection_name}/points",
                    json=payload,
                )
                return response.status_code == 200
        except Exception:
            return False

    async def _sync_collection(
        self,
        collection_name: str,
    ) -> CollectionSyncResult:
        """
        Sync a single collection from production to test.

        Args:
            collection_name: Name of the collection to sync.

        Returns:
            CollectionSyncResult with sync status.
        """
        result = CollectionSyncResult(
            collection_name=collection_name,
            success=False,
        )

        # Get source collection info
        source_info = await self._get_collection_info(
            self.production_qdrant_url,
            collection_name,
        )

        if not source_info:
            result.error = f"Could not get info for collection {collection_name}"
            return result

        # Get vector config
        vector_config = source_info.get("config", {}).get("params", {}).get("vectors")
        if not vector_config:
            result.error = "Could not get vector configuration"
            return result

        # Create collection in test system
        if not await self._create_collection(
            self.test_qdrant_url,
            collection_name,
            vector_config,
        ):
            result.error = "Failed to create collection in test system"
            return result

        # Sync all points in batches
        offset = None
        total_synced = 0

        while True:
            points, next_offset = await self._get_points_batch(
                self.production_qdrant_url,
                collection_name,
                offset,
                self.batch_size,
            )

            if not points:
                break

            # Upsert points to test
            if not await self._upsert_points(
                self.test_qdrant_url,
                collection_name,
                points,
            ):
                result.error = f"Failed to upsert points at offset {offset}"
                return result

            total_synced += len(points)

            if next_offset is None:
                break

            offset = next_offset

        result.success = True
        result.points_synced = total_synced

        return result

    async def sync_collections(
        self,
        collections: list[str] | None = None,
    ) -> SyncResult:
        """
        Sync Qdrant collections from production to test.

        Args:
            collections: Optional list of collection names to sync.
                        If None, syncs all collections.

        Returns:
            SyncResult with sync status.
        """
        result = SyncResult(
            success=False,
            status=SyncStatus.CONNECTING,
            message="Starting RAG sync",
        )

        # Check production Qdrant health
        if not await self._check_qdrant_health(self.production_qdrant_url):
            result.status = SyncStatus.FAILED
            result.message = f"Production Qdrant not healthy at {self.production_qdrant_url}"
            result.errors.append(result.message)
            result.completed_at = datetime.now()
            return result

        # Check test Qdrant health
        if not await self._check_qdrant_health(self.test_qdrant_url):
            result.status = SyncStatus.FAILED
            result.message = f"Test Qdrant not healthy at {self.test_qdrant_url}"
            result.errors.append(result.message)
            result.completed_at = datetime.now()
            return result

        result.status = SyncStatus.SYNCING

        # Get collections to sync
        if collections is None:
            collections = await self._list_collections(self.production_qdrant_url)

        if not collections:
            result.status = SyncStatus.COMPLETED
            result.success = True
            result.message = "No collections to sync"
            result.completed_at = datetime.now()
            return result

        # Sync each collection
        for collection_name in collections:
            collection_result = await self._sync_collection(collection_name)
            result.collections_synced.append(collection_result)

            if not collection_result.success:
                result.errors.append(
                    f"Failed to sync {collection_name}: {collection_result.error}"
                )

        # Determine overall success
        if result.failed_collections > 0:
            result.status = SyncStatus.FAILED
            result.message = (
                f"Sync completed with {result.failed_collections} failed collection(s)"
            )
        else:
            result.success = True
            result.status = SyncStatus.COMPLETED
            result.message = (
                f"Synced {result.successful_collections} collection(s), "
                f"{result.total_points_synced} total points"
            )

        result.completed_at = datetime.now()
        return result

    async def get_sync_status(self) -> dict[str, Any]:
        """
        Get the current sync status of production and test Qdrant instances.

        Returns:
            Dictionary with status information for both instances.
        """
        status: dict[str, Any] = {
            "production": {
                "url": self.production_qdrant_url,
                "healthy": False,
                "collections": [],
                "total_points": 0,
            },
            "test": {
                "url": self.test_qdrant_url,
                "healthy": False,
                "collections": [],
                "total_points": 0,
            },
        }

        # Check production
        if await self._check_qdrant_health(self.production_qdrant_url):
            status["production"]["healthy"] = True
            collections = await self._list_collections(self.production_qdrant_url)
            status["production"]["collections"] = collections

            # Get point counts for each collection
            total = 0
            for collection in collections:
                info = await self._get_collection_info(
                    self.production_qdrant_url, collection
                )
                if info:
                    count = info.get("points_count", 0)
                    total += count
            status["production"]["total_points"] = total

        # Check test
        if await self._check_qdrant_health(self.test_qdrant_url):
            status["test"]["healthy"] = True
            collections = await self._list_collections(self.test_qdrant_url)
            status["test"]["collections"] = collections

            # Get point counts for each collection
            total = 0
            for collection in collections:
                info = await self._get_collection_info(self.test_qdrant_url, collection)
                if info:
                    count = info.get("points_count", 0)
                    total += count
            status["test"]["total_points"] = total

        # Calculate sync status
        status["in_sync"] = (
            status["production"]["healthy"]
            and status["test"]["healthy"]
            and set(status["production"]["collections"])
            == set(status["test"]["collections"])
            and status["production"]["total_points"]
            == status["test"]["total_points"]
        )

        return status

    async def verify_sync(self) -> dict[str, Any]:
        """
        Verify that the test system is properly synced with production.

        Returns:
            Dictionary with verification results.
        """
        verification: dict[str, Any] = {
            "verified": False,
            "production_collections": [],
            "test_collections": [],
            "missing_in_test": [],
            "extra_in_test": [],
            "point_count_mismatches": [],
        }

        # Get production collections
        prod_collections = await self._list_collections(self.production_qdrant_url)
        verification["production_collections"] = prod_collections

        # Get test collections
        test_collections = await self._list_collections(self.test_qdrant_url)
        verification["test_collections"] = test_collections

        # Check for missing/extra collections
        prod_set = set(prod_collections)
        test_set = set(test_collections)

        verification["missing_in_test"] = list(prod_set - test_set)
        verification["extra_in_test"] = list(test_set - prod_set)

        # Check point counts for common collections
        for collection in prod_set & test_set:
            prod_info = await self._get_collection_info(
                self.production_qdrant_url, collection
            )
            test_info = await self._get_collection_info(
                self.test_qdrant_url, collection
            )

            if prod_info and test_info:
                prod_count = prod_info.get("points_count", 0)
                test_count = test_info.get("points_count", 0)

                if prod_count != test_count:
                    verification["point_count_mismatches"].append({
                        "collection": collection,
                        "production_count": prod_count,
                        "test_count": test_count,
                    })

        # Determine if verified
        verification["verified"] = (
            not verification["missing_in_test"]
            and not verification["extra_in_test"]
            and not verification["point_count_mismatches"]
        )

        return verification


def create_rag_sync(
    production_qdrant_url: str | None = None,
    test_qdrant_url: str | None = None,
) -> RAGSync:
    """
    Factory function to create a RAGSync instance.

    Args:
        production_qdrant_url: Optional production Qdrant URL.
        test_qdrant_url: Optional test Qdrant URL.

    Returns:
        Configured RAGSync instance.
    """
    return RAGSync(
        production_qdrant_url=production_qdrant_url,
        test_qdrant_url=test_qdrant_url,
    )
