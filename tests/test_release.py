import time_machine

from blurb._release import current_date


@time_machine.travel("2025-01-07")
def test_current_date():
    assert current_date() == "2025-01-07"
