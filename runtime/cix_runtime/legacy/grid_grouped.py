"""CIXB21 coordinate-grouped correction PAQ frame from the historical SAO route."""
from __future__ import annotations
import zlib
from . import multinomial
from . import grid_conditional as codec
from ..backends import encode_paq,decode_paq
MAGIC=b"CIXB\x21"
def encode(data,context=3,options="-8"):
 raw,stats=codec.transform(data,context,0)
 if codec.inverse(raw)!=data:raise ValueError("grouped transform inversion failed")
 payload=encode_paq(raw,"v215",options)
 return MAGIC+multinomial.vencode(len(data))+zlib.crc32(data).to_bytes(4,"big")+payload,dict(stats,context=context,options=options)
def decode(frame,max_output_bytes=None,memory_bytes=None):
 if frame[:5]!=MAGIC or max_output_bytes is None or memory_bytes is None:raise ValueError("invalid grouped PAQ frame")
 n,pos=multinomial.vdecode(frame,5)
 if n>max_output_bytes or n>memory_bytes:raise ValueError("grouped output exceeds limit")
 crc=int.from_bytes(frame[pos:pos+4],"big")
 # The conditional transform may be larger than its final source.  Bound the
 # paid intermediate by the caller allocation cap, then verify final length.
 data=codec.inverse(decode_paq(frame[pos+4:],max_output_bytes=memory_bytes,memory_bytes=memory_bytes))
 if len(data)!=n or zlib.crc32(data)!=crc:raise ValueError("grouped PAQ source mismatch")
 return data
