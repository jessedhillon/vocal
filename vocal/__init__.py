from pathlib import Path


parent = Path(__file__).parent.parent.absolute()
vp = parent / 'VERSION'
with vp.open('r') as f:
    __version__ = f.read().strip()
