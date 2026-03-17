from typing import List, Optional

import h264_profile_level_id as h264

from .rtp_parameters import (
    ExtendedCodec,
    ExtendedHeaderExtension,
    ExtendedRtpCapabilities,
    MediaKind,
    RtcpFeedback,
    RtcpParameters,
    RtpCapabilities,
    RtpCodec,
    RtpCodecCapability,
    RtpCodecParameters,
    RtpEncodingParameters,
    RtpHeaderExtension,
    RtpHeaderExtensionParameters,
    RtpParameters,
)
from .sctp_parameters import NumSctpStreams, SctpCapabilities, SctpStreamParameters


RTP_PROBATOR_MID = "probator"
RTP_PROBATOR_SSRC = 1234
RTP_PROBATOR_CODEC_PAYLOAD_TYPE = 127


def matchCodecs(
    aCodec: RtpCodec, bCodec: RtpCodec, strict: bool = False, modify: bool = False
) -> bool:
    aMimeType = aCodec.mimeType.lower()
    bMimeType = bCodec.mimeType.lower()

    if aMimeType != bMimeType:
        return False
    if aCodec.clockRate != bCodec.clockRate:
        return False
    if aCodec.channels != bCodec.channels:
        return False

    if aMimeType == "video/h264":
        aPacketizationMode = aCodec.parameters.get("packetization-mode", 0)
        bPacketizationMode = bCodec.parameters.get("packetization-mode", 0)

        if aPacketizationMode != bPacketizationMode:
            return False

        if strict:
            if not h264.isSameProfile(aCodec.parameters, bCodec.parameters):
                return False

            if modify:
                try:
                    selectedProfileLevelId = h264.generateProfileLevelIdForAnswer(
                        aCodec.parameters, bCodec.parameters
                    )
                except TypeError:
                    return False
                else:
                    if selectedProfileLevelId:
                        aCodec.parameters["profile-level-id"] = selectedProfileLevelId
                        bCodec.parameters["profile-level-id"] = selectedProfileLevelId
                    else:
                        aCodec.parameters.pop("profile-level-id", None)
                        bCodec.parameters.pop("profile-level-id", None)

    elif aMimeType == "video/vp9" and strict:
        aProfileId = aCodec.parameters.get("profile-id", 0)
        bProfileId = bCodec.parameters.get("profile-id", 0)

        if aProfileId != bProfileId:
            return False

    return True


def isRtxCodec(codec: Optional[RtpCodec]) -> bool:
    if not codec:
        return False

    return codec.mimeType.lower().endswith("/rtx")


def reduceRtcpFeedback(codecA: RtpCodec, codecB: RtpCodec) -> List[RtcpFeedback]:
    reducedRtcpFeedback: List[RtcpFeedback] = []

    for aFb in codecA.rtcpFeedback:
        matchingBFb = next(
            (
                bFb
                for bFb in codecB.rtcpFeedback
                if bFb.type == aFb.type
                and (
                    bFb.parameter == aFb.parameter
                    or (not bFb.parameter and not aFb.parameter)
                )
            ),
            None,
        )

        if matchingBFb:
            reducedRtcpFeedback.append(matchingBFb)

    return reducedRtcpFeedback


def matchHeaderExtensions(aExt: RtpHeaderExtension, bExt: RtpHeaderExtension) -> bool:
    if aExt.kind and bExt.kind and aExt.kind != bExt.kind:
        return False
    if aExt.uri != bExt.uri:
        return False

    return True


