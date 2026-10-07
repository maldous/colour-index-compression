"""Exact forward-transfer adapter for the existing SDF hydrogen constraint stream.

This module adds no molecular dictionary, learned state or filename recognition.
It makes the existing model-2 / representation-0 stream auditable on another
SDF source and reports every byte category already present in that stream.
"""
from __future__ import annotations

from benchmarks import sdf_hydrogen
from cix.multinomial import vdecode


VARIANT="hydrogen_slots_v1"
POLICY={"model":2,"representation":0,"radius":6200,"state":"empty per supplied input","backend":"NOT_RUN"}

def _parts(frame:bytes)->dict:
    if not frame.startswith(sdf_hydrogen.MAGIC):raise ValueError("invalid hydrogen frame")
    model,representation=frame[5:7];pos=7
    radius_start=pos;radius,pos=vdecode(frame,pos);radius_end=pos
    records_start=pos;records,pos=vdecode(frame,pos);records_end=pos
    flags_bytes=(records+7)//8;flags=frame[pos:pos+flags_bytes];pos+=flags_bytes
    if len(flags)!=flags_bytes:raise ValueError("truncated record flags")
    skeleton_length_start=pos;skeleton_len,pos=vdecode(frame,pos);skeleton_start=pos;pos+=skeleton_len
    if pos>len(frame):raise ValueError("truncated skeleton")
    choices_length_start=pos;choices_len,pos=vdecode(frame,pos);choices_start=pos;pos+=choices_len
    if pos>len(frame):raise ValueError("truncated choices")
    parsed=sum((flags[index//8]>>(index%8))&1 for index in range(records))
    result={"header_bytes":7,"radius_varint_bytes":radius_end-radius_start,"record_count_varint_bytes":records_end-records_start,
            "model":model,"representation":representation,"radius":radius,"record_count":records,"record_flag_bytes":flags_bytes,
            "record_flag_padding_bits":flags_bytes*8-records,"parsed_records":parsed,"literal_records":records-parsed,
            "skeleton_length_varint_bytes":skeleton_start-skeleton_length_start,"skeleton_bytes":skeleton_len,
            "choice_length_varint_bytes":choices_start-choices_length_start,
            "choice_payload_bytes":choices_len,"residual_payload_bytes":len(frame)-pos,"physical_bytes":len(frame)}
    result["component_sum_bytes"]=sum(result[key] for key in ("header_bytes","radius_varint_bytes","record_count_varint_bytes","record_flag_bytes","skeleton_length_varint_bytes","skeleton_bytes","choice_length_varint_bytes","choice_payload_bytes","residual_payload_bytes"))
    if result["component_sum_bytes"]!=len(frame):raise AssertionError("molecular frame accounting mismatch")
    return result

def inspect(data:bytes)->dict:
    """Return diagnostics; no entropy backend or packing ablation is run."""
    frame,stats=sdf_hydrogen.encode(data,**{key:value for key,value in POLICY.items() if key in ("model","representation","radius")})
    if sdf_hydrogen.decode(frame)!=data:raise AssertionError("molecular adapter round trip failed")
    accounting=_parts(frame)
    # The parser's exact `$$$$\n` split retains a trailing empty record.  It is
    # deliberately paid in count/flags/body instead of being normalized away.
    accounting["termination_policy"]="record separators and trailing empty records are retained inside the paid skeleton"
    accounting["packing_slack"]={"record_flag_padding_bits":accounting["record_flag_padding_bits"],"choice_rank_padding_bits":0,
                                "note":"representation 0 writes one byte per nontrivial choice; no rank-byte padding is claimed"}
    accounting["paq_sharing_boundary"]="PAQ may discover repeated skeleton/residual text only after this complete frame; this adapter adds no separate dictionary sharing"
    return {"variant":VARIANT,"policy":POLICY,**stats,"accounting":accounting}

def encode(data:bytes,variant:str=VARIANT)->bytes:
    """Produce the complete self-contained structural frame for a fixed variant."""
    if variant!=VARIANT:raise ValueError("unknown molecular structural variant")
    frame,_=sdf_hydrogen.encode(data,**{key:value for key,value in POLICY.items() if key in ("model","representation","radius")})
    return frame

def decode(frame:bytes)->bytes:
    return sdf_hydrogen.decode(frame)
