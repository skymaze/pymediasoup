import logging
from typing import Dict, Literal, List, Optional, Any
from aiortc import RTCPeerConnection, RTCSessionDescription, RTCRtpTransceiver
from .sdp.remote_sdp import RemoteSdp
from .sdp import common_utils
from .sdp.sdp_transform import parse as sdpParse
from .sdp.sdp_transform import write as sdpWrite
from .handler_interface import HandlerInterface, HandlerSendOptions, HandlerSendResult
from ..rtp_parameters import RtpParameters, RtpCapabilities, RtpEncodingParameters
from ..sctp_parameters import SctpCapabilities
from ..ortc import getSendingRtpParameters, getSendingRemoteRtpParameters, reduceCodecs
from ..scalability_modes import parse as smParse
from .sdp.unified_plan_utils import addLegacySimulcast, getRtpEncodings


SCTP_NUM_STREAMS = { 'OS': 1024, 'MIS': 1024 }

class AiortcHandler(HandlerInterface):
    # Handler direction.
    _direction: Optional[Literal['send', 'recv']]
    # Remote SDP handler.
    _remoteSdp: Optional[RemoteSdp]
    # Generic sending RTP parameters for audio and video.
    _sendingRtpParametersByKind: Optional[Dict[str, RtpParameters]]
    # Generic sending RTP parameters for audio and video suitable for the SDP
    # remote answer.
    _sendingRemoteRtpParametersByKind: Optional[Dict[str, RtpParameters]]
    # RTCPeerConnection instance.
    _pc: RTCPeerConnection
    # Map of RTCTransceivers indexed by MID.
    _mapMidTransceiver: Dict[str, RTCRtpTransceiver] = {}
    # Whether a DataChannel m=application section has been created.
    _hasDataChannelMediaSection = False
    # Sending DataChannel id value counter. Incremented for each new DataChannel.
    _nextSendSctpStreamId = 0
    # Got transport local and remote parameters.
    _transportReady = False

    def __init__(self, loop=None):
        super(AiortcHandler, self).__init__(loop=loop)

    @property
    def name(self) -> str:
        return 'aiortc'
    
    async def close(self):
        logging.debug('close()')

        if self._pc:
            await self._pc.close()

    async def getNativeRtpCapabilities(self) -> RtpCapabilities:
        logging.debug('getNativeRtpCapabilities()')

        pc = RTCPeerConnection()
        pc.addTransceiver('audio')
        pc.addTransceiver('video')

        offer: RTCSessionDescription = await pc.createOffer()
        await pc.close()

        sdpDict: dict = sdpParse(offer.sdp)
        nativeRtpCapabilities:RtpCapabilities = common_utils.extractRtpCapabilities(sdpDict)

        return nativeRtpCapabilities
    
    async def getNativeSctpCapabilities(self) -> SctpCapabilities:
        logging.debug('getNativeSctpCapabilities()')
        return SctpCapabilities.parse_obj({
            'numStreams': SCTP_NUM_STREAMS
        })
    
    def run(
        self,
        direction,
        iceParameters,
        iceCandidates,
        dtlsParameters,
        sctpParameters,
        iceServers,
        iceTransportPolicy,
        additionalSettings,
        proprietaryConstraints,
        extendedRtpCapabilities
    ):
        logging.debug('run()')
        self._direction = direction
        self._remoteSdp = RemoteSdp(
            iceParameters=iceParameters,
            iceCandidates=iceCandidates,
            dtlsParameters=dtlsParameters,
            sctpParameters=sctpParameters
        )
        self._sendingRtpParametersByKind = {
            'audio': getSendingRtpParameters('audio', extendedRtpCapabilities),
            'video': getSendingRtpParameters('video', extendedRtpCapabilities)
        }
        self._sendingRemoteRtpParametersByKind = {
            'audio': getSendingRemoteRtpParameters('audio', extendedRtpCapabilities),
            'video': getSendingRemoteRtpParameters('video', extendedRtpCapabilities)
        }
        self._pc = RTCPeerConnection()
        @self._pc.on('iceconnectionstatechange')
        def on_iceconnectionstatechange():
            if self._pc.iceConnectionState == 'checking':
                self.emit('@connectionstatechange', 'connecting')
            elif self._pc.iceConnectionState in ['connected', 'completed']:
                self.emit('@connectionstatechange', 'connected')
            elif self._pc.iceConnectionState == 'failed':
                self.emit('@connectionstatechange', 'failed')
            elif self._pc.iceConnectionState == 'disconnected':
                self.emit('@connectionstatechange', 'disconnected')
            elif self._pc.iceConnectionState == 'closed':
                self.emit('@connectionstatechange', 'closed')
        
    async def updateIceServers(self, iceServers):
        logging.debug('updateIceServers() passed')
        # TODO: aiortc can not update iceServers
    
    async def restartIce(self, iceParameters):
        logging.debug('restartIce()')
        self._remoteSdp.updateIceParameters(iceParameters)
        if not self._transportReady:
            return
        if self._direction == 'send':
            # NOTE: aiortc RTCPeerConnection createOffer do not have iceRestart
            offer = await self._pc.createOffer()
            logging.debug(f'restartIce() | calling pc.setLocalDescription() [offer:{offer}]')
            await self._pc.setLocalDescription(offer)
            answer = {
                'type': 'answer',
                'sdp': self._remoteSdp.getSdp()
            }
            logging.debug(f'restartIce() | calling pc.setRemoteDescription() [answer:{answer}]')
            await self._pc.setRemoteDescription(answer)
        else:
            offer = {
                'type': 'offer',
                'sdp': self._remoteSdp.getSdp()
            }
            logging.debug(f'restartIce() | calling pc.setRemoteDescription() [offer:{offer}]')
            await self._pc.setRemoteDescription(offer)
            answer = await self._pc.createAnswer()
            logging.debug(f'restartIce() | calling pc.setLocalDescription() [answer:{answer}]')
            await self._pc.setLocalDescription(answer)
        
    async def getTransportStats(self):
        return self._pc.getStats()

    async def send(self, options: HandlerSendOptions):
        self._assertSendDirection()
        logging.debug(f'send() [kind:{options.track.kind}, track.id:{options.track.id}]')
        if options.encodings:
            for idx in range(len(options.encodings)):
                options.encodings[idx].rid = f'r{idx}'
        sendingRtpParameters = self._sendingRtpParametersByKind[options.track.kind]
        sendingRtpParameters.codecs = reduceCodecs(sendingRtpParameters.codecs, options.codec)

        sendingRemoteRtpParameters = self._sendingRemoteRtpParametersByKind[options.track.kind]
        sendingRemoteRtpParameters.codecs = reduceCodecs(sendingRemoteRtpParameters.codecs, options.codec)

        mediaSectionIdx = self._remoteSdp.getNextMediaSectionIdx()
        transceiver = self._pc.addTransceiver(options.track, direction='sendonly')

        offer = self._pc.createOffer()
        localSdpDict = sdpParse(offer.sdp)
        if not self._transportReady:
            await self._setupTransport(localDtlsRole='server', localSdpDict=localSdpDict)
        # Special case for VP9 with SVC.
        hackVp9Svc = False
        layers=smParse(options.encodings[0].scalabilityMode)
        if len(options.encodings) == 1 and layers.spatialLayers > 1 and sendingRtpParameters.codecs[0].mimeType.lower() == 'video/vp9':
            logging.debug('send() | enabling legacy simulcast for VP9 SVC')
            hackVp9Svc = True
            localSdpDict = sdpParse
            offerMediaDict = localSdpDict['media'][mediaSectionIdx['idx']]
            addLegacySimulcast(offerMediaDict=offerMediaDict, numStreams=layers.spatialLayers)
            offer = {
                'type': 'offer',
                'sdp': sdpWrite(localSdpDict)
            }
        
        logging.debug(f'send() | calling pc.setLocalDescription() [offer:{offer}]')

        await self._pc.setLocalDescription(offer)
        # We can now get the transceiver.mid.
        localId = transceiver.mid
        # Set MID.
        sendingRtpParameters.mid = localId
        localSdpDict = sdpParse(self._pc.localDescription.sdp)
        offerMediaDict = localSdpDict['media'][mediaSectionIdx['idx']]
        # Set RTCP CNAME.
        sendingRtpParameters.rtcp.cname = common_utils.getCname(offerMediaDict)
        # Set RTP encodings by parsing the SDP offer if no encodings are given.
        if not options.encodings:
            sendingRtpParameters.encodings = getRtpEncodings(offerMediaDict)
        # Set RTP encodings by parsing the SDP offer and complete them with given
        # one if just a single encoding has been given.
        elif len(options.encodings) == 1:
            newEncodings = getRtpEncodings(offerMediaDict)
            newEncodingDict: dict = newEncodings[0].dict().update(options.encodings[0].dict())
            newEncodings[0]:RtpEncodingParameters = RtpEncodingParameters(**newEncodingDict)
            if hackVp9Svc:
                newEncodings = [newEncodings[0]]
            sendingRtpParameters.encodings = newEncodings
        # Otherwise if more than 1 encoding are given use them verbatim.
        else:
            sendingRtpParameters.encodings = options.encodings
        
        # If VP8 or H264 and there is effective simulcast, add scalabilityMode to
        # each encoding.
        if len(sendingRtpParameters.encodings) > 1 and (sendingRtpParameters.codecs[0].mimeType.lower() == 'video/vp8' or sendingRtpParameters.codecs[0].mimeType.lower() == 'video/h264'):
            for encoding in sendingRtpParameters.encodings:
                encoding.scalabilityMode = 'S1T3'
        self._remoteSdp.send(
            offerMediaDict=offerMediaDict,
            reuseMid=mediaSectionIdx.reuseMid,
            offerRtpParameters=sendingRtpParameters,
            answerRtpParameters=sendingRemoteRtpParameters,
            codecOptions=options.codecOptions,
            extmapAllowMixed=True
        )
        answer = {
            'type': 'answer',
            'sdp': self._remoteSdp.getSdp()
        }
        logging.debug(f'send() | calling pc.setRemoteDescription() [answer:{answer}]')
        await self._pc.setRemoteDescription(answer)
        # Store in the map.
        self._mapMidTransceiver[localId] = transceiver
        return HandlerSendResult(
            localId=localId,
            rtpParameters=sendingRtpParameters,
            rtpSender=transceiver.sender
        )