def getExtendedRtpCapabilities(
    localCaps: RtpCapabilities,
    remoteCaps: RtpCapabilities,
    preferLocalCodecsOrder: bool = False,
) -> ExtendedRtpCapabilities:
    extendedRtpCapabilities = ExtendedRtpCapabilities()

    if preferLocalCodecsOrder:
        for localCodec in localCaps.codecs:
            if isRtxCodec(localCodec):
                continue

            matchingRemoteCodec = next(
                (
                    remoteCodec
                    for remoteCodec in remoteCaps.codecs
                    if matchCodecs(remoteCodec, localCodec, strict=True, modify=True)
                ),
                None,
            )

            if not matchingRemoteCodec:
                continue

            extendedRtpCapabilities.codecs.append(
                ExtendedCodec(
                    kind=localCodec.kind,
                    mimeType=localCodec.mimeType,
                    clockRate=localCodec.clockRate,
                    channels=localCodec.channels,
                    localPayloadType=localCodec.preferredPayloadType,
                    remotePayloadType=matchingRemoteCodec.preferredPayloadType,
                    localParameters=localCodec.parameters,
                    remoteParameters=matchingRemoteCodec.parameters,
                    rtcpFeedback=reduceRtcpFeedback(localCodec, matchingRemoteCodec),
                )
            )
    else:
        for remoteCodec in remoteCaps.codecs:
            if isRtxCodec(remoteCodec):
                continue

            matchingLocalCodec = next(
                (
                    localCodec
                    for localCodec in localCaps.codecs
                    if matchCodecs(localCodec, remoteCodec, strict=True, modify=True)
                ),
                None,
            )

            if not matchingLocalCodec:
                continue

            extendedRtpCapabilities.codecs.append(
                ExtendedCodec(
                    kind=matchingLocalCodec.kind,
                    mimeType=matchingLocalCodec.mimeType,
                    clockRate=matchingLocalCodec.clockRate,
                    channels=matchingLocalCodec.channels,
                    localPayloadType=matchingLocalCodec.preferredPayloadType,
                    remotePayloadType=remoteCodec.preferredPayloadType,
                    localParameters=matchingLocalCodec.parameters,
                    remoteParameters=remoteCodec.parameters,
                    rtcpFeedback=reduceRtcpFeedback(matchingLocalCodec, remoteCodec),
                )
            )

    for extendedCodec in extendedRtpCapabilities.codecs:
        matchingLocalRtxCodec = next(
            (
                localCodec
                for localCodec in localCaps.codecs
                if isRtxCodec(localCodec)
                and localCodec.parameters.get("apt") == extendedCodec.localPayloadType
            ),
            None,
        )
        matchingRemoteRtxCodec = next(
            (
                remoteCodec
                for remoteCodec in remoteCaps.codecs
                if isRtxCodec(remoteCodec)
                and remoteCodec.parameters.get("apt") == extendedCodec.remotePayloadType
            ),
            None,
        )

        if matchingLocalRtxCodec and matchingRemoteRtxCodec:
            extendedCodec.localRtxPayloadType = matchingLocalRtxCodec.preferredPayloadType
            extendedCodec.remoteRtxPayloadType = (
                matchingRemoteRtxCodec.preferredPayloadType
            )

    for remoteExt in remoteCaps.headerExtensions:
        matchingLocalExt = next(
            (
                localExt
                for localExt in localCaps.headerExtensions
                if matchHeaderExtensions(localExt, remoteExt)
            ),
            None,
        )

        if not matchingLocalExt:
            continue

        extendedExt = ExtendedHeaderExtension(
            kind=remoteExt.kind,
            uri=remoteExt.uri,
            sendId=matchingLocalExt.preferredId,
            recvId=remoteExt.preferredId,
            encrypt=bool(matchingLocalExt.preferredEncrypt),
            direction="sendrecv",
        )

        if remoteExt.direction == "recvonly":
            extendedExt.direction = "sendonly"
        elif remoteExt.direction == "sendonly":
            extendedExt.direction = "recvonly"
        elif remoteExt.direction == "inactive":
            extendedExt.direction = "inactive"

        extendedRtpCapabilities.headerExtensions.append(extendedExt)

    return extendedRtpCapabilities


def getRecvRtpCapabilities(
    extendedRtpCapabilities: ExtendedRtpCapabilities,
) -> RtpCapabilities:
    return _getRtpCapabilities("recvonly", extendedRtpCapabilities)


def getSendRtpCapabilities(
    extendedRtpCapabilities: ExtendedRtpCapabilities,
) -> RtpCapabilities:
    return _getRtpCapabilities("sendonly", extendedRtpCapabilities)


