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
from pymediasoup.producer import ProducerOptions, Producer
from pymediasoup.errors import UnsupportedError
from pymediasoup.consumer import ConsumerOptions

from .fake_parameters import generateRouterRtpCapabilities, generateTransportRemoteParameters, generateConsumerRemoteParameters
from .fake_handler import FakeHandler

logging.basicConfig(level=logging.DEBUG)

audioTrack = AudioStreamTrack()
videoTrack = VideoStreamTrack()
TRACKS = [videoTrack, audioTrack]

class TestMethods(unittest.IsolatedAsyncioTestCase):
    # def test_create_device(self):
    #     device = Device(handlerFactory=AiortcHandler.createFactory(tracks=TRACKS))
    #     self.assertEqual(device.loaded, False)
    
    # async def test_device_load(self):
    #     device = Device(handlerFactory=AiortcHandler.createFactory(tracks=TRACKS))
    #     await device.load(generateRouterRtpCapabilities())
    #     self.assertEqual(device.handlerName, 'aiortc')
    #     self.assertTrue(device.loaded)
    
    # async def test_device_rtp_capabilities(self):
    #     device = Device(handlerFactory=AiortcHandler.createFactory(tracks=TRACKS))
    #     await device.load(generateRouterRtpCapabilities())
    #     self.assertTrue(isinstance(device.rtpCapabilities, RtpCapabilities))
    
    # async def test_device_sctp_capabilities(self):
    #     device = Device(handlerFactory=AiortcHandler.createFactory(tracks=TRACKS))
    #     await device.load(generateRouterRtpCapabilities())
    #     self.assertTrue(isinstance(device.sctpCapabilities, SctpCapabilities))
    
    # async def test_device_can_produce_audio(self):
    #     device = Device(handlerFactory=AiortcHandler.createFactory(tracks=TRACKS))
    #     await device.load(generateRouterRtpCapabilities())
    #     self.assertTrue(device.canProduce('audio'))
    
    # async def test_device_can_produce_video(self):
    #     device = Device(handlerFactory=AiortcHandler.createFactory(tracks=TRACKS))
    #     await device.load(generateRouterRtpCapabilities())
    #     self.assertTrue(device.canProduce('video'))
    
    # async def test_send_transport(self):
    #     device = Device(handlerFactory=AiortcHandler.createFactory(tracks=TRACKS))
    #     await device.load(generateRouterRtpCapabilities())
    #     id,iceParameters,iceCandidates,dtlsParameters,sctpParameters = generateTransportRemoteParameters()
    #     sendTransport = device.createSendTransport(
    #         id=id,
    #         iceParameters=iceParameters,
    #         iceCandidates=iceCandidates,
    #         dtlsParameters=dtlsParameters,
    #         sctpParameters=sctpParameters,
    #         appData={ 'baz': 'BAZ' }
    #     )
    #     self.assertTrue(isinstance(sendTransport, Transport))
    #     self.assertEqual(sendTransport.id, id)
    #     self.assertFalse(sendTransport.closed)
    #     self.assertEqual(sendTransport.direction, 'send')
    #     self.assertTrue(isinstance(sendTransport.handler, AiortcHandler))
    #     self.assertEqual(sendTransport.connectionState, 'new')
    #     self.assertDictEqual(sendTransport.appData, {'baz': 'BAZ'})

    # async def test_recv_transport(self):
    #     device = Device(handlerFactory=AiortcHandler.createFactory(tracks=TRACKS))
    #     await device.load(generateRouterRtpCapabilities())
    #     id,iceParameters,iceCandidates,dtlsParameters,sctpParameters = generateTransportRemoteParameters()
    #     recvTransport = device.createRecvTransport(
    #         id=id,
    #         iceParameters=iceParameters,
    #         iceCandidates=iceCandidates,
    #         dtlsParameters=dtlsParameters,
    #         sctpParameters=sctpParameters
    #     )
    #     self.assertTrue(isinstance(recvTransport, Transport))
    #     self.assertEqual(recvTransport.id, id)
    #     self.assertFalse(recvTransport.closed)
    #     self.assertEqual(recvTransport.direction, 'recv')
    #     self.assertTrue(isinstance(recvTransport.handler, AiortcHandler))
    #     self.assertEqual(recvTransport.connectionState, 'new')
    #     self.assertDictEqual(recvTransport.appData, {})

    #     audioProducerOptions = ProducerOptions(
    #         track=audioTrack,
    #         stopTracks=False,
    #         appData={'foo': 'FOO'}
    #     )

    #     # transport.produce() in a receiving Transport rejects with UnsupportedError
    #     with self.assertRaises(UnsupportedError):
    #         await recvTransport.produce(audioProducerOptions)
    
    # async def test_produce(self):

    #     audioProducerId = None
    #     videoProducerId = None
    #     connectEventNumTimesCalled = 0
    #     produceEventNumTimesCalled = 0

    #     device = Device(handlerFactory=FakeHandler.createFactory(tracks=TRACKS))
    #     await device.load(generateRouterRtpCapabilities())
    #     id,iceParameters,iceCandidates,dtlsParameters,sctpParameters = generateTransportRemoteParameters()
    #     sendTransport = device.createSendTransport(
    #         id=id,
    #         iceParameters=iceParameters,
    #         iceCandidates=iceCandidates,
    #         dtlsParameters=dtlsParameters,
    #         sctpParameters=sctpParameters
    #     )

    #     @sendTransport.on('connect')
    #     async def on_connect(dtlsParameters):
    #         nonlocal connectEventNumTimesCalled
    #         connectEventNumTimesCalled += 1

    #         self.assertTrue(isinstance(dtlsParameters, DtlsParameters))
        
    #     @sendTransport.on('produce')
    #     async def on_produce(args: dict) -> str:
    #         kind: str = args['kind']
    #         rtpParameters: RtpParameters = args['rtpParameters']
    #         appData: dict = args['appData']
    #         nonlocal produceEventNumTimesCalled
    #         produceEventNumTimesCalled += 1

    #         self.assertTrue(isinstance(kind, str))
    #         self.assertTrue(isinstance(rtpParameters, RtpParameters))
            
    #         id: str = ''
    #         if kind == 'audio':
    #             self.assertDictEqual(appData, {'foo': 'FOO'})
    #             id , _, _, _, _ = generateTransportRemoteParameters()
    #             nonlocal audioProducerId
    #             audioProducerId = id
    #         elif kind == 'video':
    #             self.assertDictEqual(appData, {})
    #             id , _, _, _, _ = generateTransportRemoteParameters()
    #             nonlocal videoProducerId
    #             videoProducerId = id
            
    #         return id

    #     audioProducerOptions = ProducerOptions(
    #         track=audioTrack,
    #         stopTracks=False,
    #         appData={'foo': 'FOO'}
    #     )

    #     # NOTE: 'AudioStreamTrack' object has no attribute 'enabled'
    #     # audioTrack.enabled = False

    #     audioProducer = await sendTransport.produce(audioProducerOptions)

    #     self.assertEqual(connectEventNumTimesCalled, 1)
    #     self.assertEqual(produceEventNumTimesCalled, 1)
    #     self.assertTrue(isinstance(audioProducer, Producer))
    #     self.assertEqual(audioProducer.id, audioProducerId)
    #     self.assertFalse(audioProducer.closed)
    #     self.assertEqual(audioProducer.kind, 'audio')
    #     self.assertEqual(audioProducer.track, audioTrack)
    #     self.assertTrue(isinstance(audioProducer.rtpParameters, RtpParameters))
    #     self.assertEqual(len(audioProducer.rtpParameters.codecs), 1)

    #     codecs = audioProducer.rtpParameters.codecs
    #     self.assertDictEqual(codecs[0].dict(), {
    #         'mimeType'     : 'audio/opus',
    #         'payloadType'  : 111,
    #         'clockRate'    : 48000,
    #         'channels'     : 2,
    #         'rtcpFeedback' :
    #         [
    #             { 'type': 'transport-cc', 'parameter': '' }
    #         ],
    #         'parameters' :
    #         {
    #             'minptime'     : 10,
    #             'useinbandfec' : 1
    #         }
    #     })

    #     headerExtensions = audioProducer.rtpParameters.headerExtensions
    #     self.assertDictEqual(headerExtensions[0].dict(), {
    #         'uri'        : 'urn:ietf:params:rtp-hdrext:sdes:mid',
    #         'id'         : 1,
    #         'encrypt'    : False,
    #         'parameters' : {}
    #     })
    #     self.assertDictEqual(headerExtensions[1].dict(), {
    #         'uri'        : 'urn:ietf:params:rtp-hdrext:ssrc-audio-level',
    #         'id'         : 10,
    #         'encrypt'    : False,
    #         'parameters' : {}
    #     })

    #     encodings = audioProducer.rtpParameters.encodings

    #     self.assertEqual(len(encodings), 1)

    #     # NOTE: 'AudioStreamTrack' object has no attribute 'enabled', So paused == False
    #     self.assertFalse(audioProducer.paused)
    #     self.assertEqual(audioProducer.maxSpatialLayer, None)
    #     self.assertDictEqual(audioProducer.appData, {'foo': 'FOO'})

    #     # Reset the audio paused state.
    #     audioProducer.resume()

    #     videoProducerOptions: ProducerOptions = ProducerOptions(
    #         track=videoTrack,
    #         encodings=[{'maxBitrate': 100000}, {'maxBitrate': 500000}],
    #         disableTrackOnPause=False,
    #         zeroRtpOnPause=True
    #     )
    #     videoProducer: Producer = await sendTransport.produce(videoProducerOptions)

    #     self.assertEqual(connectEventNumTimesCalled, 1)
    #     self.assertEqual(produceEventNumTimesCalled, 2)
    #     self.assertEqual(videoProducer.id, videoProducerId)
    #     self.assertFalse(videoProducer.closed)
    #     self.assertEqual(videoProducer.kind, 'video')
    #     self.assertEqual(videoProducer.track, videoTrack)
    #     self.assertTrue(isinstance(videoProducer.rtpParameters.mid, str))
    #     self.assertEqual(len(videoProducer.rtpParameters.codecs), 2)

    #     codecs = videoProducer.rtpParameters.codecs

    #     self.assertDictEqual(codecs[0].dict(exclude_none=True), {
    #         'mimeType'     : 'video/VP8',
    #         'payloadType'  : 96,
    #         'clockRate'    : 90000,
    #         'rtcpFeedback' :
    #         [
    #             { 'type': 'goog-remb', 'parameter': '' },
    #             { 'type': 'transport-cc', 'parameter': '' },
    #             { 'type': 'ccm', 'parameter': 'fir' },
    #             { 'type': 'nack', 'parameter': '' },
    #             { 'type': 'nack', 'parameter': 'pli' }
    #         ],
    #         'parameters' :
    #         {
    #             'baz' : '1234abcd'
    #         }
    #     })

    #     self.assertDictEqual(codecs[1].dict(exclude_none=True), {
    #         'mimeType'     : 'video/rtx',
    #         'payloadType'  : 97,
    #         'clockRate'    : 90000,
    #         'rtcpFeedback' : [],
    #         'parameters'   :
    #         {
    #             'apt' : 96
    #         }
    #     })

    #     headerExtensions = videoProducer.rtpParameters.dict()['headerExtensions']

    #     self.assertDictEqual(headerExtensions[0], {
    #         'uri'        : 'urn:ietf:params:rtp-hdrext:sdes:mid',
    #         'id'         : 1,
    #         'encrypt'    : False,
    #         'parameters' : {}
    #     })

    #     self.assertDictEqual(headerExtensions[1], {
    #         'uri'        : 'http://www.webrtc.org/experiments/rtp-hdrext/abs-send-time',
    #         'id'         : 3,
    #         'encrypt'    : False,
    #         'parameters' : {}
    #     })

    #     self.assertDictEqual(headerExtensions[2], {
    #         'uri'        : 'http://www.ietf.org/id/draft-holmer-rmcat-transport-wide-cc-extensions-01',
    #         'id'         : 5,
    #         'encrypt'    : False,
    #         'parameters' : {}
    #     })

    #     self.assertDictEqual(headerExtensions[3], {
    #         'uri'        : 'urn:3gpp:video-orientation',
    #         'id'         : 4,
    #         'encrypt'    : False,
    #         'parameters' : {}
    #     })

    #     self.assertDictEqual(headerExtensions[4], {
    #         'uri'        : 'urn:ietf:params:rtp-hdrext:toffset',
    #         'id'         : 2,
    #         'encrypt'    : False,
    #         'parameters' : {}
    #     })

    #     encodings = videoProducer.rtpParameters.encodings

    #     self.assertEqual(len(encodings), 2)
        
    #     self.assertFalse(videoProducer.paused)

    #     self.assertEqual(videoProducer.maxSpatialLayer, None)

    #     self.assertDictEqual(videoProducer.appData, {})

    #     sendTransport.remove_all_listeners('connect')
    #     sendTransport.remove_all_listeners('produce')
    
    async def test_consume(self):
        device = Device(handlerFactory=FakeHandler.createFactory(tracks=TRACKS))
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

        audioConsumerRemoteParameters = generateConsumerRemoteParameters(codecMimeType='audio/opus')
        videoConsumerRemoteParameters = generateConsumerRemoteParameters(codecMimeType='video/VP8')
    
        connectEventNumTimesCalled = 0

        @recvTransport.on('connect')
        async def on_connect(dtlsParameters):
            nonlocal connectEventNumTimesCalled
            connectEventNumTimesCalled += 1

        audioConsumer = await recvTransport.consume(ConsumerOptions(
            id=audioConsumerRemoteParameters['id'],
            producerId=audioConsumerRemoteParameters['producerId'],
            kind=audioConsumerRemoteParameters['kind'],
            rtpParameters=audioConsumerRemoteParameters['rtpParameters'],
            appData={'bar': 'BAR'}
        ))

        self.assertEqual(connectEventNumTimesCalled, 1)
        self.assertEqual(audioConsumer.id, audioConsumerRemoteParameters['id'])
        self.assertEqual(audioConsumer.producerId, audioConsumerRemoteParameters['producerId'])
        self.assertFalse(audioConsumer.closed)
        self.assertEqual(audioConsumer.kind, 'audio')
        self.assertEqual(audioConsumer.rtpParameters.mid, None)
        self.assertEqual(len(audioConsumer.rtpParameters.codecs), 1)

        codecs = audioConsumer.rtpParameters.codecs

        self.assertDictEqual(codecs[0].dict(), {
            'mimeType'     : 'audio/opus',
            'payloadType'  : 100,
            'clockRate'    : 48000,
            'channels'     : 2,
            'rtcpFeedback' :
            [
                { 'type': 'transport-cc', 'parameter': '' }
            ],
            'parameters' :
            {
                'useinbandfec' : 1,
                'foo'          : 'bar'
            }
        })

        headerExtensions = audioConsumer.rtpParameters.headerExtensions

        self.assertDictEqual(headerExtensions[0].dict(), {
            'uri'        : 'urn:ietf:params:rtp-hdrext:sdes:mid',
            'id'         : 1,
            'encrypt'    : False,
            'parameters' : {}
        })

        self.assertDictEqual(headerExtensions[1].dict(), {
            'uri'        : 'http://www.ietf.org/id/draft-holmer-rmcat-transport-wide-cc-extensions-01',
            'id'         : 5,
            'encrypt'    : False,
            'parameters' : {}
        })

        self.assertDictEqual(headerExtensions[2].dict(), {
            'uri'        : 'urn:ietf:params:rtp-hdrext:ssrc-audio-level',
            'id'         : 10,
            'encrypt'    : False,
            'parameters' : {}
        })

        encodings = audioConsumer.rtpParameters.encodings

        self.assertEqual(len(encodings), 1)

        self.assertFalse(audioConsumer.paused)

        self.assertDictEqual(audioConsumer.appData, {'bar': 'BAR'})

