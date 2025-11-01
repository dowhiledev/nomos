import pytest

from nomos.core.schemas import Checkpoint
from nomos.core.store.checkpoint_memory import InMemoryCheckpointStore


@pytest.mark.asyncio
async def test_checkpoint_store_save_and_load():
    store = InMemoryCheckpointStore()
    session_id = "s1"
    checkpoint = Checkpoint(id="cp1", node_id="n1", data={"k": "v"})
    await store.save(session_id, checkpoint)
    loaded = await store.load(session_id, "cp1")
    assert loaded.node_id == "n1"
    assert loaded.data["k"] == "v"
