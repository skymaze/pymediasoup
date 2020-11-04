import logging
from typing import List, Optional
from .rtp_parameters import RtpCodec, RtcpFeedback, RtpHeaderExtension, RtpCapabilities, ExtendedRtpCapabilities, ExtendedCodec, ExtendedHeaderExtension, RtpCodecCapability, RtpHeaderExtension, MediaKind, RtpParameters, RtpCodecParameters, RtpHeaderExtensionParameters, RtpEncodingParameters, RtcpParameters
import h264_profile_level_id as h264


RTP_PROBATOR_MID = 'probator'
RTP_PROBATOR_SSRC = 1234
RTP_PROBATOR_CODEC_PAYLOAD_TYPE = 127

def matchCodecs(aCodec: RtpCodec, bCodec: RtpCodec, strict: bool = False, modify: bool = False) -> bool:
    aMimeType = aCodec.mimeType.lower()
    bMimeType = bCodec.mimeType.lower()
    if aMimeType != bMimeType:
        return False
    if aCodec.clockRate != bCodec.clockRate:
        return False
    if aCodec.channels != bCodec.channels:
        return False

    if aMimeType == 'video/h264':
        aPacketizationMode = aCodec.parameters.get('packetization-mode', 0)
        bPacketizationMode = bCodec.parameters.get('packetization-mode', 0)
        if aPacketizationMode != bPacketizationMode:
            return False
        if strict:
            if not h264.isSameProfile(aCodec.parameters, bCodec.parameters):
                return False

            if modify:
                try:
                    selectedProfileLevelId = h264.generateProfileLevelIdForAnswer(
                        aCodec.parameters, bCodec.parameters)
                except TypeError:
                    return False
                else:
                    if selectedProfileLevelId:
                        aCodec.parameters['profile-level-id'] = selectedProfileLevelId
                    else:
                        del aCodec.parameters['profile-level-id']

    elif aMimeType == 'video/vp9':
        if strict:
            aProfileId = aCodec.parameters.get('profile-id', 0)
            bProfileId = bCodec.parameters.get('profile-id', 0)
            if aProfileId != bProfileId:
                return False

    else:
        pass

    return True


def isRtxCodec(codec: RtpCodec) -> bool:
    if not codec:
        return False
    return codec.mimeType.endswith('/rtx')


def reduceRtcpFeedback(codecA: RtpCodec, codecB: RtpCodec) -> List[RtcpFeedback]:
    reducedRtcpFeedback: List[RtcpFeedback] = []
    for aFb in codecA.rtcpFeedback:
        matchingBFbs = [bFb for bFb in codecB.rtcpFeedback if bFb.type == aFb.type and (
            bFb.parameter == aFb.parameter or (not bFb.parameter and not aFb.parameter))]
        if matchingBFbs:
            reducedRtcpFeedback.append(matchingBFbs[0])

    return reducedRtcpFeedback


def matchHeaderExtensions(aExt: RtpHeaderExtension, bExt: RtpHeaderExtension) -> bool:
    if aExt.kind != bExt.kind:
        return False
    if aExt.uri != bExt.uri:
        return False
    return True

# Generate extended RTP capabilities for sending and receiving.


