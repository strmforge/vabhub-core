import pytest
import json
from datetime import datetime, timedelta
from unittest.mock import patch, AsyncMock

from core.database import DatabaseManager


class TestDatabaseManager:
    """Test cases for DatabaseManager class."""

    @pytest.mark.asyncio
    async def test_database_initialization(self, database_manager):
        """Test database initialization and table creation."""
        # Verify that database is properly initialized
        assert database_manager.engine is not None
        assert database_manager.session is not None

        # Verify that tables are created
        tables = await database_manager.execute_query(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
        table_names = [table["name"] for table in tables]

        expected_tables = [
            "users",
            "subscriptions",
            "tasks",
            "charts_data",
            "chart_items",
            "media_servers",
            "downloaders",
        ]

        for table in expected_tables:
            assert table in table_names

    @pytest.mark.asyncio
    async def test_save_charts_data(self, database_manager, sample_chart_data):
        """Test saving charts data to database."""
        expires_at = (datetime.now() + timedelta(hours=1)).isoformat()

        chart_id = await database_manager.save_charts_data(
            source=sample_chart_data["source"],
            region=sample_chart_data["region"],
            time_range=sample_chart_data["time_range"],
            media_type=sample_chart_data["media_type"],
            chart_data=json.dumps(sample_chart_data["chart_data"]),
            expires_at=expires_at,
        )

        assert chart_id is not None
        assert chart_id.startswith("chart_")

        # Verify data was saved
        saved_data = await database_manager.get_charts_data(
            source=sample_chart_data["source"],
            region=sample_chart_data["region"],
            time_range=sample_chart_data["time_range"],
            media_type=sample_chart_data["media_type"],
        )

        assert saved_data is not None
        assert saved_data["source"] == sample_chart_data["source"]
        assert saved_data["region"] == sample_chart_data["region"]

    @pytest.mark.asyncio
    async def test_get_charts_data_not_found(self, database_manager):
        """Test getting non-existent charts data."""
        result = await database_manager.get_charts_data(
            source="nonexistent",
            region="nonexistent",
            time_range="nonexistent",
            media_type="nonexistent",
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_save_chart_items(self, database_manager, sample_chart_data):
        """Test saving chart items to database."""
        expires_at = (datetime.now() + timedelta(hours=1)).isoformat()

        chart_id = await database_manager.save_charts_data(
            source=sample_chart_data["source"],
            region=sample_chart_data["region"],
            time_range=sample_chart_data["time_range"],
            media_type=sample_chart_data["media_type"],
            chart_data=json.dumps(sample_chart_data["chart_data"]),
            expires_at=expires_at,
        )

        # Save chart items
        chart_items = sample_chart_data["chart_data"]["items"]
        success = await database_manager.save_chart_items(chart_id, chart_items)

        assert success is True

        # Verify items were saved
        saved_items = await database_manager.get_chart_items(chart_id)
        assert len(saved_items) == len(chart_items)
        assert saved_items[0]["title"] == chart_items[0]["title"]

    @pytest.mark.asyncio
    async def test_subscription_crud_operations(self, database_manager):
        """Test subscription CRUD operations."""
        # Create subscription
        subscription_data = {
            "name": "Test Subscription",
            "query": "test query",
            "enabled": True,
            "priority": 1,
        }

        subscription_id = await database_manager.create_subscription(subscription_data)
        assert subscription_id is not None

        # Get all subscriptions
        subscriptions = await database_manager.get_subscriptions()
        assert len(subscriptions) > 0

        # Get specific subscription
        subscription = await database_manager.get_subscription(subscription_id)
        assert subscription is not None
        assert subscription["name"] == subscription_data["name"]

        # Update subscription
        update_data = {
            "name": "Updated Subscription",
            "query": "updated query",
            "enabled": False,
            "priority": 2,
        }

        success = await database_manager.update_subscription(
            subscription_id, update_data
        )
        assert success is True

        # Verify update
        updated_subscription = await database_manager.get_subscription(subscription_id)
        assert updated_subscription["name"] == update_data["name"]

        # Delete subscription
        delete_success = await database_manager.delete_subscription(subscription_id)
        assert delete_success is True

        # Verify deletion
        deleted_subscription = await database_manager.get_subscription(subscription_id)
        assert deleted_subscription is None

    @pytest.mark.asyncio
    async def test_task_crud_operations(self, database_manager):
        """Test task CRUD operations."""
        # Create task
        task_data = {
            "name": "Test Task",
            "type": "download",
            "status": "pending",
            "progress": 0,
        }

        task_id = await database_manager.create_task(task_data)
        assert task_id is not None

        # Get tasks
        tasks = await database_manager.get_tasks()
        assert len(tasks) > 0

        # Update task status
        success = await database_manager.update_task_status(
            task_id, "running", 50, "Processing..."
        )
        assert success is True

        # Verify update
        running_tasks = await database_manager.get_tasks("running")
        assert len(running_tasks) > 0
        assert running_tasks[0]["progress"] == 50

    @pytest.mark.asyncio
    async def test_media_servers_and_downloaders(self, database_manager):
        """Test media servers and downloaders retrieval."""
        # Test media servers
        media_servers = await database_manager.get_media_servers()
        assert isinstance(media_servers, list)

        # Test downloaders
        downloaders = await database_manager.get_downloaders()
        assert isinstance(downloaders, list)

    @pytest.mark.asyncio
    async def test_execute_query_error_handling(self, database_manager):
        """Test error handling in execute_query."""
        # Test with invalid SQL
        with pytest.raises(Exception):
            await database_manager.execute_query("INVALID SQL")

    @pytest.mark.asyncio
    async def test_execute_update_error_handling(self, database_manager):
        """Test error handling in execute_update."""
        # Test with invalid SQL
        with pytest.raises(Exception):
            await database_manager.execute_update("INVALID SQL", ())

    @pytest.mark.asyncio
    async def test_charts_data_expiration(self, database_manager, sample_chart_data):
        """Test charts data expiration logic."""
        # Save data with past expiration
        past_expires = (datetime.now() - timedelta(hours=1)).isoformat()

        chart_id = await database_manager.save_charts_data(
            source=sample_chart_data["source"],
            region=sample_chart_data["region"],
            time_range=sample_chart_data["time_range"],
            media_type=sample_chart_data["media_type"],
            chart_data=json.dumps(sample_chart_data["chart_data"]),
            expires_at=past_expires,
        )

        # Should not return expired data
        result = await database_manager.get_charts_data(
            source=sample_chart_data["source"],
            region=sample_chart_data["region"],
            time_range=sample_chart_data["time_range"],
            media_type=sample_chart_data["media_type"],
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_database_connection_pooling(self, database_manager):
        """Test database connection pooling."""
        # Test multiple concurrent operations
        import asyncio

        async def test_operation(i):
            return await database_manager.execute_query("SELECT ?", (i,))

        # Run multiple concurrent queries
        tasks = [test_operation(i) for i in range(5)]
        results = await asyncio.gather(*tasks)

        assert len(results) == 5
        for i, result in enumerate(results):
            assert result[0][0] == i

    @pytest.mark.asyncio
    async def test_database_close(self, temp_db_path):
        """Test database close operation."""
        db_url = f"sqlite:///{temp_db_path}"
        db = DatabaseManager(db_url)
        await db.initialize()

        # Verify database is open
        assert db.engine is not None
        assert db.session is not None

        # Close database
        await db.close()

        # Verify database is closed
        assert db.engine is None
        assert db.session is None
