# copilot_server/tests/agent/test_db_schema.py

import pytest
import asyncpg

@pytest.mark.asyncio
async def test_agent_sessions_table_exists():
    """Verify agent_sessions table created correctly."""
    conn = await asyncpg.connect(
        database="eve_sde",
        user="eve",
        password="EvE_Pr0ject_2024",
        host="localhost"
    )

    # Check table exists
    result = await conn.fetchval("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables
            WHERE table_name = 'agent_sessions'
        )
    """)
    assert result is True

    # Check columns
    columns = await conn.fetch("""
        SELECT column_name, data_type
        FROM information_schema.columns
        WHERE table_name = 'agent_sessions'
    """)
    column_names = [r['column_name'] for r in columns]
    assert 'id' in column_names
    assert 'character_id' in column_names
    assert 'status' in column_names

    await conn.close()

@pytest.mark.asyncio
async def test_agent_messages_table_exists():
    """Verify agent_messages table created correctly."""
    conn = await asyncpg.connect(
        database="eve_sde",
        user="eve",
        password="EvE_Pr0ject_2024",
        host="localhost"
    )

    result = await conn.fetchval("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables
            WHERE table_name = 'agent_messages'
        )
    """)
    assert result is True

    await conn.close()
