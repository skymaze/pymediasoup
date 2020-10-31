import logging
import unittest
from aiortc import VideoStreamTrack
from aiortc.mediastreams import AudioStreamTrack
import cv2

from pymediasoup import Device
from pymediasoup import AiortcHandler
from pymediasoup.rtp_parameters import RtpCapabilities, RtpParameters
from pymediasoup.sctp_parameters import SctpCapabilities
from pymediasoup.transport import Transport
from pymediasoup.models.transport import DtlsParameters
from pymediasoup.producer import ProducerOptions

from .fake_parameters import generateRouterRtpCapabilities, generateTransportRemoteParameters

logging.basicConfig(level=logging.DEBUG)

audioTrack = AudioStreamTrack()
videoTrack = VideoStreamTrack()
TRACKS = [videoTrack, audioTrack]

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
    
    async def test_produce(self):

        audioProducerId = None
        videoProducerId = None
        connectEventNumTimesCalled = 0
        produceEventNumTimesCalled = 0

        device = Device(handlerFactory=AiortcHandler.createFactory(tracks=[]))
        await device.load(generateRouterRtpCapabilities())
        id,iceParameters,iceCandidates,dtlsParameters,sctpParameters = generateTransportRemoteParameters()
        sendTransport = device.createSendTransport(
            id=id,
            iceParameters=iceParameters,
            iceCandidates=iceCandidates,
            dtlsParameters=dtlsParameters,
            sctpParameters=sctpParameters
        )

        @sendTransport.on('connect')
        async def on_connect(dtlsParameters):
            nonlocal connectEventNumTimesCalled
            connectEventNumTimesCalled += 1

            self.assertTrue(isinstance(dtlsParameters, DtlsParameters))
        
        @sendTransport.on('produce')
        async def on_produce(args: dict) -> str:
            kind: str = args['kind']
            rtpParameters: RtpParameters = args['rtpParameters']
            appData: dict = args['appData']
            nonlocal produceEventNumTimesCalled
            produceEventNumTimesCalled += 1

            self.assertTrue(isinstance(kind, str))
            self.assertTrue(isinstance(rtpParameters, RtpParameters))
            
            id: str = ''
            if kind == 'audio':
                self.assertDictEqual(appData, {'foo': 'FOO'})
                id , _, _, _, _ = generateTransportRemoteParameters()
                audioProducerId = id
            elif kind == 'video':
                self.assertDictEqual(appData, {})
                id , _, _, _, _ = generateTransportRemoteParameters()
                videoProducerId = id
            
            return id

        producerOptions = ProducerOptions(
            track=AudioStreamTrack(),
            stopTracks=False,
            appData={'foo': 'FOO'}
        )

        audioProducer = await sendTransport.produce(producerOptions)

        self.assertEqual(connectEventNumTimesCalled, 1)
        self.assertEqual(produceEventNumTimesCalled, 1)