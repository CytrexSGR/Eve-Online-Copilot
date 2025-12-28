import pytest
import asyncpg

DATABASE_URL = "postgresql://eve:EvE_Pr0ject_2024@localhost/eve_sde"


@pytest.mark.asyncio
async def test_agent_events_table_exists():
    """Test that agent_events table exists with correct schema."""
    conn = await asyncpg.connect(DATABASE_URL)

    # Check table exists
    result = await conn.fetchval("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables
            WHERE table_name = 'agent_events'
        )
    """)
    assert result is True, "agent_events table should exist"

    # Check columns
    columns = await conn.fetch("""
        SELECT column_name, data_type
        FROM information_schema.columns
        WHERE table_name = 'agent_events'
        ORDER BY ordinal_position
    """)

    expected_columns = {
        'id': 'bigint',
        'session_id': 'character varying',
        'plan_id': 'character varying',
        'event_type': 'character varying',
        'payload': 'jsonb',
        'timestamp': 'timestamp without time zone'
    }

    actual_columns = {row['column_name']: row['data_type'] for row in columns}

    for col_name, col_type in expected_columns.items():
        assert col_name in actual_columns, f"Column {col_name} should exist"
        assert actual_columns[col_name] == col_type

    await conn.close()


@pytest.mark.asyncio
async def test_agent_events_indexes():
    """Test that agent_events has proper indexes."""
    conn = await asyncpg.connect(DATABASE_URL)

    indexes = await conn.fetch("""
        SELECT indexname
        FROM pg_indexes
        WHERE tablename = 'agent_events'
    """)

    index_names = [idx['indexname'] for idx in indexes]

    assert any('session_id' in name for name in index_names)
    assert any('plan_id' in name for name in index_names)
    assert any('event_type' in name for name in index_names)
    assert any('timestamp' in name for name in index_names)

    await conn.close()