def getExtendedRtpCapabilities(localCaps: RtpCapabilities, remoteCaps: RtpCapabilities) -> ExtendedRtpCapabilities:
    extendedRtpCapabilities: ExtendedRtpCapabilities = ExtendedRtpCapabilities()
    # Match media codecs and keep the order preferred by remoteCaps.
    for remoteCodec in remoteCaps.codecs:
        if isRtxCodec(remoteCodec):
            continue

        matchingLocalCodecs = [localCodec for localCodec in localCaps.codecs if matchCodecs(
            localCodec, remoteCodec, strict=True, modify=True)]

        if not matchingLocalCodecs:
            continue

        matchingLocalCodec = matchingLocalCodecs[0]

        extendedCodec: ExtendedCodec = ExtendedCodec(
            mimeType=matchingLocalCodec.mimeType,
            kind=matchingLocalCodec.kind,
            clockRate=matchingLocalCodec.clockRate,
            channels=matchingLocalCodec.channels,
            localPayloadType=matchingLocalCodec.preferredPayloadType,
            remotePayloadType=remoteCodec.preferredPayloadType,
            localParameters=matchingLocalCodec.parameters,
            remoteParameters=remoteCodec.parameters,
            rtcpFeedback=reduceRtcpFeedback(matchingLocalCodec, remoteCodec)
        )
        extendedRtpCapabilities.codecs.append(extendedCodec)

    # Match RTX codecs.
    for extendedCodec in extendedRtpCapabilities.codecs:
        matchingLocalRtxCodecs = [localCodec for localCodec in localCaps.codecs if isRtxCodec(
            localCodec) and localCodec.parameters.get('apt') == extendedCodec.localPayloadType]
        matchingRemoteRtxCodecs = [remoteCodec for remoteCodec in remoteCaps.codecs if isRtxCodec(
            remoteCodec) and remoteCodec.parameters.get('apt') == extendedCodec.remotePayloadType]
        if matchingLocalRtxCodecs and matchingRemoteRtxCodecs:
            extendedCodec.localRtxPayloadType = matchingLocalRtxCodecs[0].preferredPayloadType
            extendedCodec.remoteRtxPayloadType = matchingRemoteRtxCodecs[0].preferredPayloadType

    # Match header extensions.
    for remoteExt in remoteCaps.headerExtensions:
        matchingLocalExts = [
            localExt for localExt in localCaps.headerExtensions if matchHeaderExtensions(localExt, remoteExt)]

        if not matchingLocalExts:
            continue

        matchingLocalExt = matchingLocalExts[0]

        extendedExt: ExtendedHeaderExtension = ExtendedHeaderExtension(
            kind=remoteExt.kind,
            uri=remoteExt.uri,
            sendId=matchingLocalExt.preferredId,
            recvId=remoteExt.preferredId,
            encrypt=matchingLocalExt.preferredEncrypt,
            direction='sendrecv'
        )

        if remoteExt.direction == 'sendrecv':
            extendedExt.direction = 'sendrecv'
        elif remoteExt.direction == 'recvonly':
            extendedExt.direction = 'sendonly'
        elif remoteExt.direction == 'sendonly':
            extendedExt.direction = 'recvonly'
        elif remoteExt.direction == 'inactive':
            extendedExt.direction = 'inactive'
        else:
            pass

        extendedRtpCapabilities.headerExtensions.append(extendedExt)

    return extendedRtpCapabilities

# Generate RTP capabilities for receiving media based on the given extended
# RTP capabilities.


def getRecvRtpCapabilities(extendedRtpCapabilities: ExtendedRtpCapabilities) -> RtpCapabilities:
    rtpCapabilities: RtpCapabilities = RtpCapabilities()
    for extendedCodec in extendedRtpCapabilities.codecs:
        codec: RtpCodecCapability = RtpCodecCapability(**extendedCodec.dict())
        rtpCapabilities.codecs.append(codec)

        # Add RTX codec.
        if not extendedCodec.remoteRtxPayloadType:
            continue

        rtxCodec: RtpCodecCapability = RtpCodecCapability(
            mimeType=f'{extendedCodec.kind}/rtx',
            kind=extendedCodec.kind,
            preferredPayloadType=extendedCodec.remoteRtxPayloadType,
            clockRate=extendedCodec.clockRate,
            parameters={
                'apt': extendedCodec.remotePayloadType
            },
            rtcpFeedback=[]
        )

        rtpCapabilities.codecs.append(rtxCodec)

        # TODO: In the future, we need to add FEC, CN, etc, codecs.

    for extendedExtension in extendedRtpCapabilities.headerExtensions:
        # Ignore RTP extensions not valid for receiving.
        if extendedExtension.direction != 'sendrecv' and extendedExtension.direction != 'recvonly':
            continue

        ext: RtpHeaderExtension = RtpHeaderExtension(
            kind=extendedExtension.kind,
            uri=extendedExtension.uri,
            preferredId=extendedExtension.recvId,
            preferredEncrypt=extendedExtension.encrypt,
            direction=extendedExtension.direction
        )

        rtpCapabilities.headerExtensions.append(ext)

    return rtpCapabilities