def getSendingRtpParameters(
    kind: MediaKind, extendedRtpCapabilities: ExtendedRtpCapabilities
) -> RtpParameters:
    rtpParameters = RtpParameters(rtcp=RtcpParameters())

    for extendedCodec in extendedRtpCapabilities.codecs:
        if extendedCodec.kind != kind:
            continue

        rtpParameters.codecs.append(
            RtpCodecParameters(
                mimeType=extendedCodec.mimeType,
                payloadType=extendedCodec.localPayloadType,
                clockRate=extendedCodec.clockRate,
                channels=extendedCodec.channels,
                parameters=extendedCodec.localParameters,
                rtcpFeedback=extendedCodec.rtcpFeedback,
            )
        )

        if extendedCodec.localRtxPayloadType:
            rtpParameters.codecs.append(
                RtpCodecParameters(
                    mimeType=f"{extendedCodec.kind}/rtx",
                    payloadType=extendedCodec.localRtxPayloadType,
                    clockRate=extendedCodec.clockRate,
                    parameters={"apt": extendedCodec.localPayloadType},
                    rtcpFeedback=[],
                )
            )

    for extendedExtension in extendedRtpCapabilities.headerExtensions:
        if (extendedExtension.kind and extendedExtension.kind != kind) or (
            extendedExtension.direction not in ["sendrecv", "sendonly"]
        ):
            continue

        rtpParameters.headerExtensions.append(
            RtpHeaderExtensionParameters(
                uri=extendedExtension.uri,
                id=extendedExtension.sendId,
                encrypt=extendedExtension.encrypt,
                parameters={},
            )
        )

    return rtpParameters


def getSendingRemoteRtpParameters(
    kind: MediaKind, extendedRtpCapabilities: ExtendedRtpCapabilities
) -> RtpParameters:
    rtpParameters = RtpParameters(rtcp=RtcpParameters())

    for extendedCodec in extendedRtpCapabilities.codecs:
        if extendedCodec.kind != kind:
            continue

        rtpParameters.codecs.append(
            RtpCodecParameters(
                mimeType=extendedCodec.mimeType,
                payloadType=extendedCodec.localPayloadType,
                clockRate=extendedCodec.clockRate,
                channels=extendedCodec.channels,
                parameters=extendedCodec.remoteParameters,
                rtcpFeedback=extendedCodec.rtcpFeedback,
            )
        )

        if extendedCodec.localRtxPayloadType:
            rtpParameters.codecs.append(
                RtpCodecParameters(
                    mimeType=f"{extendedCodec.kind}/rtx",
                    payloadType=extendedCodec.localRtxPayloadType,
                    clockRate=extendedCodec.clockRate,
                    parameters={"apt": extendedCodec.localPayloadType},
                    rtcpFeedback=[],
                )
            )

    for extendedExtension in extendedRtpCapabilities.headerExtensions:
        if (extendedExtension.kind and extendedExtension.kind != kind) or (
            extendedExtension.direction not in ["sendrecv", "sendonly"]
        ):
            continue

        rtpParameters.headerExtensions.append(
            RtpHeaderExtensionParameters(
                uri=extendedExtension.uri,
                id=extendedExtension.sendId,
                encrypt=extendedExtension.encrypt,
                parameters={},
            )
        )

    if any(
        ext.uri
        == "http://www.ietf.org/id/draft-holmer-rmcat-transport-wide-cc-extensions-01"
        for ext in rtpParameters.headerExtensions
    ):
        for codec in rtpParameters.codecs:
            codec.rtcpFeedback = [
                fb for fb in codec.rtcpFeedback if fb.type != "goog-remb"
            ]
    elif any(
        ext.uri == "http://www.webrtc.org/experiments/rtp-hdrext/abs-send-time"
        for ext in rtpParameters.headerExtensions
    ):
        for codec in rtpParameters.codecs:
            codec.rtcpFeedback = [
                fb for fb in codec.rtcpFeedback if fb.type != "transport-cc"
            ]
    else:
        for codec in rtpParameters.codecs:
            codec.rtcpFeedback = [
                fb
                for fb in codec.rtcpFeedback
                if fb.type not in ["transport-cc", "goog-remb"]
            ]

    return rtpParameters


def reduceCodecs(
    codecs: List[RtpCodecParameters], capCodec: Optional[RtpCodecCapability] = None
) -> List[RtpCodecParameters]:
    filteredCodecs: List[RtpCodecParameters] = []

    if not capCodec:
        filteredCodecs.append(codecs[0])

        if len(codecs) > 1 and isRtxCodec(codecs[1]):
            filteredCodecs.append(codecs[1])
    else:
        for idx, codec in enumerate(codecs):
            if matchCodecs(codec, capCodec, strict=True):
                filteredCodecs.append(codec)

                if idx + 1 < len(codecs) and isRtxCodec(codecs[idx + 1]):
                    filteredCodecs.append(codecs[idx + 1])

                break

        if not filteredCodecs:
            raise TypeError("no matching codec found")

    return filteredCodecs


