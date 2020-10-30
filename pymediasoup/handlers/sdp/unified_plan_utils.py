import re
from typing import List
from ...rtp_parameters import RtpEncodingParameters, RTX


def getRtpEncodings(offerMediaDict: dict) -> List[RtpEncodingParameters]:
    ssrcs = set()
    for line in offerMediaDict.get('ssrcs', []):
        ssrc = line.get('id')
        ssrcs.add(ssrc)
    
    if len(ssrcs) == 0:
        raise Exception('no a=ssrc lines found')

    ssrcToRtxSsrc = {}

    # First assume RTX is used.
    for line in offerMediaDict.get('ssrcGroups', []):
        if line.get('semantics') != 'FID':
            continue
        ssrc, rtxSsrc = re.split('\s', line.get('ssrcs'))

        ssrc = int(ssrc)
        rtxSsrc = int(rtxSsrc)

        if ssrc in ssrcs:
            # Remove both the SSRC and RTX SSRC from the set so later we know that they
            # are already handled.
            ssrcs.remove(ssrc)
            ssrcs.remove(rtxSsrc)

            # Add to the map.
            ssrcToRtxSsrc[ssrc] = rtxSsrc
    
    # If the set of SSRCs is not empty it means that RTX is not being used, so take
    # media SSRCs from there.
    for ssrc in ssrcs:
        ssrcToRtxSsrc[ssrc] = None
    
    encodings: List[RtpEncodingParameters] = []
    for ssrc, rtxSsrc in ssrcToRtxSsrc.items():
        encoding = RtpEncodingParameters(ssrc=ssrc)
        if rtxSsrc != None:
            encoding.rtx = RTX(ssrc=rtxSsrc)
        encodings.append(encoding)
    return encodings

# Adds multi-ssrc based simulcast into the given SDP media section offer.
def addLegacySimulcast(offerMediaDict: dict, numStreams: int):
    if numStreams <= 1:
        raise Exception('numStreams must be greater than 1')

    # Get the SSRC.
    ssrcMsidLines = [line for line in offerMediaDict.get('ssrcs', []) if line.get('attribute') == 'msid']
    if not ssrcMsidLines:
        raise Exception('a=ssrc line with msid information not found')
    
    ssrcMsidLine = ssrcMsidLines[0]

    # NOTE: const [ streamId, trackId ] = ssrcMsidLine.value.split(' ')[0];
    streamId, trackId = ssrcMsidLine.get('value').split(' ')
    firstSsrc = ssrcMsidLine.get('id')

    firstRtxSsrc = None

    # Get the SSRC for RTX.
    for line in offerMediaDict.get('ssrcGroups', []):
        if line.get('semantics') != 'FID':
            # False
            continue
        ssrcs = re.split('\s', line.get('ssrcs'))
        if int(ssrcs[0]) == firstSsrc:
            firstRtxSsrc = int(ssrcs[1])
            # True
    
    ssrcCnameLine = [line for line in offerMediaDict.get('ssrcs', []) if line.get('attribute') == 'cname']

    if not ssrcCnameLine:
        raise Exception('a=ssrc line with cname information not found')
    
    cname = ssrcCnameLine.get('value')

    ssrcs = []
    rtxSsrcs = []

    for i in range(numStreams):
        ssrcs.append(firstSsrc + i)
        if firstRtxSsrc != None:
            rtxSsrcs.append(firstRtxSsrc + i)
    
    offerMediaDict['ssrcGroups'] = []
    offerMediaDict['ssrcs'] = []

    offerMediaDict['ssrcGroups'].append({
        'semantics': 'SIM',
        'ssrc': ' '.join(ssrcs)
    })

    for ssrc in ssrcs:
        offerMediaDict['ssrcs'].append({
            'id': ssrc,
            'attribute': 'cname',
            'value': cname
        })
        offerMediaDict['ssrcs'].append({
            'id': ssrc,
            'attribute': 'msid',
            'value': f'{streamId} {trackId}'
        })
    
    for i in range(len(rtxSsrcs)):
        ssrc = ssrcs[i]
        rtxSsrc = rtxSsrcs[i]

        offerMediaDict['ssrc'].append({
            'id': rtxSsrc,
            'attribute': 'cname',
            'value': cname
        })
        offerMediaDict['ssrc'].append({
            'id': rtxSsrc,
            'attribute': 'msid',
            'value': f'{streamId} {trackId}'
        })
        offerMediaDict['ssrc'].append({
            'id': 'FID',
            'ssrcs': f'{ssrc} {rtxSsrc}'
        })

