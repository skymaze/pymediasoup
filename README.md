# PyMediasoup
[![Python](https://img.shields.io/pypi/pyversions/pymediasoup)](https://www.python.org/)
[![Pypi](https://img.shields.io/pypi/v/pymediasoup)](https://pypi.org/project/pymediasoup/)
[![License](https://img.shields.io/pypi/l/pymediasoup)](https://github.com/skymaze/pymediasoup/blob/main/LICENSE)


[mediasoup](https://mediasoup.org/) python client


## Install
```bash
pip3 install pymediasoup
```

## Usage
PyMediasoup API design is similar to the official [mediasoup-client](https://github.com/versatica/mediasoup-client)

```python
from pymediasoup import Device
from pymediasoup import AiortcHandler

# Create a device
# In order to generate the correct parameters, here should contain all the tracks you want to use
tracks = []
device = Device(handlerFactory=AiortcHandler.createFactory(tracks=tracks))
```

## LICENSE
MIT