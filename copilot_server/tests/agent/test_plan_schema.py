import pytest
import asyncpg

DATABASE_URL = "postgresql://eve:EvE_Pr0ject_2024@localhost/eve_sde"

@pytest.mark.asyncio
async def test_agent_plans_table_exists():
    """Test that agent_plans table exists with correct schema."""
    conn = await asyncpg.connect(DATABASE_URL)

    # Check table exists
    result = await conn.fetchval("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables
            WHERE table_name = 'agent_plans'
        )
    """)
    assert result is True, "agent_plans table should exist"

    # Check columns
    columns = await conn.fetch("""
        SELECT column_name, data_type, is_nullable
        FROM information_schema.columns
        WHERE table_name = 'agent_plans'
        ORDER BY ordinal_position
    """)

    expected_columns = {
        'id': 'character varying',
        'session_id': 'character varying',
        'purpose': 'text',
        'plan_data': 'jsonb',
        'status': 'character varying',
        'auto_executing': 'boolean',
        'created_at': 'timestamp without time zone',
        'approved_at': 'timestamp without time zone',
        'executed_at': 'timestamp without time zone',
        'completed_at': 'timestamp without time zone',
        'duration_ms': 'integer'
    }

    actual_columns = {row['column_name']: row['data_type'] for row in columns}

    for col_name, col_type in expected_columns.items():
        assert col_name in actual_columns, f"Column {col_name} should exist"
        assert actual_columns[col_name] == col_type, f"Column {col_name} should be {col_type}"

    await conn.close()


@pytest.mark.asyncio
async def test_agent_plans_foreign_key():
    """Test that agent_plans has foreign key to agent_sessions."""
    conn = await asyncpg.connect(DATABASE_URL)

    result = await conn.fetch("""
        SELECT
            tc.constraint_name,
            kcu.column_name,
            ccu.table_name AS foreign_table_name,
            ccu.column_name AS foreign_column_name
        FROM information_schema.table_constraints AS tc
        JOIN information_schema.key_column_usage AS kcu
            ON tc.constraint_name = kcu.constraint_name
        JOIN information_schema.constraint_column_usage AS ccu
            ON ccu.constraint_name = tc.constraint_name
        WHERE tc.table_name = 'agent_plans'
            AND tc.constraint_type = 'FOREIGN KEY'
    """)

    assert len(result) > 0, "Should have foreign key constraint"
    fk = result[0]
    assert fk['column_name'] == 'session_id'
    assert fk['foreign_table_name'] == 'agent_sessions'
    assert fk['foreign_column_name'] == 'id'

    await conn.close()


@pytest.mark.asyncio
async def test_agent_plans_indexes():
    """Test that agent_plans has proper indexes."""
    conn = await asyncpg.connect(DATABASE_URL)

    indexes = await conn.fetch("""
        SELECT indexname, indexdef
        FROM pg_indexes
        WHERE tablename = 'agent_plans'
    """)

    index_names = [idx['indexname'] for idx in indexes]

    # Should have index on session_id and status
    assert any('session_id' in name for name in index_names), "Should have session_id index"
    assert any('status' in name for name in index_names), "Should have status index"

    await conn.close()
