"""Add the verified implicit-width record representation to portfolio 4."""
import sys
import time
from benchmarks import competitive_database_portfolio as parent
from benchmarks import mysql_fixed_columns as fixed

NAME='CIX competitive constrained-grid/database portfolio 5'
SOURCES=[__file__,fixed.__file__]


def additions(data):
    if not parent.recognizes(data):return []
    t=time.perf_counter();frame,_=fixed.encode(data,1)
    return [(frame,dict(name='database-implied-width',size=len(frame),encode_seconds=time.perf_counter()-t))]


def encode(data,**kwargs):
    frame,selection=parent.encode(data,**kwargs)
    for candidate,row in additions(data):
        selection['trials'].append(row)
        if len(candidate)<len(frame):frame=candidate;selection['selected']=row['name']
    return frame,selection


def decode(frame):
    if frame[:5]==fixed.MAGIC:return fixed.decode(frame)
    return parent.decode(frame)


if __name__=='__main__':
    from benchmarks.competitive_additive import main
    main(sys.modules[__name__])
