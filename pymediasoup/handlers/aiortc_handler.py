import logging
from typing import Dict, Literal, List, Optional, Any
from aiortc import RTCPeerConnection, RTCSessionDescription
from aiortc.sdp import SessionDescription
from .sdp.remote_sdp import RemoteSdp
from .sdp import common_utils
from .handler_interface import HandlerInterface
from ..rtp_parameters import RtpParameters


SCTP_NUM_STREAMS = { 'OS': 1024, 'MIS': 1024 }

class AiortcHandler(HandlerInterface):
    # Handler direction.
    _direction: Optional[Literal['send' | 'recv']]
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
    
    async def getNativeSctpCapabilities(self) -> dict:
        logging.debug(getNativeSctpCapabilities())
        return {
            'numStreams': SCTP_NUM_STREAMS
        }
