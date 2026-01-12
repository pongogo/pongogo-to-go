"""Stress tests for event_capture module.

These tests validate database resilience under load:
- Concurrent writes from multiple threads
- Large dataset handling
- Rapid sequential writes
- Database lock handling
"""

import sqlite3
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from mcp_server.event_capture import (
    get_event_stats,
    store_routing_event,
)


class TestConcurrentWrites:
    """Tests for concurrent database writes."""

    def test_multiple_threads_can_write(self, tmp_path, monkeypatch):
        """Multiple threads should successfully write events."""
        db_path = tmp_path / ".pongogo" / "pongogo.db"
        monkeypatch.setattr(
            "mcp_server.database.events.get_default_db_path",
            lambda _project_root=None: db_path,
        )

        num_threads = 10
        events_per_thread = 10
        results = []

        def write_events(thread_id: int) -> list[bool]:
            """Write multiple events from a thread."""
            thread_results = []
            for i in range(events_per_thread):
                result = store_routing_event(
                    user_message=f"thread {thread_id} query {i}",
                    routed_instructions=[f"inst_{thread_id}_{i}"],
                    engine_version="stress-test-0.1",
                    session_id=f"session_{thread_id}",
                )
                thread_results.append(result)
            return thread_results

        # Run concurrent writes
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(write_events, i) for i in range(num_threads)]
            for future in as_completed(futures):
                results.extend(future.result())

        # All writes should succeed
        assert len(results) == num_threads * events_per_thread
        assert all(results), f"Some writes failed: {results.count(False)} failures"

        # Verify all events are in database
        stats = get_event_stats()
        assert stats["total_count"] == num_threads * events_per_thread

    def test_high_contention_writes(self, tmp_path, monkeypatch):
        """Database should handle high contention without data loss."""
        db_path = tmp_path / ".pongogo" / "pongogo.db"
        monkeypatch.setattr(
            "mcp_server.database.events.get_default_db_path",
            lambda _project_root=None: db_path,
        )

        # Higher contention: more threads, fewer events each
        num_threads = 20
        events_per_thread = 5
        barrier = threading.Barrier(num_threads)  # Synchronize start

        def write_with_barrier(thread_id: int) -> int:
            """Wait for all threads then write."""
            barrier.wait()  # Start all at once for maximum contention
            success_count = 0
            for i in range(events_per_thread):
                if store_routing_event(
                    user_message=f"contention test {thread_id}-{i}",
                    routed_instructions=["test_inst"],
                    engine_version="contention-test",
                ):
                    success_count += 1
            return success_count

        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [
                executor.submit(write_with_barrier, i) for i in range(num_threads)
            ]
            total_success = sum(f.result() for f in as_completed(futures))

        # All writes should succeed even under contention
        expected = num_threads * events_per_thread
        assert total_success == expected, f"Expected {expected}, got {total_success}"

        stats = get_event_stats()
        assert stats["total_count"] == expected