# Generate RTP parameters of the given kind for sending media.
# NOTE: mid, encodings and rtcp fields are left empty.


def getSendingRtpParameters(kind: MediaKind, extendedRtpCapabilities: ExtendedRtpCapabilities) -> RtpParameters:
    rtpParameters: RtpParameters = RtpParameters()
    for extendedCodec in extendedRtpCapabilities.codecs:
        if extendedCodec.kind != kind:
            continue

        codec: RtpCodecParameters = RtpCodecParameters(
            mimeType=extendedCodec.mimeType,
            payloadType=extendedCodec.localPayloadType,
            clockRate=extendedCodec.clockRate,
            channels=extendedCodec.channels,
            parameters=extendedCodec.localParameters,
            rtcpFeedback=extendedCodec.rtcpFeedback
        )

        rtpParameters.codecs.append(codec)

        # Add RTX codec.
        if extendedCodec.localRtxPayloadType:
            rtxCodec: RtpCodecParameters = RtpCodecParameters(
                mimeType=f'{extendedCodec.kind}/rtx',
                payloadType=extendedCodec.localRtxPayloadType,
                clockRate=extendedCodec.clockRate,
                parameters={'apt': extendedCodec.localPayloadType},
                rtcpFeedback=[]
            )

            rtpParameters.codecs.append(rtxCodec)

    for extendedExtension in extendedRtpCapabilities.headerExtensions:
        if extendedExtension.kind != kind or (extendedExtension.direction not in ['sendrecv', 'sendonly']):
            continue

        ext: RtpHeaderExtensionParameters = RtpHeaderExtensionParameters(
            uri=extendedExtension.uri,
            id=extendedExtension.sendId,
            encrypt=extendedExtension.encrypt,
            parameters={}
        )

        rtpParameters.headerExtensions.append(ext)
    
    return rtpParameters

# Generate RTP parameters of the given kind suitable for the remote SDP answer.
def getSendingRemoteRtpParameters(kind: MediaKind, extendedRtpCapabilities: ExtendedRtpCapabilities) -> RtpParameters:
    rtpParameters: RtpParameters = RtpParameters()
    for extendedCodec in extendedRtpCapabilities.codecs:
        if extendedCodec.kind != kind:
            continue

        codec = RtpCodecParameters(
            mimeType=extendedCodec.mimeType,
            payloadType=extendedCodec.localPayloadType,
            clockRate=extendedCodec.clockRate,
            channels=extendedCodec.channels,
            parameters=extendedCodec.remoteParameters,
            rtcpFeedback=extendedCodec.rtcpFeedback
        )

        rtpParameters.codecs.append(codec)

        # Add RTX codec.
        if extendedCodec.localRtxPayloadType:
            rtxCodec: RtpCodecParameters = RtpCodecParameters(
                mimeType=f'{extendedCodec.kind}/rtx',
                payloadType=extendedCodec.localRtxPayloadType,
                clockRate=extendedCodec.clockRate,
                parameters={'apt': extendedCodec.localPayloadType},
                rtcpFeedback=[]
            )

            rtpParameters.codecs.append(rtxCodec)
    
    for extendedExtension in extendedRtpCapabilities.headerExtensions:
        if extendedExtension.kind != kind or (extendedExtension.direction not in ['sendrecv', 'sendonly']):
            continue

        ext: RtpHeaderExtensionParameters = RtpHeaderExtensionParameters(
            uri=extendedExtension.uri,
            id=extendedExtension.sendId,
            encrypt=extendedExtension.encrypt,
            parameters={}
        )

        rtpParameters.headerExtensions.append(ext)
    
    # Reduce codecs' RTCP feedback. Use Transport-CC if available, REMB otherwise.
    if [ext for ext in rtpParameters.headerExtensions if ext.uri == 'http://www.ietf.org/id/draft-holmer-rmcat-transport-wide-cc-extensions-01']:
        for codec in rtpParameters.codecs:
            codec.rtcpFeedback = [fb for fb in codec.rtcpFeedback if fb.type != 'goog-remb']
        
    elif [ext for ext in rtpParameters.headerExtensions if ext.uri == 'http://www.webrtc.org/experiments/rtp-hdrext/abs-send-time']:
        for codec in rtpParameters.codecs:
            codec.rtcpFeedback = [fb for fb in codec.rtcpFeedback if fb.type != 'transport-cc']
    
    else:
        for codec in rtpParameters.codecs:
            codec.rtcpFeedback = [fb for fb in codec.rtcpFeedback if fb.type not in ['transport-cc', 'goog-remb']]
        
    return rtpParameters

