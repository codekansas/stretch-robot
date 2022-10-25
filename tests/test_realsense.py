import itertools

import numpy as np
import pytest
from PIL import Image

from stretch.cpp.realsense import ColorFrameGenerator
from stretch.cpp.realsense.lib import device_count


@pytest.mark.realsense
def test_realsense() -> None:
    assert device_count() > 0
    for frame in itertools.islice(ColorFrameGenerator(), 3):
        arr = np.array(frame, copy=False)
        img = Image.fromarray(arr)
        assert img.size > (0, 0)
