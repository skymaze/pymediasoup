import unittest
from aiortc import VideoStreamTrack, AudioStreamTrack
import cv2

from pymediasoup import Device
from pymediasoup import AiortcHandler
from pymediasoup.rtp_parameters import RtpCapabilities
from pymediasoup.sctp_parameters import SctpCapabilities
from pymediasoup.transport import Transport

from .fake_parameters import generateRouterRtpCapabilities, generateTransportRemoteParameters


TRACKS = [VideoStreamTrack(), AudioStreamTrack()]

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
    
    async def test_send_transport(self):
        device = Device(handlerFactory=AiortcHandler.createFactory(tracks=TRACKS))
        await device.load(generateRouterRtpCapabilities())
        id,iceParameters,iceCandidates,dtlsParameters,sctpParameters = generateTransportRemoteParameters()
        sendTransport = device.createSendTransport(
            id=id,
            iceParameters=iceParameters,
            iceCandidates=iceCandidates,
            dtlsParameters=dtlsParameters,
            sctpParameters=sctpParameters,
            appData={ 'baz': 'BAZ' }
        )
        self.assertTrue(isinstance(sendTransport, Transport))
        self.assertEqual(sendTransport.id, id)
        self.assertFalse(sendTransport.closed)
        self.assertEqual(sendTransport.direction, 'send')
        self.assertTrue(isinstance(sendTransport.handler, AiortcHandler))
        self.assertEqual(sendTransport.connectionState, 'new')
        self.assertDictEqual(sendTransport.appData, {'baz': 'BAZ'})

    async def test_recv_transport(self):
        device = Device(handlerFactory=AiortcHandler.createFactory(tracks=TRACKS))
        await device.load(generateRouterRtpCapabilities())
        id,iceParameters,iceCandidates,dtlsParameters,sctpParameters = generateTransportRemoteParameters()
        recvTransport = device.createRecvTransport(
            id=id,
            iceParameters=iceParameters,
            iceCandidates=iceCandidates,
            dtlsParameters=dtlsParameters,
            sctpParameters=sctpParameters
        )
        self.assertTrue(isinstance(recvTransport, Transport))
        self.assertEqual(recvTransport.id, id)
        self.assertFalse(recvTransport.closed)
        self.assertEqual(recvTransport.direction, 'recv')
        self.assertTrue(isinstance(recvTransport.handler, AiortcHandler))
        self.assertEqual(recvTransport.connectionState, 'new')
        self.assertDictEqual(recvTransport.appData, {})