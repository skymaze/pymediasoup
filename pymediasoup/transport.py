from typing import Optional, Literal, List
from pydantic import BaseModel


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
    tcpType: Literal['active', 'passive', 'so']

# The hash function algorithm (as defined in the "Hash function Textual Names"
# registry initially specified in RFC 4572 Section 8) and its corresponding
# certificate fingerprint value (in lowercase hex string as expressed utilizing
# the syntax of "fingerprint" in RFC 4572 Section 5).
class DtlsFingerprint(BaseModel):
    algorithm: str
    value: str

class DtlsParameters(BaseModel):
    # DTLS role. Default 'auto'.
    role: Literal['auto', 'client', 'server'] = 'auto'
    fingerprints: List[DtlsFingerprint]

