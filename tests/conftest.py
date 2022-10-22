import pytest
from _pytest.python import Function

from stretch.cpp.realsense.lib import device_count as realsense_device_count


def pytest_runtest_setup(item: Function) -> None:
    for mark in item.iter_markers():
        if mark.name == "realsense" and not realsense_device_count() > 0:
            pytest.skip("Skipping because this test requires TensorRT to run")
