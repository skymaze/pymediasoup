import sys
if sys.version_info >= (3, 8):
    from typing import Optional, List, Any, Literal
else:
    from typing import Optional, List, Any
    from typing_extensions import Literal

from pydantic import BaseModel


# Media kind ('audio' or 'video').
MediaKind = Literal['audio', 'video']

# Provides information on RTCP feedback messages for a specific codec. Those
# messages can be transport layer feedback messages or codec-specific feedback
# messages. The list of RTCP feedbacks supported by mediasoup is defined in the
# supportedRtpCapabilities.ts file.
class RtcpFeedback(BaseModel):
    type: str
    parameter: str = ''

class Codec(BaseModel):
    # The codec MIME media type/subtype (e.g. 'audio/opus', 'video/VP8').
    mimeType: str
    # Codec clock rate expressed in Hertz.
    clockRate: int
    # The number of channels supported (e.g. two for stereo). Just for audio.
	# Default 1.
    channels: Optional[int] = None
    # Transport layer and codec-specific feedback messages for this codec.
    rtcpFeedback: List[RtcpFeedback] = []

class RtpCodec(Codec):
    # Codec specific parameters. Some parameters (such as 'packetization-mode'
    # and 'profile-level-id' in H264 or 'profile-id' in VP9) are critical for
    # codec matching.
    parameters: dict = {}

class ExtendedCodec(Codec):
    kind: MediaKind
    localPayloadType: int
    localRtxPayloadType: Optional[int]
    remotePayloadType: int
    remoteRtxPayloadType: Optional[int]
    localParameters: dict = {}
    remoteParameters: dict = {}

# Provides information on the capabilities of a codec within the RTP
# capabilities. The list of media codecs supported by mediasoup and their
# settings is defined in the supportedRtpCapabilities.ts file.
#
# Exactly one RtpCodecCapability will be present for each supported combination
# of parameters that requires a distinct value of preferredPayloadType. For
# example:
#
# - Multiple H264 codecs, each with their own distinct 'packetization-mode' and
#   'profile-level-id' values.
# - Multiple VP9 codecs, each with their own distinct 'profile-id' value.
#
# RtpCodecCapability entries in the mediaCodecs array of RouterOptions do not
# require preferredPayloadType field (if unset, mediasoup will choose a random
# one). If given, make sure it's in the 96-127 range.
class RtpCodecCapability(RtpCodec):
    # Media kind.
    kind: MediaKind
    # The preferred RTP payload type.
    preferredPayloadType: Optional[int]

# Provides information on codec settings within the RTP parameters. The list
# of media codecs supported by mediasoup and their settings is defined in the
# supportedRtpCapabilities.ts file.
class RtpCodecParameters(RtpCodec):
    # The value that goes in the RTP Payload Type Field. Must be unique.
    payloadType: int

# Provides information relating to supported header extensions. The list of
# RTP header extensions supported by mediasoup is defined in the
# supportedRtpCapabilities.ts file.
#
# mediasoup does not currently support encrypted RTP header extensions. The
# direction field is just present in mediasoup RTP capabilities (retrieved via
# router.rtpCapabilities or mediasoup.getSupportedRtpCapabilities()). It's
# ignored if present in endpoints' RTP capabilities.
class RtpHeaderExtension(BaseModel):
    # Media kind. If empty string, it's valid for all kinds.
	# Default any media kind.
    kind: Optional[MediaKind] = None
    # The URI of the RTP header extension, as defined in RFC 5285.
    uri: str
    # The preferred numeric identifier that goes in the RTP packet. Must be
	# unique.
    preferredId: int
    # If True, it is preferred that the value in the header be encrypted as per
	# RFC 6904. Default False.
    preferredEncrypt: Optional[bool] = False
    # If 'sendrecv', mediasoup supports sending and receiving this RTP extension.
	# 'sendonly' means that mediasoup can send (but not receive) it. 'recvonly'
	# means that mediasoup can receive (but not send) it.
    direction: Optional[Literal['sendrecv', 'sendonly', 'recvonly', 'inactive']] = 'sendrecv'

class ExtendedHeaderExtension(BaseModel):
    kind: Optional[MediaKind] = None
    uri: str
    sendId: int
    recvId: int
    encrypt: bool
    direction: Optional[Literal['sendrecv', 'sendonly', 'recvonly', 'inactive']] = 'sendrecv'

# The RTP capabilities define what mediasoup or an endpoint can receive at
# media level.
class RtpCapabilities(BaseModel):
    # Supported media and RTX codecs.
    codecs: List[RtpCodecCapability] = []
    # Supported RTP header extensions.
    headerExtensions: List[RtpHeaderExtension] = []
    # Supported FEC mechanisms.
    fecMechanisms: List[str] = []

