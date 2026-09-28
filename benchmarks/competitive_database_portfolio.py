"""Strictly additive, automatically detected MyISAM constraint portfolio."""
import sys
import time
from benchmarks import competitive_grid_refresh as parent
from benchmarks import mysql_record_constraints as records

NAME='CIX competitive spatial/volume/grid/database portfolio 4'
SOURCES=[__file__,records.__file__]


def recognizes(data):
    if len(data)<256 or data[0] not in (1,3):return False
    rows,columns=records.split(data[:4096])
    return len(columns[0])>=4 and len(columns[0])*10>=len(rows)*9


def additions(data):
    if not recognizes(data):return []
    trials=[]
    for mode in range(5):
        t=time.perf_counter();frame,_=records.encode(data,mode)
        trials.append((frame,dict(name=f'database-constraints-{mode}',size=len(frame),encode_seconds=time.perf_counter()-t)))
    return trials


def encode(data,**kwargs):
    frame,selection=parent.encode(data,**kwargs)
    for candidate,row in additions(data):
        selection['trials'].append(row)
        if len(candidate)<len(frame):frame=candidate;selection['selected']=row['name']
    return frame,selection


def decode(frame):
    if frame[:5]==records.MAGIC:return records.decode(frame)
    return parent.decode(frame)


if __name__=='__main__':
    from benchmarks.competitive_additive import main
    main(sys.modules[__name__])
