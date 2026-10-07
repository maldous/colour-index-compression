"""Prospective shared-symbol constraints + native PAQ portfolio extension."""
import sys
from benchmarks import competitive_filtered as parent, qualified_structural_paq as native

NAME='CIX competitive native-PAQ shared-symbol portfolio'
SOURCES=[__file__,*native.SOURCES]


def additions(data,cache=None): return native.addition(data,cache,'got',3)


def encode(data,**kwargs):
    frame,selection=parent.encode(data,**kwargs)
    for candidate,row,_ in additions(data):
        selection['trials'].append(row)
        if len(candidate)<len(frame):frame=candidate;selection['selected']=row['name']
    return frame,selection


def decode(frame):
    return native.got.decode(frame) if frame[:5]==native.got.MAGIC else parent.decode(frame)


if __name__=='__main__':
    from benchmarks.competitive_certified import main
    main(sys.modules[__name__])