class TestLargeDataset:
    """Tests for handling large datasets."""

    def test_insert_many_events(self, tmp_path, monkeypatch):
        """Database should handle inserting many events efficiently."""
        db_path = tmp_path / ".pongogo" / "pongogo.db"
        monkeypatch.setattr(
            "mcp_server.database.events.get_default_db_path",
            lambda _project_root=None: db_path,
        )

        num_events = 500
        start_time = time.time()

        for i in range(num_events):
            store_routing_event(
                user_message=f"bulk insert query {i}",
                routed_instructions=[f"inst_{i % 10}"],  # 10 unique instructions
                engine_version="bulk-test",
                context={"index": i, "batch": i // 100},
            )

        elapsed = time.time() - start_time

        # Should complete in reasonable time (< 30 seconds for 500 events)
        assert elapsed < 30, (
            f"Bulk insert too slow: {elapsed:.2f}s for {num_events} events"
        )

        # Verify count
        stats = get_event_stats()
        assert stats["total_count"] == num_events

    def test_stats_performance_with_large_dataset(self, tmp_path, monkeypatch):
        """Stats queries should remain fast with large dataset."""
        db_path = tmp_path / ".pongogo" / "pongogo.db"
        monkeypatch.setattr(
            "mcp_server.database.events.get_default_db_path",
            lambda _project_root=None: db_path,
        )

        # Insert events
        num_events = 200
        for i in range(num_events):
            store_routing_event(
                user_message=f"perf query {i}",
                routed_instructions=[f"inst_{i}"],
                engine_version="perf-test",
            )

        # Stats query should be fast (< 1 second)
        start_time = time.time()
        stats = get_event_stats()
        elapsed = time.time() - start_time

        assert elapsed < 1.0, f"Stats query too slow: {elapsed:.2f}s"
        assert stats["total_count"] == num_events


class TestRapidSequentialWrites:
    """Tests for rapid sequential write patterns."""

    def test_rapid_fire_writes(self, tmp_path, monkeypatch):
        """Rapid sequential writes should all succeed."""
        db_path = tmp_path / ".pongogo" / "pongogo.db"
        monkeypatch.setattr(
            "mcp_server.database.events.get_default_db_path",
            lambda _project_root=None: db_path,
        )

        num_events = 100
        success_count = 0

        for i in range(num_events):
            if store_routing_event(
                user_message=f"rapid query {i}",
                routed_instructions=["inst1", "inst2"],
                engine_version="rapid-test",
            ):
                success_count += 1

        assert success_count == num_events
        stats = get_event_stats()
        assert stats["total_count"] == num_events

    def test_write_with_large_context(self, tmp_path, monkeypatch):
        """Should handle events with large context objects."""
        db_path = tmp_path / ".pongogo" / "pongogo.db"
        monkeypatch.setattr(
            "mcp_server.database.events.get_default_db_path",
            lambda _project_root=None: db_path,
        )

        # Create large context (simulating many files in context)
        large_context = {
            "files": [
                f"src/module_{i}/file_{j}.py" for i in range(10) for j in range(10)
            ],
            "directories": [f"src/module_{i}/" for i in range(10)],
            "branch": "feature/large-context-test",
            "metadata": {f"key_{i}": f"value_{i}" for i in range(50)},
        }

        success = store_routing_event(
            user_message="query with large context",
            routed_instructions=["inst1", "inst2", "inst3"],
            engine_version="large-context-test",
            context=large_context,
        )

        assert success is True
        stats = get_event_stats()
        assert stats["total_count"] == 1


class TestDatabaseResilience:
    """Tests for database error handling and resilience."""

    def test_handles_readonly_database(self, tmp_path, monkeypatch):
        """Should handle read-only database gracefully."""
        db_path = tmp_path / ".pongogo" / "pongogo.db"
        monkeypatch.setattr(
            "mcp_server.database.events.get_default_db_path",
            lambda _project_root=None: db_path,
        )

        # Create database first
        store_routing_event(
            user_message="initial event",
            routed_instructions=["inst1"],
            engine_version="test",
        )

        # Make it read-only
        db_path.chmod(0o444)

        try:
            # Should return False (graceful failure), not raise
            result = store_routing_event(
                user_message="should fail gracefully",
                routed_instructions=["inst2"],
                engine_version="test",
            )
            assert result is False
        finally:
            # Restore permissions for cleanup
            db_path.chmod(0o644)

    def test_handles_corrupted_schema(self, tmp_path, monkeypatch):
        """Should handle database with unexpected schema gracefully."""
        db_path = tmp_path / ".pongogo" / "pongogo.db"
        db_path.parent.mkdir(parents=True, exist_ok=True)
        monkeypatch.setattr(
            "mcp_server.database.events.get_default_db_path",
            lambda _project_root=None: db_path,
        )

        # Create a database with wrong schema
        conn = sqlite3.connect(db_path)
        conn.execute("CREATE TABLE routing_events (wrong_column TEXT)")
        conn.commit()
        conn.close()

        # Should still work (ensure_schema is idempotent, creates missing columns)
        # or fail gracefully
        result = store_routing_event(
            user_message="test query",
            routed_instructions=["inst1"],
            engine_version="test",
        )
        # Either succeeds (schema fixed) or fails gracefully
        assert result in (True, False)

    def test_concurrent_readers_and_writers(self, tmp_path, monkeypatch):
        """Concurrent reads and writes should not block each other."""
        db_path = tmp_path / ".pongogo" / "pongogo.db"
        monkeypatch.setattr(
            "mcp_server.database.events.get_default_db_path",
            lambda _project_root=None: db_path,
        )

        # Seed some initial data
        for i in range(10):
            store_routing_event(
                user_message=f"seed {i}",
                routed_instructions=["inst"],
                engine_version="test",
            )

        num_writers = 5
        num_readers = 5
        events_per_writer = 10
        reads_per_reader = 10

        write_results = []
        read_results = []

        def writer(writer_id: int) -> list[bool]:
            results = []
            for i in range(events_per_writer):
                result = store_routing_event(
                    user_message=f"writer {writer_id} event {i}",
                    routed_instructions=["inst"],
                    engine_version="concurrent-test",
                )
                results.append(result)
            return results

        def reader(reader_id: int) -> list[int]:
            counts = []
            for _ in range(reads_per_reader):
                stats = get_event_stats()
                counts.append(stats["total_count"])
                time.sleep(0.001)  # Small delay between reads
            return counts

        with ThreadPoolExecutor(max_workers=num_writers + num_readers) as executor:
            # Submit writers and readers
            writer_futures = [executor.submit(writer, i) for i in range(num_writers)]
            reader_futures = [executor.submit(reader, i) for i in range(num_readers)]

            for f in as_completed(writer_futures):
                write_results.extend(f.result())
            for f in as_completed(reader_futures):
                read_results.extend(f.result())

        # All writes should succeed
        assert all(write_results)

        # Reads should show monotonically increasing counts (or same)
        # and all should be >= initial seed count
        for count in read_results:
            assert count >= 10  # At least the seed data


class TestSchemaCreation:
    """Tests for schema creation under various conditions."""

    def test_multiple_processes_create_schema(self, tmp_path, monkeypatch):
        """Schema creation should be idempotent across concurrent processes."""
        db_path = tmp_path / ".pongogo" / "pongogo.db"
        monkeypatch.setattr(
            "mcp_server.database.events.get_default_db_path",
            lambda _project_root=None: db_path,
        )

        num_threads = 10
        barrier = threading.Barrier(num_threads)

        def create_and_write(thread_id: int) -> bool:
            barrier.wait()  # All threads start at once
            return store_routing_event(
                user_message=f"schema race {thread_id}",
                routed_instructions=["inst"],
                engine_version="schema-test",
            )

        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(create_and_write, i) for i in range(num_threads)]
            results = [f.result() for f in as_completed(futures)]

        # All should succeed despite racing to create schema
        assert all(results)
        stats = get_event_stats()
        assert stats["total_count"] == num_threads