def generateProbatorRtpParameters(videoRtpParameters: RtpParameters) -> RtpParameters:
    videoRtpParameters = videoRtpParameters.copy(deep=True)
    validateAndNormalizeRtpParameters(videoRtpParameters)

    rtpParameters = RtpParameters(
        mid=RTP_PROBATOR_MID,
        encodings=[RtpEncodingParameters(ssrc=RTP_PROBATOR_SSRC)],
        rtcp=RtcpParameters(cname="probator"),
    )

    rtpParameters.codecs.append(videoRtpParameters.codecs[0])
    rtpParameters.codecs[0].payloadType = RTP_PROBATOR_CODEC_PAYLOAD_TYPE
    rtpParameters.headerExtensions = videoRtpParameters.headerExtensions

    return rtpParameters


def canSend(kind: MediaKind, extendedRtpCapabilities: ExtendedRtpCapabilities) -> bool:
    return any(codec.kind == kind for codec in extendedRtpCapabilities.codecs)


def canReceive(
    rtpParameters: RtpParameters, extendedRtpCapabilities: ExtendedRtpCapabilities
) -> bool:
    validateAndNormalizeRtpParameters(rtpParameters)

    if not rtpParameters.codecs:
        return False

    firstMediaCodec = rtpParameters.codecs[0]

    return any(
        codec.remotePayloadType == firstMediaCodec.payloadType
        for codec in extendedRtpCapabilities.codecs
    )


def validateAndNormalizeRtpCapabilities(caps: RtpCapabilities) -> None:
    if not isinstance(caps, RtpCapabilities):
        raise TypeError("caps is not an object")

    for codec in caps.codecs:
        validateAndNormalizeRtpCodecCapability(codec)

    for ext in caps.headerExtensions:
        validateAndNormalizeRtpHeaderExtension(ext)


def validateAndNormalizeRtpParameters(params: RtpParameters) -> None:
    if not isinstance(params, RtpParameters):
        raise TypeError("params is not an object")

    if params.mid is not None and not isinstance(params.mid, str):
        raise TypeError("params.mid is not a string")

    for codec in params.codecs:
        validateAndNormalizeRtpCodecParameters(codec)

    for ext in params.headerExtensions:
        validateRtpHeaderExtensionParameters(ext)

    for encoding in params.encodings:
        validateAndNormalizeRtpEncodingParameters(encoding)

    if params.rtcp is None:
        params.rtcp = RtcpParameters()
    elif not isinstance(params.rtcp, RtcpParameters):
        raise TypeError("params.rtcp is not an object")

    validateAndNormalizeRtcpParameters(params.rtcp)


def validateAndNormalizeSctpStreamParameters(params: SctpStreamParameters) -> None:
    if not isinstance(params, SctpStreamParameters):
        raise TypeError("params is not an object")

    if params.streamId is None or not isinstance(params.streamId, int):
        raise TypeError("missing params.streamId")

    if params.ordered is None:
        params.ordered = True
    elif not isinstance(params.ordered, bool):
        raise TypeError("invalid params.ordered")

    if params.maxPacketLifeTime is not None and not isinstance(
        params.maxPacketLifeTime, int
    ):
        raise TypeError("invalid params.maxPacketLifeTime")

    if params.maxRetransmits is not None and not isinstance(params.maxRetransmits, int):
        raise TypeError("invalid params.maxRetransmits")

    if params.maxPacketLifeTime is not None and params.maxRetransmits is not None:
        raise TypeError("cannot provide both maxPacketLifeTime and maxRetransmits")

    if params.maxPacketLifeTime is not None or params.maxRetransmits is not None:
        params.ordered = False

    if params.label is not None and not isinstance(params.label, str):
        raise TypeError("invalid params.label")

    if params.protocol is not None and not isinstance(params.protocol, str):
        raise TypeError("invalid params.protocol")


def validateSctpCapabilities(caps: SctpCapabilities) -> None:
    if not isinstance(caps, SctpCapabilities):
        raise TypeError("caps is not an object")

    if not isinstance(caps.numStreams, NumSctpStreams):
        raise TypeError("missing caps.numStreams")

    validateNumSctpStreams(caps.numStreams)


