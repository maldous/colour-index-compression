"""Reversible token/dictionary model for textual CIX blocks.

The model is byte-exact and language-agnostic. It tokenizes ASCII word/identifier runs,
whitespace runs, and individual remaining bytes. Repeated multi-byte tokens are assigned
frequency-ranked IDs. Dictionary bytes, token tags, literal bytes, literal lengths, and
dictionary IDs become separate CIX substreams.
"""
from __future__ import annotations

from collections import Counter

from .multinomial import (
    decode_type_class_known_n,
    encode_type_class_known_n,
    vdecode,
    vencode,
)
from .substreams import decode_uints, encode_uints

TOKEN_VERSION=1

def _word(byte:int)->bool:
    return 48<=byte<=57 or 65<=byte<=90 or 97<=byte<=122 or byte in (95,36)

def _space(byte:int)->bool:
    return byte in (9,10,13,32)

def tokenize(data:bytes)->list[bytes]:
    out=[]; i=0
    while i<len(data):
        b=data[i]
        if _word(b):
            j=i+1
            while j<len(data) and _word(data[j]): j+=1
            out.append(data[i:j]); i=j
        elif _space(b):
            j=i+1
            while j<len(data) and _space(data[j]): j+=1
            out.append(data[i:j]); i=j
        else:
            out.append(data[i:i+1]); i+=1
    return out

def _dictionary(tokens:list[bytes], limit:int=4096)->list[bytes]:
    freq=Counter(tokens)
    scored=[]
    for token,count in freq.items():
        if count<2 or len(token)<2 or len(token)>255:
            continue
        # Conservative physical gain estimate: replace token bytes with ~1-byte ID;
        # charge dictionary bytes and a small length entry.
        gain=count*(len(token)-1)-len(token)-2
        if gain>0:
            scored.append((gain,count,len(token),token))
    scored.sort(key=lambda x:(-x[0],-x[1],-x[2],x[3]))
    chosen=[x[3] for x in scored[:limit]]
    # ID order by decreasing observed frequency makes integer IDs Zipf-friendly.
    chosen.sort(key=lambda t:(-freq[t],-len(t),t))
    return chosen

def encode_token_block(data:bytes)->tuple[bytes,str]:
    tokens=tokenize(data)
    dictionary=_dictionary(tokens)
    if not dictionary:
        raise ValueError("no profitable token dictionary")
    ids={token:i for i,token in enumerate(dictionary)}

    tags=bytearray(); token_ids=[]; literal_lengths=[]; literal_bytes=bytearray()
    for token in tokens:
        token_id=ids.get(token)
        if token_id is None:
            tags.append(0)
            literal_lengths.append(len(token)-1)
            literal_bytes+=token
        else:
            tags.append(1)
            token_ids.append(token_id)

    dict_lengths=encode_uints([len(t)-1 for t in dictionary])
    dict_bytes_raw=b"".join(dictionary)
    dict_bytes=encode_type_class_known_n(dict_bytes_raw)

    tag_blob=encode_type_class_known_n(bytes(tags))
    id_blob=encode_uints(token_ids)
    literal_len_blob=encode_uints(literal_lengths)
    literal_blob=encode_type_class_known_n(bytes(literal_bytes))

    out=bytearray((TOKEN_VERSION,))
    out+=vencode(len(tokens))+vencode(len(dictionary))
    out+=vencode(len(token_ids))+vencode(len(literal_lengths))+vencode(len(literal_bytes))
    for stream in (dict_lengths,dict_bytes,tag_blob,id_blob,literal_len_blob,literal_blob):
        out+=vencode(len(stream)); out+=stream
    return bytes(out),f"tokens-d{len(dictionary)}"

def decode_token_block(blob:bytes,*,source_length:int)->bytes:
    if not blob or blob[0]!=TOKEN_VERSION:
        raise ValueError("unknown token block version")
    pos=1
    token_count,pos=vdecode(blob,pos)
    dictionary_count,pos=vdecode(blob,pos)
    id_count,pos=vdecode(blob,pos)
    literal_count,pos=vdecode(blob,pos)
    literal_bytes_count,pos=vdecode(blob,pos)

    streams=[]
    for _ in range(6):
        length,pos=vdecode(blob,pos); end=pos+length
        if end>len(blob): raise ValueError("truncated token substream")
        streams.append(blob[pos:end]); pos=end
    if pos!=len(blob): raise ValueError("trailing token bytes")

    dict_lengths=[x+1 for x in decode_uints(streams[0],dictionary_count)]
    dict_total=sum(dict_lengths)
    dict_raw,used=decode_type_class_known_n(streams[1],0,dict_total)
    if used!=len(streams[1]): raise ValueError("unused dictionary bytes")
    dictionary=[]; p=0
    for length in dict_lengths:
        dictionary.append(dict_raw[p:p+length]); p+=length

    tags,used=decode_type_class_known_n(streams[2],0,token_count)
    if used!=len(streams[2]): raise ValueError("unused token tags")
    token_ids=decode_uints(streams[3],id_count)
    literal_lengths=[x+1 for x in decode_uints(streams[4],literal_count)]
    literals,used=decode_type_class_known_n(streams[5],0,literal_bytes_count)
    if used!=len(streams[5]): raise ValueError("unused literal bytes")

    out=bytearray(); ip=0; lp=0; bp=0
    for tag in tags:
        if tag:
            if ip>=len(token_ids): raise ValueError("token id stream exhausted")
            tid=token_ids[ip]; ip+=1
            if tid>=len(dictionary): raise ValueError("invalid token id")
            out+=dictionary[tid]
        else:
            if lp>=len(literal_lengths): raise ValueError("literal length stream exhausted")
            length=literal_lengths[lp]; lp+=1
            end=bp+length
            if end>len(literals): raise ValueError("literal byte stream exhausted")
            out+=literals[bp:end]; bp=end
    if ip!=len(token_ids) or lp!=len(literal_lengths) or bp!=len(literals):
        raise ValueError("unused token substream data")
    if len(out)!=source_length:
        raise ValueError("token source length mismatch")
    return bytes(out)
