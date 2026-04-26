import numpy as np
from pathlib import Path
import sys

home = Path(__file__).parent.parent.parent
sys.path.insert(0, str(home))

from kriegsspiel.engine import state
from kriegsspiel.scenarios.latgale_2027 import build_latgale_world



w = build_latgale_world()
w.compute_visibilities()
for unit in w.units.values():
    print(unit.observes)




# from 
