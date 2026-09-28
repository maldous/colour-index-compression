"""Extend the independently measured PAQ compute tier from 12 to 24 MiB."""
import sys
import time
from benchmarks import competitive_hydrogen as parent
from benchmarks import competitive_small_paq as reference
from benchmarks import competitive_database_portfolio as database
from benchmarks.competitive_codec import encode_paq

NAME='CIX competitive PAQ/structural constraint portfolio 10'
SOURCES=[__file__]


def eligible(data):
    return reference.MAX_BYTES<len(data)<=2*reference.MAX_BYTES and not database.recognizes(data)


def additions(data,cache=None):
    if not eligible(data):return []
    t=time.perf_counter();proof=None
    if cache:frame,proof=reference.qualify(data,cache)
    else:frame=encode_paq(data,'v216','-8')
    return [(frame,dict(name='paq-v216-8-12to24MiB-nondatabase',size=len(frame),encode_seconds=time.perf_counter()-t),proof)]


def encode(data,**kwargs):
    frame,selection=parent.encode(data,**kwargs)
    for candidate,row,_ in additions(data):
        selection['trials'].append(row)
        if len(candidate)<len(frame):frame=candidate;selection['selected']=row['name']
    return frame,selection


def decode(frame):return parent.decode(frame)


if __name__=='__main__':
    from benchmarks.competitive_certified import main
    main(sys.modules[__name__])
