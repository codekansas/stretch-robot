import pytest

from stretch.cpp.realsense.lib import device_count


@pytest.mark.realsense
def test_realsense() -> None:
    assert device_count() > 0
