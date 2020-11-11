import sys
if sys.version_info >= (3, 8):
    from typing import Optional, Literal
else:
    from typing import Optional
    from typing_extensions import Literal

from pydantic import BaseModel


class NumSctpStreams(BaseModel):
    # Initially requested number of outgoing SCTP streams.
    OS: int
    # Maximum number of incoming SCTP streams.
    MIS: int

class SctpCapabilities(BaseModel):
    numStreams: NumSctpStreams

class SctpParameters(BaseModel):
    # Must always equal 5000.
    port: int
    # Initially requested number of outgoing SCTP streams.
    OS: int
    # Maximum number of incoming SCTP streams.
    MIS: int
    # Maximum allowed size for SCTP messages.
    maxMessageSize: int

# SCTP stream parameters describe the reliability of a certain SCTP stream.
# If ordered is True then maxPacketLifeTime and maxRetransmits must be
# False.
# If ordered if False, only one of maxPacketLifeTime or maxRetransmits
# can be True.
class SctpStreamParameters(BaseModel):
    # SCTP stream id.
    streamId: Optional[int]
    # Whether data messages must be received in order. if True the messages will
	# be sent reliably. Default True.
    ordered: Optional[bool] = True
    # When ordered is False indicates the time (in milliseconds) after which a
	# SCTP packet will stop being retransmitted.
    maxPacketLifeTime: Optional[int]
    # When ordered is False indicates the maximum number of times a packet will
	# be retransmitted.
    maxRetransmits: Optional[int]
    # DataChannel priority.
    priority: Optional[Literal['very-low','low','medium','high']]
    # A label which can be used to distinguish this DataChannel from others.
    label: Optional[str]
    # Name of the sub-protocol used by this DataChannel.
    protocol: Optional[str]