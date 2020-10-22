from typing import Dict, Literal, List, Optional, Any
from aiortc import RTCPeerConnection
from .sdp.remote_sdp import RemoteSdp
from .handler_interface import HandlerInterface
from ..rtp_parameters import RtpParameters


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