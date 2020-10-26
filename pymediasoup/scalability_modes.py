import re
from pydantic import BaseModel


class ScalabilityMode(BaseModel):
    spatialLayers: int
    temporalLayers: int

reg = r'^[LS]([1-9]\\d{0,1})T([1-9]\\d{0,1})'
def parse(scalabilityMode: str) -> ScalabilityMode:
    match = re.match(reg, scalabilityMode)
    if match:
        return ScalabilityMode(
            spatialLayers=int(match[1]),
            temporalLayers=int(match[2])
        )
    else:
        return ScalabilityMode(
            spatialLayers=1,
            temporalLayers=1
        )