# Reduce given codecs by returning an array of codecs "compatible" with the
# given capability codec. If no capability codec is given, take the first
# one(s).
#
# Given codecs must be generated by ortc.getSendingRtpParameters() or
# ortc.getSendingRemoteRtpParameters().
#
# The returned array of codecs also include a RTX codec if available.
def reduceCodecs(codecs: List[RtpCodecParameters], capCodec: Optional[RtpCodecCapability]=None):
    filteredCodecs: List[RtpCodecParameters] = []

    # If no capability codec is given, take the first one (and RTX).
    if not capCodec:
        filteredCodecs.append(codecs[0])
        if len(codecs) >=2:
            if isRtxCodec(codecs[1]):
                filteredCodecs.append(codecs[1])

    # Otherwise look for a compatible set of codecs.
    else:
        for idx in range(len(codecs)):
            if matchCodecs(codecs[idx], capCodec):
                filteredCodecs.append(codecs[idx])

                if idx + 1 < len(codecs):
                    if isRtxCodec(codecs[idx + 1]):
                        filteredCodecs.append(codecs[idx + 1])
                        break
        
        if not filteredCodecs:
            raise TypeError('no matching codec found')
    
    return filteredCodecs

# Create RTP parameters for a Consumer for the RTP probator.
def generateProbatorRtpParameters(videoRtpParameters: RtpParameters) -> RtpParameters:
    videoRtpParameters = videoRtpParameters.copy(deep=True)

    rtpParameters: RtpParameters = RtpParameters(
        mid=RTP_PROBATOR_MID,
        encodings=[RtpEncodingParameters(ssrc=RTP_PROBATOR_SSRC)],
        rtcp=RtcpParameters(cname='probator')
    )

    rtpParameters.codecs.append(videoRtpParameters.codecs[0])
    rtpParameters.codecs[0].payloadType = RTP_PROBATOR_CODEC_PAYLOAD_TYPE
    rtpParameters.headerExtensions = videoRtpParameters.headerExtensions

    return rtpParameters

# Whether media can be sent based on the given RTP capabilities.
def canSend(kind: MediaKind, extendedRtpCapabilities: ExtendedRtpCapabilities) -> bool:
    return len([codec for codec in extendedRtpCapabilities.codecs if codec.kind == kind]) > 0

# Whether the given RTP parameters can be received with the given RTP
# capabilities.
def canReceive(rtpParameters: RtpParameters, extendedRtpCapabilities: ExtendedRtpCapabilities) -> bool:
    if not rtpParameters.codecs:
        return False
    
    firstMediaCodec = rtpParameters.codecs[0]

    return len([codec for codec in extendedRtpCapabilities.codecs if codec.remotePayloadType == firstMediaCodec.payloadType]) > 0
