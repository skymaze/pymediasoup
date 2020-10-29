import unittest
from aiortc import VideoStreamTrack
import cv2

from pymediasoup import Device
from pymediasoup import AiortcHandler

TRACKS = [VideoStreamTrack()]


class TestMethods(unittest.TestCase):
    def test_create_device(self):
        device = Device(handlerFactory=AiortcHandler.createFactory(tracks=TRACKS))
        self.assertEqual(device.loaded, False)