#!/usr/bin/env python3
"""Wikipedia field columns with matched raw/arithmetic/rank block representations."""
from __future__ import annotations
from collections import defaultdict
from benchmarks import hutter_structure_columns as structure
from benchmarks import hutter_wikipedia_column_coding as coding
from cix.multinomial import vencode, vdecode

MAGIC = b'HWC1\0'
MODES = ('raw', 'remaining', 'rank')
BLOCK = 1024
pack = structure._pack_stream
read = structure._read_stream


def column_frame(column, requested):
    values = column['values']; blocks = []
    out = bytearray(vencode((len(values) + BLOCK - 1) // BLOCK))
    for start in range(0, len(values), BLOCK):
        block = values[start:start+BLOCK]
        effective = requested if column['eligible_short_field'] else 'raw'
        encoded, stats = coding.encode(block, effective)
        out.extend(vencode(len(block))); out.extend(pack(encoded))
        blocks.append(stats)
    frame = (vencode(column['skeleton_id']) + vencode(column['slot_ordinal']) +
             vencode(len(values)) + pack(bytes(out)))
    return frame, blocks


def assemble(original, descriptor, dictionary, literal, columns, mode):
    return (MAGIC + bytes([MODES.index(mode)]) + vencode(original) + pack(descriptor) +
            pack(dictionary) + pack(literal) + pack(columns))


def encode(data, mode='raw'):
    if mode not in MODES: raise ValueError('invalid column policy')
    parts = structure.extract_columns(data)
    column_bytes = bytearray(vencode(len(parts['columns'])))
    actual_blocks = defaultdict(int)
    for column in parts['columns']:
        frame, blocks = column_frame(column, mode)
        column_bytes.extend(frame)
        for block in blocks: actual_blocks[block['actual_mode']] += 1
    frame = assemble(len(data), parts['descriptor'], parts['dictionary'], parts['literal_exceptions'], bytes(column_bytes), mode)
    costs = dict(descriptor_bytes=len(parts['descriptor']), dictionary_bytes=len(parts['dictionary']),
                 literal_bytes=len(parts['literal_exceptions']), column_stream_bytes=len(column_bytes))
    costs['framing_bytes'] = len(frame)-sum(costs.values())
    assert sum(costs.values()) == len(frame)
    return frame, dict(physical_bytes=len(frame), **costs, mode=mode,
                       pages=parts['pages'], skeletons=parts['skeletoncount'], slot_columns=parts['slotcolumns'],
                       actual_blocks=dict(actual_blocks), initial_state='empty; fixed 1024-value blocks')


def decode(blob):
    if not blob.startswith(MAGIC) or len(blob)<=len(MAGIC) or blob[len(MAGIC)]>=len(MODES):
        raise ValueError('invalid Wikipedia column frame')
    original, pos = vdecode(blob,len(MAGIC)+1)
    descriptor,pos=read(blob,pos); dictionary,pos=read(blob,pos); literal,pos=read(blob,pos); table,pos=read(blob,pos)
    if pos!=len(blob): raise ValueError('trailing Wikipedia frame')
    skeletons=structure.d1._deserialize_skeletons(dictionary)
    page_counts=structure._page_counts(descriptor,skeletons)
    expected={(sid,slot):count for sid,count in page_counts.items() for slot in range(structure.d1._placeholder_count(skeletons[sid]))}
    count, at=vdecode(table,0)
    if count!=len(expected) or count>structure.MAX_COLUMNS: raise ValueError('column count mismatch')
    raw_table=bytearray(vencode(count)); seen=set()
    for _ in range(count):
        sid,at=vdecode(table,at); slot,at=vdecode(table,at); n,at=vdecode(table,at); content,at=read(table,at)
        key=sid,slot
        if key in seen or key not in expected or n!=expected[key]: raise ValueError('invalid column declaration')
        seen.add(key)
        block_count,p=vdecode(content,0)
        if block_count!=(n+BLOCK-1)//BLOCK: raise ValueError('invalid block count')
        values=[]
        for block_index in range(block_count):
            size,p=vdecode(content,p); frame,p=read(content,p)
            if size!=min(BLOCK,n-block_index*BLOCK): raise ValueError('invalid block size')
            values.extend(coding.decode(frame,size))
        if p!=len(content) or len(values)!=n: raise ValueError('column blocks mismatch')
        raw_values=b''.join(pack(value) for value in values)
        raw_table.extend(vencode(sid)+vencode(slot)+vencode(n)+pack(raw_values))
    if at!=len(table) or set(expected)!=seen: raise ValueError('invalid column table end')
    restored=structure._decode_parts(descriptor,dictionary,literal,bytes(raw_table))
    if len(restored)!=original: raise ValueError('restored length mismatch')
    return restored


def profile(data):
    parts=structure.extract_columns(data); classes={}; details=[]
    for column in parts['columns']:
        kind=column['field_class']
        row=classes.setdefault(kind,dict(field_class=kind,original_value_bytes=0,value_count=0,values=set(),within_column_repeated_occurrences=0,complete_column_bytes={mode:0 for mode in MODES}))
        row['original_value_bytes']+=sum(map(len,column['values']))
        row['value_count']+=len(column['values']); row['values'].update(column['values'])
        row['within_column_repeated_occurrences']+=len(column['values'])-len(set(column['values']))
        item={k:v for k,v in column.items() if k!='values'}; item['candidates']={}
        for mode in MODES:
            frame,blocks=column_frame(column,mode)
            row['complete_column_bytes'][mode]+=len(frame)
            item['candidates'][mode]=dict(complete_bytes=len(frame),blocks=blocks)
        details.append(item)
    rows=[]
    for kind,row in sorted(classes.items()):
        unique=row.pop('values'); row['distinct_values_within_class']=len(unique)
        row['class_repeated_occurrences']=row['value_count']-len(unique)
        row['input_byte_share_percent']=100*row['original_value_bytes']/len(data) if data else 0
        rows.append(row)
    residual=len(data)-sum(row['original_value_bytes'] for row in rows)
    shared={}
    for mode in MODES:
        column_bytes=vencode(len(parts['columns']))+b''.join(column_frame(col,mode)[0] for col in parts['columns'])
        frame=assemble(len(data),parts['descriptor'],parts['dictionary'],parts['literal_exceptions'],column_bytes,mode)
        shared[mode]=len(frame)-sum(row['complete_column_bytes'][mode] for row in rows)
    return dict(input_bytes=len(data),field_classes=rows,shared_structure_and_literal_original_bytes=residual,
                shared_structure_and_literal_encoded_bytes=shared,columns=details,
                note='All encoded costs are complete pre-PAQ transform costs. Joint PAQ bytes are measured only for the full stream; field costs are not post-PAQ attributions. No metadata cost is omitted.')
