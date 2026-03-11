# Examples

## mediaoup-demo
1. open https://v3demo.mediasoup.org/
2. copy roomId (keep the browser tab open)
3. run
```bash
uv run --with websockets python mediasoup.py roomId
```

If you see HTTP 403 during WebSocket handshake, the room may be expired/closed.
