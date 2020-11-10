import logging
logging.basicConfig(level=logging.DEBUG)

import json
import asyncio
import argparse
import secrets

from pymediasoup import Device
from pymediasoup import AiortcHandler

# Import aiortc
from aiortc import VideoStreamTrack
from aiortc.mediastreams import AudioStreamTrack
from aiortc.contrib.media import MediaPlayer

# Implement simple protoo client
import websockets
from random import random
# Save answers temporarily
answers = {}

# websocket receive task
async def recv_msg_task(websocket):
    while True:
        await asyncio.sleep(0.5)
        answer = json.loads(await websocket.recv())
        if answer.get('id') != None:
            answers[answer.get('id')] = answer

# wait for answer ready
async def wait_answer_ready(id):
    while True:
        await asyncio.sleep(0.5)
        if answers.get(id) != None:
            break

# Generates a random positive integer.
def generateRandomNumber() -> int:
    return round(random() * 10000000)

async def run(uri, player):
    async with websockets.connect(uri, subprotocols=['protoo']) as websocket:
        task_run_recv_msg = asyncio.create_task(recv_msg_task(websocket))
        task_run_produce = asyncio.create_task(produce(player, websocket))

        await task_run_recv_msg
        await task_run_produce

async def produce(player, websocket):
    TRACKS = []

    if player and player.audio:
        audioTrack = player.audio
    else:
        audioTrack = AudioStreamTrack()
    if player and player.video:
        videoTrack = player.video
    else:
        videoTrack = VideoStreamTrack()

    TRACKS.append(videoTrack)
    TRACKS.append(audioTrack)

    # Init device
    device = Device(handlerFactory=AiortcHandler.createFactory(tracks=TRACKS))

    # Get Router RtpCapabilities
    reqId = generateRandomNumber()
    req = {
        'request': True,
        'id': reqId,
        'method': 'getRouterRtpCapabilities',
        'data': {}
    }
    await websocket.send(json.dumps(req))
    await asyncio.wait_for(wait_answer_ready(reqId), timeout=5)
    ans = answers.get(reqId)

    # Load Router RtpCapabilities
    await device.load(ans['data'])

    # Create Produce WebRtc Transport
    reqId = generateRandomNumber()
    req = {
        'request': True,
        'id': reqId,
        'method': 'createWebRtcTransport',
        'data': {
            'forceTcp': False,
            'producing': True,
            'consuming': False,
            'sctpCapabilities': device.sctpCapabilities.dict()
        }
    }
    await websocket.send(json.dumps(req))
    await asyncio.wait_for(wait_answer_ready(reqId), timeout=5)
    ans = answers.get(reqId)

    # Create send Transport
    sendTransport = device.createSendTransport(
        id=ans['data']['id'], 
        iceParameters=ans['data']['iceParameters'], 
        iceCandidates=ans['data']['iceCandidates'], 
        dtlsParameters=ans['data']['dtlsParameters'],
        sctpParameters=ans['data']['sctpParameters']
    )

    transId = ans['data']['id']

    @sendTransport.on('connect')
    async def on_connect(dtlsParameters):
        reqId = generateRandomNumber()
        req = {
            "request":True,
            "id":reqId,
            "method":"connectWebRtcTransport",
            "data":{
                "transportId": transId,
                "dtlsParameters": dtlsParameters.dict(exclude_none=True)
            }
        }
        await websocket.send(json.dumps(req))
        await asyncio.wait_for(wait_answer_ready(reqId), timeout=5)
    
    @sendTransport.on('produce')
    async def on_produce(kind: str, rtpParameters, appData: dict):
        reqId = generateRandomNumber()
        req = {
            "id": reqId,
            'method': 'produce',
            'request': True,
            'data': {
                'transportId': transId,
                'kind': kind,
                'rtpParameters': rtpParameters.dict(exclude_none=True),
                'appData': appData
            }
        }
        await websocket.send(json.dumps(req))
        await asyncio.wait_for(wait_answer_ready(reqId), timeout=5)
        ans = answers.get(reqId)
        return ans['data']['id']
    
    # Join room
    reqId = generateRandomNumber()
    req = {
        "request":True,
        "id":reqId,
        "method":"join",
        "data":{
            "displayName":"pymediasoup",
            "device":{
                "flag":"python",
                "name":"python","version":"0.1.0"
            },
            "rtpCapabilities": device.rtpCapabilities.dict(exclude_none=True),
            "sctpCapabilities":device.sctpCapabilities.dict(exclude_none=True)
        }
    }
    await websocket.send(json.dumps(req))
    await asyncio.wait_for(wait_answer_ready(reqId), timeout=5)
    ans = answers.get(reqId)

    # produce
    await sendTransport.produce(
        track=videoTrack,
        stopTracks=False,
        appData={}
    )
    await sendTransport.produce(
        track=audioTrack,
        stopTracks=False,
        appData={}
    )

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="PyMediaSoup")
    parser.add_argument("room", nargs="?")
    parser.add_argument("--play-from", help="Read the media from a file and sent it.")
    args = parser.parse_args()

    if not args.room:
        args.room = secrets.token_urlsafe(8).lower()
    peerId = secrets.token_urlsafe(8).lower()

    uri = f'wss://v3demo.mediasoup.org:4443/?roomId={args.room}&peerId={peerId}'

    if args.play_from:
        player = MediaPlayer(args.play_from)
    else:
        player = None

    # run event loop
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(run(uri=uri, player=player))
    except KeyboardInterrupt:
        pass
    finally:
        pass