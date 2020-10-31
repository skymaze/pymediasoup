import inspect
from pyee import AsyncIOEventEmitter

class EnhancedEventEmitter(AsyncIOEventEmitter):
    def __init__(self, loop=None):
        super(EnhancedEventEmitter, self).__init__(loop=loop)
    
    async def emit_for_results(self, event, *args, **kwargs):
        results = []
        for f in list(self._events[event].values()):
            try:
                result = await f(*args, **kwargs)
            except Exception as exc:
                self.emit('error', exc)
            else:
                if result:
                    results.append(result)
        return results