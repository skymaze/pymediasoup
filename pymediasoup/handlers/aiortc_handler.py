import logging
from typing import Dict, Literal, List, Optional, Any
from aiortc import RTCPeerConnection, RTCSessionDescription, RTCRtpTransceiver
from aiortc.sdp import SessionDescription
from .sdp.remote_sdp import RemoteSdp
from .sdp import common_utils
from .handler_interface import HandlerInterface
from ..rtp_parameters import RtpParameters, RtpCapabilities
from ..sctp_parameters import SctpCapabilities
from ..ortc import getSendingRtpParameters, getSendingRemoteRtpParameters


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

        sdpObject: dict = SessionDescription.parse(offer.sdp)
        nativeRtpCapabilities = common_utils.extractRtpCapabilities(sdpObject)

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