def validateNumSctpStreams(numStreams: NumSctpStreams) -> None:
    if not isinstance(numStreams, NumSctpStreams):
        raise TypeError("numStreams is not an object")

    if not isinstance(numStreams.OS, int):
        raise TypeError("missing numStreams.OS")

    if not isinstance(numStreams.MIS, int):
        raise TypeError("missing numStreams.MIS")


def validateAndNormalizeRtpCodecCapability(codec: RtpCodecCapability) -> None:
    if not isinstance(codec, RtpCodecCapability):
        raise TypeError("codec is not an object")

    mimeTypeParts = codec.mimeType.split("/", 1)
    if len(mimeTypeParts) != 2:
        raise TypeError("invalid codec.mimeType")

    codec.kind = mimeTypeParts[0].lower()

    if codec.preferredPayloadType is None or not isinstance(codec.preferredPayloadType, int):
        raise TypeError("missing codec.preferredPayloadType")

    if not isinstance(codec.clockRate, int):
        raise TypeError("missing codec.clockRate")

    if codec.kind == "audio":
        if not isinstance(codec.channels, int):
            codec.channels = 1
    else:
        codec.channels = None

    _normalizeCodecParameters(codec)
    _normalizeRtcpFeedbackList(codec.rtcpFeedback)


def validateAndNormalizeRtpCodecParameters(codec: RtpCodecParameters) -> None:
    if not isinstance(codec, RtpCodecParameters):
        raise TypeError("codec is not an object")

    mimeTypeParts = codec.mimeType.split("/", 1)
    if len(mimeTypeParts) != 2:
        raise TypeError("invalid codec.mimeType")

    if not isinstance(codec.payloadType, int):
        raise TypeError("missing codec.payloadType")

    if not isinstance(codec.clockRate, int):
        raise TypeError("missing codec.clockRate")

    kind = mimeTypeParts[0].lower()
    if kind == "audio":
        if not isinstance(codec.channels, int):
            codec.channels = 1
    else:
        codec.channels = None

    _normalizeCodecParameters(codec)
    _normalizeRtcpFeedbackList(codec.rtcpFeedback)


def validateAndNormalizeRtpHeaderExtension(ext: RtpHeaderExtension) -> None:
    if not isinstance(ext, RtpHeaderExtension):
        raise TypeError("ext is not an object")

    if ext.kind is not None and ext.kind not in ["audio", "video"]:
        raise TypeError("invalid ext.kind")

    if not isinstance(ext.uri, str):
        raise TypeError("missing ext.uri")

    if not isinstance(ext.preferredId, int):
        raise TypeError("missing ext.preferredId")

    if ext.preferredEncrypt is None:
        ext.preferredEncrypt = False
    elif not isinstance(ext.preferredEncrypt, bool):
        raise TypeError("invalid ext.preferredEncrypt")

    if ext.direction is None:
        ext.direction = "sendrecv"
    elif ext.direction not in ["sendrecv", "sendonly", "recvonly", "inactive"]:
        raise TypeError("invalid ext.direction")


def validateRtpHeaderExtensionParameters(ext: RtpHeaderExtensionParameters) -> None:
    if not isinstance(ext, RtpHeaderExtensionParameters):
        raise TypeError("ext is not an object")

    if not isinstance(ext.uri, str):
        raise TypeError("missing ext.uri")

    if not isinstance(ext.id, int):
        raise TypeError("missing ext.id")

    if ext.encrypt is None:
        ext.encrypt = False
    elif not isinstance(ext.encrypt, bool):
        raise TypeError("invalid ext.encrypt")

    if ext.parameters is None:
        ext.parameters = {}
    elif not isinstance(ext.parameters, dict):
        raise TypeError("invalid ext.parameters")

    for key, value in list(ext.parameters.items()):
        if value is None:
            ext.parameters[key] = ""
            value = ""

        if not isinstance(value, (str, int, float)):
            raise TypeError("invalid header extension parameter")


