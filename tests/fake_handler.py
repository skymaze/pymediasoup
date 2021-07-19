from pymediasoup.handlers.aiortc_handler import AiortcHandler
from pymediasoup.rtp_parameters import RtpCapabilities


class FakeHandler(AiortcHandler):
    def __init__(self, tracks=[], loop=None):
        super(FakeHandler, self).__init__(tracks=tracks, loop=loop)

    async def getNativeRtpCapabilities(self):
        nativeRtpCapabilities: RtpCapabilities = RtpCapabilities(
            **{
                "codecs": [
                    {
                        "mimeType": "audio/opus",
                        "kind": "audio",
                        "preferredPayloadType": 111,
                        "clockRate": 48000,
                        "channels": 2,
                        "rtcpFeedback": [{"type": "transport-cc"}],
                        "parameters": {"minptime": 10, "useinbandfec": 1},
                    },
                    {
                        "mimeType": "audio/ISAC",
                        "kind": "audio",
                        "preferredPayloadType": 103,
                        "clockRate": 16000,
                        "channels": 1,
                        "rtcpFeedback": [{"type": "transport-cc"}],
                        "parameters": {},
                    },
                    {
                        "mimeType": "audio/CN",
                        "kind": "audio",
                        "preferredPayloadType": 106,
                        "clockRate": 32000,
                        "channels": 1,
                        "rtcpFeedback": [{"type": "transport-cc"}],
                        "parameters": {},
                    },
                    {
                        "mimeType": "video/VP8",
                        "kind": "video",
                        "preferredPayloadType": 96,
                        "clockRate": 90000,
                        "rtcpFeedback": [
                            {"type": "goog-remb"},
                            {"type": "transport-cc"},
                            {"type": "ccm", "parameter": "fir"},
                            {"type": "nack"},
                            {"type": "nack", "parameter": "pli"},
                        ],
                        "parameters": {"baz": "1234abcd"},
                    },
                    {
                        "mimeType": "video/rtx",
                        "kind": "video",
                        "preferredPayloadType": 97,
                        "clockRate": 90000,
                        "rtcpFeedback": [],
                        "parameters": {"apt": 96},
                    },
                ],
                "headerExtensions": [
                    {
                        "kind": "audio",
                        "uri": "urn:ietf:params:rtp-hdrext:sdes:mid",
                        "preferredId": 1,
                    },
                    {
                        "kind": "video",
                        "uri": "urn:ietf:params:rtp-hdrext:sdes:mid",
                        "preferredId": 1,
                    },
                    {
                        "kind": "video",
                        "uri": "urn:ietf:params:rtp-hdrext:toffset",
                        "preferredId": 2,
                    },
                    {
                        "kind": "video",
                        "uri": "http://www.webrtc.org/experiments/rtp-hdrext/abs-send-time",
                        "preferredId": 3,
                    },
                    {
                        "kind": "video",
                        "uri": "urn:3gpp:video-orientation",
                        "preferredId": 4,
                    },
                    {
                        "kind": "video",
                        "uri": "http://www.ietf.org/id/draft-holmer-rmcat-transport-wide-cc-extensions-01",
                        "preferredId": 5,
                    },
                    {
                        "kind": "video",
                        "uri": "http://www.webrtc.org/experiments/rtp-hdrext/playout-delay",
                        "preferredId": 6,
                    },
                    {
                        "kind": "video",
                        "uri": "http://www.webrtc.org/experiments/rtp-hdrext/video-content-type",
                        "preferredId": 7,
                    },
                    {
                        "kind": "video",
                        "uri": "http://www.webrtc.org/experiments/rtp-hdrext/video-timing",
                        "preferredId": 8,
                    },
                    {
                        "kind": "audio",
                        "uri": "urn:ietf:params:rtp-hdrext:ssrc-audio-level",
                        "preferredId": 10,
                    },
                ],
                "fecMechanisms": [],
            }
        )
        return nativeRtpCapabilities
