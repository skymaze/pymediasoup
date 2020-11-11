import sys
if sys.version_info >= (3, 8):
    from typing import Optional, Literal, List, Any, Callable, Dict
else:
    from typing import Optional, List, Any, Callable, Dict
    from typing_extensions import Literal

from enum import IntEnum
from aiortc import RTCIceServer
from pydantic import BaseModel
from ..ortc import ExtendedRtpCapabilities
from ..sctp_parameters import SctpParameters, SctpStreamParameters


class IceParameters(BaseModel):
    # ICE username fragment.
    usernameFragment: str
    # ICE password.
    password: str
    # ICE Lite.
    iceLite: Optional[bool]

class IceCandidate(BaseModel):
    # Unique identifier that allows ICE to correlate candidates that appear on
    # multiple transports.
    foundation: str
    # The assigned priority of the candidate.
    priority: int
    # The IP address of the candidate.
    ip: str
    # The protocol of the candidate.
    protocol: Literal['udp', 'tcp']
    # The port for the candidate.
    port: int
    # The type of candidate..
    type: Literal['host', 'srflx', 'prflx', 'relay']
    # The type of TCP candidate.
    tcpType: Optional[Literal['active', 'passive', 'so']]

# The hash function algorithm (as defined in the "Hash function Textual Names"
# registry initially specified in RFC 4572 Section 8) and its corresponding
# certificate fingerprint value (in lowercase hex string as expressed utilizing
# the syntax of "fingerprint" in RFC 4572 Section 5).
class DtlsFingerprint(BaseModel):
    algorithm: str
    value: str

DtlsRole = Literal['auto', 'client', 'server']

class DtlsParameters(BaseModel):
    # DTLS role. Default 'auto'.
    role: DtlsRole = 'auto'
    fingerprints: List[DtlsFingerprint]

ConnectionState = Literal['new', 'connecting', 'connected', 'failed', 'disconnected', 'closed']

class IpVersion(IntEnum):
    ipv4 = 4
    ipv6 = 6

class PlainRtpParameters(BaseModel):
    ip: str
    ipVersion: IpVersion
    port: int

class TransportOptions(BaseModel):
    id: str
    iceParameters: IceParameters
    iceCandidates: List[IceCandidate]
    dtlsParameters: DtlsParameters
    sctpParameters: Optional[SctpParameters]
    iceServers: Optional[List[RTCIceServer]]
    iceTransportPolicy: Optional[Literal['all', 'relay']]
    additionalSettings: Optional[dict] = None
    proprietaryConstraints: Any = None
    appData: Optional[dict] = {}

    class Config:
        arbitrary_types_allowed=True

class InternalTransportOptions(TransportOptions):
    direction: Literal['send', 'recv']
    handlerFactory: Callable
    extendedRtpCapabilities: Optional[ExtendedRtpCapabilities] = None
    canProduceByKind: Dict[str, bool]
