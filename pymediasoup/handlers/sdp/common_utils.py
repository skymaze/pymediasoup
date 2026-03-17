from typing import Dict, List, Optional

from sdp_transform import parseParams
from ...models.transport import DtlsParameters, DtlsFingerprint
from ...rtp_parameters import (
    RtpCapabilities,
    RtpCodecCapability,
    RtpHeaderExtension,
    RtpParameters,
    RtcpFeedback,
)


def extractRtpCapabilities(sdpDict: dict) -> RtpCapabilities:
    # Map of RtpCodecParameters indexed by payload type.
    codecsMap: Dict[Optional[int], RtpCodecCapability] = {}
    # Array of RtpHeaderExtensions.
    headerExtensions: List[RtpHeaderExtension] = []
    # Whether a m=audio/video section has been already found.
    gotAudio = False
    gotVideo = False

    m: dict
    for m in sdpDict.get("media", []):
        kind = m.get("type")
        if kind not in ("audio", "video"):
            continue

        if kind == "audio":
            if gotAudio:
                continue
            gotAudio = True
        elif kind == "video":
            if gotVideo:
                continue
            gotVideo = True
        # Get codecs.
        rtp: dict
        for rtp in m.get("rtp", []):
            rate = rtp.get("rate")
            if rate is None:
                continue

            codecCapability = RtpCodecCapability(
                kind=kind,
                mimeType=f"{kind}/{rtp.get('codec', '')}",
                preferredPayloadType=rtp.get("payload"),
                clockRate=int(rate),
                channels=rtp.get("encoding"),
                parameters={},
                rtcpFeedback=[],
            )
            codecsMap[codecCapability.preferredPayloadType] = codecCapability

        # Get codec parameters.
        for fmtp in m.get("fmtp", []):
            parameters = parseParams(fmtp.get("config"))
            codecCapability = codecsMap.get(fmtp.get("payload"))

            if not codecCapability:
                continue
            # Specials case to convert parameter value to string.
            if parameters.get("profile-level-id"):
                parameters["profile-level-id"] = str(parameters["profile-level-id"])
            codecCapability.parameters = parameters

        # Get RTCP feedback for each codec.
        for fb in m.get("rtcpFb", []):
            codecCapability = codecsMap.get(fb.get("payload"))
            if not codecCapability:
                continue
            feedback = RtcpFeedback(
                type=fb.get("type"), parameter=fb.get("subtype", "")
            )
            codecCapability.rtcpFeedback.append(feedback)

        # Get RTP header extensions.
        for ext in m.get("ext") or []:
            if ext.get("encrypt-uri"):
                continue
            headerExtension: RtpHeaderExtension = RtpHeaderExtension(
                kind=kind, uri=ext.get("uri"), preferredId=ext.get("value")
            )
            headerExtensions.append(headerExtension)

    rtpCapabilities: RtpCapabilities = RtpCapabilities(
        codecs=list(codecsMap.values()), headerExtensions=headerExtensions
    )

    return rtpCapabilities


def extractDtlsParameters(sdpDict: dict) -> DtlsParameters:
    mediaDicts = [
        m for m in sdpDict.get("media", []) if m.get("iceUfrag") and m.get("port") != 0
    ]
    if not mediaDicts:
        raise Exception("no active media section found")
    mediaDict = mediaDicts[0]
    fingerprint: Optional[dict] = (
        mediaDict.get("fingerprint")
        if mediaDict.get("fingerprint")
        else sdpDict.get("fingerprint")
    )
    if fingerprint is None:
        raise Exception("no DTLS fingerprint found")
    role = "auto"
    if mediaDict.get("setup") == "activate":
        role = "client"
    elif mediaDict.get("setup") == "passive":
        role = "server"
    elif mediaDict.get("setup") == "actpass":
        role = "auto"

    dtlsParameters = DtlsParameters(
        role=role,
        fingerprints=[
            DtlsFingerprint(
                algorithm=fingerprint.get("type"), value=fingerprint.get("hash")
            )
        ],
    )

    return dtlsParameters


def getCname(offerMediaDict: dict):
    ssrcCnameLines = [
        line
        for line in offerMediaDict.get("ssrcs", [])
        if line.get("attribute") == "cname"
    ]
    if not ssrcCnameLines:
        return ""
    return ssrcCnameLines[0].get("value", "")


def applyCodecParameters(
    offerRtpParameters: RtpParameters, answerMediaDict: Optional[dict] = None
):
    if answerMediaDict is None:
        answerMediaDict = {}

    for codec in offerRtpParameters.codecs:
        mimeType = codec.mimeType.lower()
        if mimeType != "audio/opus":
            continue

        rtps = [
            r
            for r in answerMediaDict.get("rtp", [])
            if r.get("payload") == codec.payloadType
        ]

        if not rtps:
            continue

        fmtps = [
            f
            for f in answerMediaDict.get("fmtp", [])
            if f.get("payload") == codec.payloadType
        ]
        if not fmtps:
            fmtp = {"payload": codec.payloadType, "config": ""}
            if answerMediaDict.get("fmtp") is not None:
                answerMediaDict["fmtp"].append(fmtp)
            else:
                answerMediaDict["fmtp"] = [fmtp]
        else:
            fmtp = fmtps[0]

        parameters = parseParams(fmtp.get("config", ""))

        if mimeType == "audio/opus":
            spropStereo = codec.parameters.get("sprop-stereo")
            if spropStereo is not None:
                parameters["stereo"] = 1 if spropStereo else 0

        # Write the codec fmtp.config back.
        fmtp["config"] = ";".join(
            [f"{key}={value}" for key, value in parameters.items()]
        )