class RTX(BaseModel):
    ssrc: int

# Provides information relating to an encoding, which represents a media RTP
# stream and its associated RTX stream (if any).
class RtpEncodingParameters(BaseModel):
    # The media SSRC.
    ssrc: Optional[int]
    # The RID RTP extension value. Must be unique.
    rid: Optional[str]
    # Codec payload type this encoding affects. If unset, first media codec is
	# chosen.
    codecPayloadType: Optional[int]
    # RTX stream information. It must contain a numeric ssrc field indicating
	# the RTX SSRC.
    rtx: Optional[RTX]
    # It indicates whether discontinuous RTP transmission will be used. Useful
	# for audio (if the codec supports it) and for video screen sharing (when
	# static content is being transmitted, this option disables the RTP
	# inactivity checks in mediasoup). Default False.
    dtx: Optional[bool] = False
    # Number of spatial and temporal layers in the RTP stream (e.g. 'L1T3').
	# See webrtc-svc.
    scalabilityMode: Optional[str]
    # Others.
    scaleResolutionDownBy: Optional[int]
    maxBitrate: Optional[int]
    maxFramerate: Optional[int]
    adaptivePtime: Optional[bool]
    priority: Optional[Literal['very-low','low','medium','high']]
    networkPriority: Optional[Literal['very-low','low','medium','high']]

# Defines a RTP header extension within the RTP parameters. The list of RTP
# header extensions supported by mediasoup is defined in the
# supportedRtpCapabilities.ts file.
#
# mediasoup does not currently support encrypted RTP header extensions and no
# parameters are currently considered.
class RtpHeaderExtensionParameters(BaseModel):
    # The URI of the RTP header extension, as defined in RFC 5285.
    uri: str
    # The numeric identifier that goes in the RTP packet. Must be unique.
    id: int
    # If True, the value in the header is encrypted as per RFC 6904. Default False.
    encrypt: Optional[bool] = False
    # Configuration parameters for the header extension.
    parameters: Optional[dict] = {}

class RtcpParameters(BaseModel):
    # The Canonical Name (CNAME) used by RTCP (e.g. in SDES messages).
    cname: Optional[str]
    # Whether reduced size RTCP RFC 5506 is configured (if True) or compound RTCP
	# as specified in RFC 3550 (if False). Default True.
    reducedSize: Optional[bool] = True
    # Whether RTCP-mux is used. Default True.
    mux: Optional[bool]

# The RTP send parameters describe a media stream received by mediasoup from
# an endpoint through its corresponding mediasoup Producer. These parameters
# may include a mid value that the mediasoup transport will use to match
# received RTP packets based on their MID RTP extension value.
#
# mediasoup allows RTP send parameters with a single encoding and with multiple
# encodings (simulcast). In the latter case, each entry in the encodings array
# must include a ssrc field or a rid field (the RID RTP extension value). Check
# the Simulcast and SVC sections for more information.
#
# The RTP receive parameters describe a media stream as sent by mediasoup to
# an endpoint through its corresponding mediasoup Consumer. The mid value is
# unset (mediasoup does not include the MID RTP extension into RTP packets
# being sent to endpoints).
#
# There is a single entry in the encodings array (even if the corresponding
# producer uses simulcast). The consumer sends a single and continuous RTP
# stream to the endpoint and spatial/temporal layer selection is possible via
# consumer.setPreferredLayers().
#
# As an exception, previous bullet is not True when consuming a stream over a
# PipeTransport, in which all RTP streams from the associated producer are
# forwarded verbatim through the consumer.
#
# The RTP receive parameters will always have their ssrc values randomly
# generated for all of its  encodings (and optional rtx: { ssrc: XXXX } if the
# endpoint supports RTX), regardless of the original RTP send parameters in
# the associated producer. This applies even if the producer's encodings have
# rid set.
class RtpParameters(BaseModel):
    # The MID RTP extension value as defined in the BUNDLE specification.
    mid: Optional[str]
    # Media and RTX codecs in use.
    codecs: List[RtpCodecParameters] = []
    # RTP header extensions in use.
    headerExtensions: List[RtpHeaderExtensionParameters] = []
    # Transmitted RTP streams and their settings.
    encodings: List[RtpEncodingParameters] = []
    # Parameters used for RTCP.
    rtcp: Optional[RtcpParameters]
    
class ExtendedRtpCapabilities(BaseModel):
    codecs: List[ExtendedCodec] = []
    headerExtensions: List[ExtendedHeaderExtension] = []
