from typing import List
from aiortc.sdp import SessionDescription, MediaDescription

from ...transport import DtlsParameters, DtlsRole
from ...rtp_parameters import RtpCapabilities, RtpCodecCapability, RtpHeaderExtension, RtpParameters, RtcpFeedback


def extractRtpCapabilities(sdpObject: SessionDescription) -> RtpCapabilities:
    # List of codec
    codecs: List[RtpCodecCapability] = []
    # Array of RtpHeaderExtensions.
    headerExtensions: List[RtpHeaderExtension] = []
    # Whether a m=audio/video section has been already found.
    gotAudio = False
    gotVideo = False

    m: MediaDescription
    for m in sdpObject.media:
        kind = m.kind
        if kind == 'audio':
            if gotAudio:
                continue

            gotAudio = True
            break
        elif kind == 'video':
            if gotVideo:
                continue
            getVideo = True
            break
    
        # Get codecs.
        for rtpCodec in m.rtp.codecs:
            codec: RtpCodecCapability = RtpCodecCapability(
                kind=kind,
                mimeType=rtpCodec.mimeType,
                preferredPayloadType=rtpCodec.payloadType,
                clockRate=rtpCodec.clockRate,
                channels=rtpCodec.channels,
                parameters=rtpCodec.parameters,
                rtcpFeedback=rtpCodec.rtcpFeedback
            )
            codecs.append(codec)
        
        # Get RTP header extensions.
        for ext in m.rtp.headerExtensions:
            headerExtension: RtpHeaderExtension = RtpHeaderExtension(
                kind=kind,
                uri=ext.uri,
                preferredId=ext.id
            )
            headerExtensions.append(headerExtension)

    rtpCapabilities: RtpCapabilities = RtpCapabilities(
        codecs=codecs,
        headerExtensions=headerExtensions
    )

    return rtpCapabilities