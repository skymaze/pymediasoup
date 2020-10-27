from typing import List

from .sdp_transform import parseParams
from ...transport import DtlsParameters, DtlsRole, DtlsFingerprint
from ...rtp_parameters import RtpCapabilities, RtpCodecCapability, RtpHeaderExtension, RtpParameters, RtcpFeedback


def extractRtpCapabilities(sdpDict: dict) -> RtpCapabilities:
    # Map of RtpCodecParameters indexed by payload type.
    codecsMap: {}
    # Array of RtpHeaderExtensions.
    headerExtensions: List[RtpHeaderExtension] = []
    # Whether a m=audio/video section has been already found.
    gotAudio = False
    gotVideo = False

    m: dict
    for m in sdpDict.get('media', []):
        kind: str = m.get('type')
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
        rtp: dict
        for rtp in m.get('rtp', []):
            codec: RtpCodecCapability = RtpCodecCapability(
                kind=kind,
                mimeType=f"{kind}/{rtp.get('codec','')}",
                preferredPayloadType=rtp.get('payload'),
                clockRate=rtp.get('rate'),
                channels=rtp.get('encoding'),
                parameters={},
                rtcpFeedback=[]
            )
            codecsMap[codec.preferredPayloadType] = codec
        
        # Get codec parameters.
        for fmtp in m.get('fmtp', []):
            parameters = parseParams(fmtp.get('config'))
            codec = codecsMap.get(fmtp.get('payload'))

            if not codec:
                continue
            # Specials case to convert parameter value to string.
            if parameters.get('profile-level-id'):
                parameters['profile-level-id'] = str(parameters['profile-level-id'])
            codec.parameters = parameters

        # Get RTCP feedback for each codec.
        for fb in m.get('rtcpFb', []):
            codec = codecsMap.get(fb.get('payload'))
            if not codec:
                continue
            feedback = {
                'type': fb.get('type'),
                'parameter': fb.get('subtype')
            }
            if not feedback.get('parameter'):
                del feedback['parameter']
            codec.rtcpFeedback.append(feedback)

        # Get RTP header extensions.
        for ext in m.get('ext'):
            if ext.get('encrypt-uri'):
                continue
            headerExtension: RtpHeaderExtension = RtpHeaderExtension(
                kind=kind,
                uri=ext.get('uri'),
                preferredId=ext.get('value')
            )
            headerExtensions.append(headerExtension)

    rtpCapabilities: RtpCapabilities = RtpCapabilities(
        codecs=list(codecsMap.values()),
        headerExtensions=headerExtensions
    )

    return rtpCapabilities

def extractDtlsParameters(sdpDict: dict) -> DtlsParameters:
    mediaDicts = [m for m in sdpDict.get('media', []) if m.get('iceUfrag') and m.get('port') != 0]
    if not mediaDicts:
        raise Exception('no active media section found')
    mediaDict = mediaDicts[0]
    fingerprint = mediaDict.get('fingerprint') if mediaDict.get('fingerprint') else sdpDict.get('fingerprint')
    role = 'auto'
    if mediaDict.get('setup') == 'activate':
        role = 'client'
    elif mediaDict.get('setup') == 'passive':
        role = 'server'
    elif mediaDict.get('setup') == 'actpass':
        role = 'auto'
    
    dtlsParameters = DtlsParameters(
        role=role,
        fingerprint=[DtlsFingerprint(
            algorithm=fingerprint.get('type'),
            value=fingerprint.get('hash')
        )]
    )

    return dtlsParameters

def getCname(offerMediaDict: dict):
    ssrcCnameLines = [line for line in offerMediaDict.get('ssrcs', []) if line.get('attribute') == 'cname']
    if not ssrcCnameLines:
        return ''
    return ssrcCnameLines[0].get('value', '')