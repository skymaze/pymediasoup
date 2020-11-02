from typing import List, Optional

from sdp_transform import parseParams
from ...models.transport import DtlsParameters, DtlsRole, DtlsFingerprint
from ...rtp_parameters import RtpCapabilities, RtpCodecCapability, RtpHeaderExtension, RtpParameters, RtcpFeedback


def extractRtpCapabilities(sdpDict: dict) -> RtpCapabilities:
    # Map of RtpCodecParameters indexed by payload type.
    codecsMap:dict = {}
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
        elif kind == 'video':
            if gotVideo:
                continue
            getVideo = True
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
            feedback = RtcpFeedback(
                type=fb.get('type'),
                parameter=fb.get('subtype', '')
            )
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
        fingerprints=[DtlsFingerprint(
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

def applyCodecParameters(offerRtpParameters: RtpParameters, answerMediaDict: Optional[dict] = {}):
    for codec in offerRtpParameters.codecs:
        mimeType = codec.mimeType.lower()
        if mimeType != 'audio/opus':
            continue

        rtps = [r for r in answerMediaDict.get('rtp', []) if r.get('payload') == codec.payloadType]
        if not rtps:
            continue
        rtp = rtps[0]
        
        fmtps = [f for f in answerMediaDict.get('rmtp', []) if f.get('payload') == codec.payloadType]
        if not fmtps:
            fmtp = {
                'payload': codec.payloadType,
                'config': ''
            }
            if answerMediaDict.get('rmtp') != None:
                answerMediaDict['fmtp'].append(fmtp)
            else:
                answerMediaDict['fmtp'] = [fmtp]
        else:
            fmtp = fmtps[0]
        
        parameters = parseParams(fmtp.get('config', ''))
        
        if mimeType == 'audio/opus':
            spropStereo = codec.parameters.get('sprop-stereo')
            if spropStereo != None:
                parameters['stereo'] = 1 if spropStereo else 0

        # Write the codec fmtp.config back.
        fmtp['config'] = ';'.join([f'{key}={value}' for key, value in parameters.items()])
