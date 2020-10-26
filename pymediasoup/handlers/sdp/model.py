import re
from re import Pattern
from typing import Literal, List, Type, TypeVar
from pydantic import BaseModel


class SdpModel(BaseModel):
    _pattern: str = r'(.*)'
    _pattern_keys: List[str] = []

    @classmethod
    def parse_sdp(cls: Type['SdpModel'], sdp: str) -> 'SdpModel':
        match = re.match(cls._pattern, sdp)
        obj = {}
        if match:
            index = 0
            for key in cls._pattern_keys:
                index += 1
                obj[key] = match.group(index)
        return cls(**obj)

class Origin(SdpModel):
    # o=- 20518 0 IN IP4 203.0.113.1
    _pattern = r'^(\S*) (\d*) (\d*) (\S*) IP(\d) (\S*)'
    _pattern_keys = ['username', 'sessionId', 'sessionVersion', 'netType', 'ipVer', 'address']
    username: str = '-'
    sessionId: str
    sessionVersion: int
    netType: str
    ipVer: int
    address: str

class Timing(SdpModel):
    # t=0 0
    _pattern = r'^(\d*) (\d*)'
    _pattern_keys = ['start', 'stop']
    start: int
    stop: int

class Connection(SdpModel):
    # c=IN IP4 10.47.197.26
    _pattern = r'^IN IP(\d) (\S*)'
    _pattern_keys = ['version', 'ip']
    version: int
    ip: str

class Bandwidth(SdpModel):
    # b=AS:4000
    _pattern = r'^(TIAS|AS|CT|RR|RS):(\d*)'
    _pattern_keys = ['type', 'limit']
    type: str
    limit: str

class Fingerprint(SdpModel):
    # a=fingerprint:SHA-1 00:11:22:33:44:55:66:77:88:99:AA:BB:CC:DD:EE:FF:00:11:22:33
    _pattern = r'^fingerprint:(\S*) (\S*)'
    _pattern_keys = ['type', 'hash']
    type: str
    hash: str

class Rtp(BaseModel):
    # a=rtpmap:110 opus/48000/2
    _pattern = r'^rtpmap:(\d*) ([\w\-.]*)(?:\s*\/(\d*)(?:\s*\/(\S*))?)?'
    _pattern_keys = ['payload', 'codec', 'rate', 'encoding']
    payload: int
    codec: str
    rate: int
    encoding: str

class Fmtp(BaseModel):
    # a=fmtp:108 profile-level-id=24;object=23;bitrate=64000
    # a=fmtp:111 minptime=10; useinbandfec=1
    _pattern = r'^fmtp:(\d*) ([\S| ]*)'
    _pattern_keys = ['payload', 'config']
    payload: int
    config: str

class Candidate(BaseModel):
    _pattern = r'^IN IP(\d) (\S*)'
    _pattern_keys = ['version', 'ip']
    foundation: int
    component: int
    transport: str
    priority: int
    ip: str
    port: int
    type: str

class Attribute(BaseModel):
    rtp: List[Rtp]
    fmtp: List[Fmtp]
    control: str
    

class Media(BaseModel):
    # m=video 51744 RTP/AVP 126 97 98 34 31
    _pattern = r'^(\w*) (\d*) ([\w/]*)(?: (.*))?'
    _pattern_keys = ['type', 'port', 'protocol', 'payloads']
    attribute: Attribute
    type: str
    port: int
    protocol: str
    payloads: str
    direction: str
    candidates: List[Candidate]

class SessionDescriptionProtocol(BaseModel):
    version: int
    origin: Origin
    name: str
    timing: Timing
    connection: Connection
    iceUfrag: str
    icePwd: str
    fingerprint: Fingerprint
    media: List[Media]

    def parse_str(self, sdp: str):
        pass

    
    def parse_field(self, character: str, value: str):
        if character == 'v':
            self.version = int(value)
        elif character == 'o':
            pass
