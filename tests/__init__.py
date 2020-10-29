import unittest
from aiortc import VideoStreamTrack
import cv2

from pymediasoup import Device
from pymediasoup import AiortcHandler
from pymediasoup.rtp_parameters import RtpCapabilities
from pymediasoup.sctp_parameters import SctpCapabilities

from .fake_parameters import generateRouterRtpCapabilities


TRACKS = [VideoStreamTrack()]

class TestMethods(unittest.IsolatedAsyncioTestCase):
    def test_create_device(self):
        device = Device(handlerFactory=AiortcHandler.createFactory(tracks=TRACKS))
        self.assertEqual(device.loaded, False)
    
    async def test_device_load(self):
        device = Device(handlerFactory=AiortcHandler.createFactory(tracks=TRACKS))
        await device.load(generateRouterRtpCapabilities())
        self.assertEqual(device.handlerName, 'aiortc')
        self.assertTrue(device.loaded)
    
    async def test_device_rtp_capabilities(self):
        device = Device(handlerFactory=AiortcHandler.createFactory(tracks=TRACKS))
        await device.load(generateRouterRtpCapabilities())
        self.assertTrue(isinstance(device.rtpCapabilities, RtpCapabilities))
    
    async def test_device_sctp_capabilities(self):
        device = Device(handlerFactory=AiortcHandler.createFactory(tracks=TRACKS))
        await device.load(generateRouterRtpCapabilities())
        self.assertTrue(isinstance(device.sctpCapabilities, SctpCapabilities))
    
    async def test_device_can_produce_audio(self):
        device = Device(handlerFactory=AiortcHandler.createFactory(tracks=TRACKS))
        await device.load(generateRouterRtpCapabilities())
        self.assertTrue(device.canProduce('audio'))
    
    async def test_device_can_produce_video(self):
        device = Device(handlerFactory=AiortcHandler.createFactory(tracks=TRACKS))
        await device.load(generateRouterRtpCapabilities())
        self.assertTrue(device.canProduce('video'))