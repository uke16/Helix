"""RAG Database Synchronization.

Syncs RAG data (Qdrant embeddings) from production to test system.
This ensures the test system has realistic data for testing.

The sync copies:
- Qdrant collections (embeddings)
- Collection metadata

Note: This is a 1:1 copy, not a selective sync.
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from enum import Enum


class SyncStatus(str, Enum):
    """Status of a sync operation."""
    PENDING = "pending"
    SYNCING = "syncing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class SyncResult:
    """Result of a sync operation."""
    success: bool
    status: SyncStatus
    message: str
    collections_synced: int = 0
    points_synced: int = 0
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None
    details: dict = field(default_factory=dict)


class RAGSync:
    """Syncs RAG data between production and test Qdrant instances."""

    PRODUCTION_QDRANT_URL = "http://localhost:6333"
    TEST_QDRANT_URL = "http://localhost:6335"

    def __init__(
        self,
        production_url: Optional[str] = None,
        test_url: Optional[str] = None,
    ):
        """Initialize RAG sync.

        Args:
            production_url: Production Qdrant URL
            test_url: Test Qdrant URL
        """
        self.production_url = production_url or self.PRODUCTION_QDRANT_URL
        self.test_url = test_url or self.TEST_QDRANT_URL

    async def get_sync_status(self) -> SyncResult:
        """Get current sync status by comparing collections.

        Returns:
            SyncResult with comparison details
        """
        started_at = datetime.now()

        try:
            import aiohttp

            async with aiohttp.ClientSession() as session:
                # Get production collections
                async with session.get(
                    f"{self.production_url}/collections",
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as response:
                    if response.status != 200:
                        return SyncResult(
                            success=False,
                            status=SyncStatus.FAILED,
                            message="Failed to get production collections",
                            started_at=started_at,
                            completed_at=datetime.now(),
                        )
                    prod_data = await response.json()
                    prod_collections = {
                        c["name"] for c in prod_data.get("result", {}).get("collections", [])
                    }

                # Get test collections
                async with session.get(
                    f"{self.test_url}/collections",
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as response:
                    if response.status != 200:
                        return SyncResult(
                            success=False,
                            status=SyncStatus.FAILED,
                            message="Failed to get test collections",
                            started_at=started_at,
                            completed_at=datetime.now(),
                        )
                    test_data = await response.json()
                    test_collections = {
                        c["name"] for c in test_data.get("result", {}).get("collections", [])
                    }

            # Compare
            missing_in_test = prod_collections - test_collections
            extra_in_test = test_collections - prod_collections

            if not missing_in_test:
                status = SyncStatus.COMPLETED
                message = f"Test has all {len(prod_collections)} collections"
            else:
                status = SyncStatus.PENDING
                message = f"Test missing {len(missing_in_test)} collections"

            return SyncResult(
                success=True,
                status=status,
                message=message,
                collections_synced=len(test_collections & prod_collections),
                started_at=started_at,
                completed_at=datetime.now(),
                details={
                    "production_collections": list(prod_collections),
                    "test_collections": list(test_collections),
                    "missing_in_test": list(missing_in_test),
                    "extra_in_test": list(extra_in_test),
                },
            )

        except Exception as e:
            return SyncResult(
                success=False,
                status=SyncStatus.FAILED,
                message="Failed to check sync status",
                error=str(e),
                started_at=started_at,
                completed_at=datetime.now(),
            )

    async def sync_collection(
        self,
        collection_name: str,
        batch_size: int = 100,
    ) -> SyncResult:
        """Sync a single collection from production to test.

        Args:
            collection_name: Name of collection to sync
            batch_size: Number of points per batch

        Returns:
            SyncResult with sync details
        """
        started_at = datetime.now()
        points_synced = 0

        try:
            import aiohttp

            async with aiohttp.ClientSession() as session:
                # Get collection info from production
                async with session.get(
                    f"{self.production_url}/collections/{collection_name}",
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as response:
                    if response.status != 200:
                        return SyncResult(
                            success=False,
                            status=SyncStatus.FAILED,
                            message=f"Collection not found: {collection_name}",
                            started_at=started_at,
                            completed_at=datetime.now(),
                        )
                    collection_info = await response.json()

                # Delete collection in test if exists
                await session.delete(
                    f"{self.test_url}/collections/{collection_name}",
                    timeout=aiohttp.ClientTimeout(total=10),
                )

                # Create collection in test with same config
                config = collection_info.get("result", {}).get("config", {})
                vectors_config = config.get("params", {}).get("vectors", {})

                create_payload = {
                    "vectors": vectors_config,
                }

                async with session.put(
                    f"{self.test_url}/collections/{collection_name}",
                    json=create_payload,
                    timeout=aiohttp.ClientTimeout(total=30),
                ) as response:
                    if response.status not in [200, 201]:
                        error_text = await response.text()
                        return SyncResult(
                            success=False,
                            status=SyncStatus.FAILED,
                            message=f"Failed to create collection in test",
                            error=error_text,
                            started_at=started_at,
                            completed_at=datetime.now(),
                        )

                # Scroll through all points and copy
                offset = None
                while True:
                    scroll_payload = {
                        "limit": batch_size,
                        "with_payload": True,
                        "with_vector": True,
                    }
                    if offset:
                        scroll_payload["offset"] = offset

                    async with session.post(
                        f"{self.production_url}/collections/{collection_name}/points/scroll",
                        json=scroll_payload,
                        timeout=aiohttp.ClientTimeout(total=60),
                    ) as response:
                        if response.status != 200:
                            break
                        scroll_data = await response.json()

                    points = scroll_data.get("result", {}).get("points", [])
                    if not points:
                        break

                    # Upsert points to test
                    upsert_payload = {"points": points}
                    async with session.put(
                        f"{self.test_url}/collections/{collection_name}/points",
                        json=upsert_payload,
                        timeout=aiohttp.ClientTimeout(total=60),
                    ) as response:
                        if response.status not in [200, 201]:
                            error_text = await response.text()
                            return SyncResult(
                                success=False,
                                status=SyncStatus.FAILED,
                                message=f"Failed to upsert points",
                                error=error_text,
                                points_synced=points_synced,
                                started_at=started_at,
                                completed_at=datetime.now(),
                            )

                    points_synced += len(points)
                    offset = scroll_data.get("result", {}).get("next_page_offset")

                    if not offset:
                        break

            return SyncResult(
                success=True,
                status=SyncStatus.COMPLETED,
                message=f"Synced {points_synced} points from {collection_name}",
                collections_synced=1,
                points_synced=points_synced,
                started_at=started_at,
                completed_at=datetime.now(),
            )

        except Exception as e:
            return SyncResult(
                success=False,
                status=SyncStatus.FAILED,
                message=f"Failed to sync collection {collection_name}",
                error=str(e),
                points_synced=points_synced,
                started_at=started_at,
                completed_at=datetime.now(),
            )

    async def sync_all_collections(
        self,
        batch_size: int = 100,
    ) -> SyncResult:
        """Sync all collections from production to test.

        Args:
            batch_size: Number of points per batch

        Returns:
            SyncResult with overall sync status
        """
        started_at = datetime.now()
        collections_synced = 0
        total_points = 0
        errors = []

        try:
            import aiohttp

            async with aiohttp.ClientSession() as session:
                # Get all production collections
                async with session.get(
                    f"{self.production_url}/collections",
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as response:
                    if response.status != 200:
                        return SyncResult(
                            success=False,
                            status=SyncStatus.FAILED,
                            message="Failed to get production collections",
                            started_at=started_at,
                            completed_at=datetime.now(),
                        )
                    data = await response.json()
                    collections = [
                        c["name"] for c in data.get("result", {}).get("collections", [])
                    ]

            # Sync each collection
            for collection_name in collections:
                result = await self.sync_collection(collection_name, batch_size)
                if result.success:
                    collections_synced += 1
                    total_points += result.points_synced
                else:
                    errors.append(f"{collection_name}: {result.error}")

            success = len(errors) == 0

            return SyncResult(
                success=success,
                status=SyncStatus.COMPLETED if success else SyncStatus.FAILED,
                message=f"Synced {collections_synced}/{len(collections)} collections, {total_points} points",
                collections_synced=collections_synced,
                points_synced=total_points,
                started_at=started_at,
                completed_at=datetime.now(),
                error="; ".join(errors) if errors else None,
                details={
                    "total_collections": len(collections),
                    "synced_collections": collections_synced,
                    "errors": errors,
                },
            )

        except Exception as e:
            return SyncResult(
                success=False,
                status=SyncStatus.FAILED,
                message="Failed to sync collections",
                error=str(e),
                collections_synced=collections_synced,
                points_synced=total_points,
                started_at=started_at,
                completed_at=datetime.now(),
            )

    async def verify_sync(self) -> SyncResult:
        """Verify that test system has same data as production.

        Compares point counts for all collections.

        Returns:
            SyncResult with verification details
        """
        started_at = datetime.now()

        try:
            import aiohttp

            mismatches = []

            async with aiohttp.ClientSession() as session:
                # Get production collections
                async with session.get(
                    f"{self.production_url}/collections",
                ) as response:
                    prod_data = await response.json()
                    prod_collections = [
                        c["name"] for c in prod_data.get("result", {}).get("collections", [])
                    ]

                for collection_name in prod_collections:
                    # Get production count
                    async with session.get(
                        f"{self.production_url}/collections/{collection_name}",
                    ) as response:
                        prod_info = await response.json()
                        prod_count = prod_info.get("result", {}).get("points_count", 0)

                    # Get test count
                    async with session.get(
                        f"{self.test_url}/collections/{collection_name}",
                    ) as response:
                        if response.status != 200:
                            mismatches.append(f"{collection_name}: missing in test")
                            continue
                        test_info = await response.json()
                        test_count = test_info.get("result", {}).get("points_count", 0)

                    if prod_count != test_count:
                        mismatches.append(
                            f"{collection_name}: prod={prod_count}, test={test_count}"
                        )

            success = len(mismatches) == 0

            return SyncResult(
                success=success,
                status=SyncStatus.COMPLETED if success else SyncStatus.PENDING,
                message="Sync verified" if success else f"{len(mismatches)} mismatches found",
                collections_synced=len(prod_collections),
                started_at=started_at,
                completed_at=datetime.now(),
                details={"mismatches": mismatches},
            )

        except Exception as e:
            return SyncResult(
                success=False,
                status=SyncStatus.FAILED,
                message="Verification failed",
                error=str(e),
                started_at=started_at,
                completed_at=datetime.now(),
            )