def validateAndNormalizeRtpEncodingParameters(encoding: RtpEncodingParameters) -> None:
    if not isinstance(encoding, RtpEncodingParameters):
        raise TypeError("encoding is not an object")

    if encoding.ssrc is not None and not isinstance(encoding.ssrc, int):
        raise TypeError("invalid encoding.ssrc")

    if encoding.rid is not None and not isinstance(encoding.rid, str):
        raise TypeError("invalid encoding.rid")

    if encoding.codecPayloadType is not None and not isinstance(encoding.codecPayloadType, int):
        raise TypeError("invalid encoding.codecPayloadType")

    if encoding.rtx is not None and not isinstance(encoding.rtx.ssrc, int):
        raise TypeError("missing encoding.rtx.ssrc")

    if not isinstance(encoding.dtx, bool):
        encoding.dtx = False

    if encoding.scalabilityMode is not None and not isinstance(encoding.scalabilityMode, str):
        raise TypeError("invalid encoding.scalabilityMode")


def validateAndNormalizeRtcpParameters(rtcp: RtcpParameters) -> None:
    if not isinstance(rtcp, RtcpParameters):
        raise TypeError("rtcp is not an object")

    if rtcp.cname is not None and not isinstance(rtcp.cname, str):
        raise TypeError("invalid rtcp.cname")

    if not isinstance(rtcp.reducedSize, bool):
        rtcp.reducedSize = True


def _getRtpCapabilities(
    direction: str, extendedRtpCapabilities: ExtendedRtpCapabilities
) -> RtpCapabilities:
    rtpCapabilities = RtpCapabilities()

    for extendedCodec in extendedRtpCapabilities.codecs:
        if direction == "recvonly":
            preferredPayloadType = extendedCodec.remotePayloadType
            rtxPayloadType = extendedCodec.remoteRtxPayloadType
            apt = extendedCodec.remotePayloadType
        else:
            preferredPayloadType = extendedCodec.localPayloadType
            rtxPayloadType = extendedCodec.localRtxPayloadType
            apt = extendedCodec.localPayloadType

        rtpCapabilities.codecs.append(
            RtpCodecCapability(
                kind=extendedCodec.kind,
                mimeType=extendedCodec.mimeType,
                preferredPayloadType=preferredPayloadType,
                clockRate=extendedCodec.clockRate,
                channels=extendedCodec.channels,
                parameters=extendedCodec.localParameters,
                rtcpFeedback=extendedCodec.rtcpFeedback,
            )
        )

        if rtxPayloadType is not None:
            rtpCapabilities.codecs.append(
                RtpCodecCapability(
                    kind=extendedCodec.kind,
                    mimeType=f"{extendedCodec.kind}/rtx",
                    preferredPayloadType=rtxPayloadType,
                    clockRate=extendedCodec.clockRate,
                    parameters={"apt": apt},
                    rtcpFeedback=[],
                )
            )

    for extendedExtension in extendedRtpCapabilities.headerExtensions:
        if extendedExtension.direction not in ["sendrecv", direction]:
            continue

        preferredId = (
            extendedExtension.recvId if direction == "recvonly" else extendedExtension.sendId
        )

        rtpCapabilities.headerExtensions.append(
            RtpHeaderExtension(
                kind=extendedExtension.kind,
                uri=extendedExtension.uri,
                preferredId=preferredId,
                preferredEncrypt=extendedExtension.encrypt,
                direction=extendedExtension.direction,
            )
        )

    return rtpCapabilities


def _normalizeCodecParameters(codec: RtpCodec) -> None:
    if codec.parameters is None:
        codec.parameters = {}
    elif not isinstance(codec.parameters, dict):
        raise TypeError("invalid codec.parameters")

    for key, value in list(codec.parameters.items()):
        if value is None:
            codec.parameters[key] = ""
            value = ""

        if not isinstance(value, (str, int, float)):
            raise TypeError(f"invalid codec parameter [key:{key}, value:{value}]")

        if key == "apt" and not isinstance(value, int):
            raise TypeError("invalid codec apt parameter")


def _normalizeRtcpFeedbackList(feedbacks: List[RtcpFeedback]) -> None:
    if not isinstance(feedbacks, list):
        raise TypeError("codec.rtcpFeedback is not an array")

    for feedback in feedbacks:
        if not isinstance(feedback.type, str):
            raise TypeError("missing fb.type")

        if feedback.parameter is None or not isinstance(feedback.parameter, str):
            feedback.parameter = ""
