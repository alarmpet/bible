# -*- coding: utf-8 -*-
from __future__ import annotations
import cv2
import numpy as np
from pathlib import Path
import pytest

from postflight_release import check_decoded_stream_motion_mae

def test_frozen_static_frames_fail_motion_gate():
    # 30 identical frames (static hold)
    frames = [np.full((360, 640, 3), 128, dtype=np.uint8) for _ in range(30)]
    # Subtitle change at bottom 15% should NOT count as motion
    for f in frames[15:]:
        f[310:350, :] = 255
        
    passed, min_mae, msg = check_decoded_stream_motion_mae(frames, window_size=25, min_mae_threshold=0.85)
    assert passed is False
    assert min_mae < 0.85
    assert "static hold" in msg.lower() or "frozen" in msg.lower() or "low motion" in msg.lower()


def test_continuous_motion_frames_pass_motion_gate():
    # 30 panning frames
    frames = []
    for i in range(30):
        img = np.zeros((360, 640, 3), dtype=np.uint8)
        # Shift a bright block horizontally across frames
        x_start = int(50 + i * 8)
        img[100:260, x_start:x_start + 120] = 200
        frames.append(img)
        
    passed, min_mae, msg = check_decoded_stream_motion_mae(frames, window_size=25, min_mae_threshold=0.85)
    assert passed is True
    assert min_mae >= 0.85
