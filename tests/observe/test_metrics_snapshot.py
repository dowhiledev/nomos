from nomos.core.observe import measure, LATENCY_HIST


def test_measure_records_latency():
    with measure("unit.test.work"):
        # trivial fast block
        pass
    assert "unit.test.work" in LATENCY_HIST
    assert len(LATENCY_HIST["unit.test.work"]) >= 1
