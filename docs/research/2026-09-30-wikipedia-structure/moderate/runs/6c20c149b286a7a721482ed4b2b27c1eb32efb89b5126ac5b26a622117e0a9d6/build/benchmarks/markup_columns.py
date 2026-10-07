"""Byte-exact markup field conditioning; column order is explicit and paid.

Recognized tags supply context labels. Opaque or malformed content remains
literal. Decoding is a framed byte operation, not an XML/HTML reserialization.
"""
import re
from cix.multinomial import vencode,vdecode

MAGIC=b'CIXV\x01'
TOKEN=re.compile(br'<!--.*?-->|<!\[CDATA\[.*?\]\]>|<\?.*?\?>|</?[A-Za-z_:][A-Za-z0-9_.:-]*(?:[^<>\x22\x27]|\x22[^\x22]*\x22|\x27[^\x27]*\x27)*>',re.S)
NAME=re.compile(br'</?([A-Za-z_:][A-Za-z0-9_.:-]*)')
STACK_MAGIC=b'CIXV\x02'
STACK_TOKEN=re.compile(TOKEN.pattern+br'|\x00[\x00\x01]',re.S)
TEXT_STACK_MAGIC=b'CIXV\x03'
TEXT_STACK_TOKEN=re.compile(TOKEN.pattern+br'|</!*>',re.S)
TEXT_ESCAPE=re.compile(br'</(!*)>')


def update_stack(stack,token):
    name=NAME.match(token)
    if not name:return
    tag=name.group(1)
    if token.startswith(b'</'):
        if tag in stack:
            index=len(stack)-1-stack[::-1].index(tag);del stack[index:]
    elif not token.rstrip().endswith(b'/>'):stack.append(tag)


def encode_stack(data,text=False):
    stack=[];out=bytearray((TEXT_STACK_MAGIC if text else STACK_MAGIC)+vencode(len(data)));at=0;forced=0;removed=0
    def literal(value):
        out.extend(TEXT_ESCAPE.sub(lambda m:b'</!'+m.group(1)+b'>',value) if text else value.replace(b'\0',b'\0\0'))
    for match in TOKEN.finditer(data):
        literal(data[at:match.start()]);token=match.group();at=match.end()
        if stack and token==b'</'+stack[-1]+b'>':
            marker=b'</>' if text else b'\0\1';out.extend(marker);forced+=1;removed+=len(token)-len(marker);stack.pop()
        else:
            if text:out.extend(token)
            else:literal(token)
            update_stack(stack,token)
    literal(data[at:])
    return bytes(out),dict(mode=4 if text else 3,original_bytes=len(data),transformed_bytes=len(out),
        forced_closing_tags=forced,removed_tag_bytes=removed)


def decode_stack(blob):
    n,pos=vdecode(blob,5);data=blob[pos:];out=bytearray();at=0;stack=[];text=blob[:5]==TEXT_STACK_MAGIC
    for match in (TEXT_STACK_TOKEN if text else STACK_TOKEN).finditer(data):
        gap=data[at:match.start()];out.extend(gap if text else gap.replace(b'\0\0',b'\0'));token=match.group();at=match.end()
        if token==(b'</>' if text else b'\0\1'):
            if not stack:raise ValueError('closing-tag stack exhausted')
            out.extend(b'</'+stack.pop()+b'>')
        elif text and TEXT_ESCAPE.fullmatch(token):out.extend(b'</'+token[3:])
        elif not text and token==b'\0\0':out.append(0)
        else:
            if not text:token=token.replace(b'\0\0',b'\0')
            out.extend(token);update_stack(stack,token)
    out.extend(data[at:] if text else data[at:].replace(b'\0\0',b'\0'))
    if len(out)!=n:raise ValueError('tag-stack reconstruction length mismatch')
    return bytes(out)


def encode(data,mode=1,repeat=True):
    if mode==3:return encode_stack(data)
    if mode==4:return encode_stack(data,True)
    if mode not in (1,2):raise ValueError('unknown markup grouping')
    stack=[];groups={};columns=[];previous=[];skeleton=bytearray();at=0;fields=0;repeated=0;lifted=0
    def literal(value):skeleton.extend(value.replace(b'\0',b'\0\0'))
    def gap(value):
        nonlocal fields,repeated,lifted
        if not stack or not value.strip() or b'\0' in value:literal(value);return
        key=stack[-1] if mode==1 else tuple(stack)
        if key not in groups:groups[key]=len(columns);columns.append(bytearray());previous.append(None)
        group=groups[key];fields+=1;lifted+=len(value)
        if repeat and previous[group]==value:skeleton.extend(b'\0\2'+vencode(group));repeated+=1
        else:
            skeleton.extend(b'\0\1'+vencode(group)+vencode(len(value)));columns[group].extend(value);previous[group]=value
    for match in TOKEN.finditer(data):
        gap(data[at:match.start()]);token=match.group();literal(token);at=match.end()
        update_stack(stack,token)
    gap(data[at:])
    out=bytearray(MAGIC+bytes([mode,int(repeat)])+vencode(len(data))+vencode(len(skeleton))+skeleton+vencode(len(columns)))
    for column in columns:out.extend(vencode(len(column)));out.extend(column)
    return bytes(out),dict(mode=mode,repeat=repeat,groups=len(columns),fields=fields,repeated_fields=repeated,
        lifted_bytes=lifted,column_bytes=sum(map(len,columns)),skeleton_bytes=len(skeleton),
        transformed_bytes=len(out),original_bytes=len(data))


def decode(blob):
    if blob[:5] in (STACK_MAGIC,TEXT_STACK_MAGIC):return decode_stack(blob)
    if len(blob)<7 or blob[:5]!=MAGIC or blob[5] not in (1,2) or blob[6] not in (0,1):raise ValueError('invalid markup frame')
    n,pos=vdecode(blob,7);ns,pos=vdecode(blob,pos);skeleton=blob[pos:pos+ns];pos+=ns
    if len(skeleton)!=ns:raise ValueError('truncated skeleton')
    count,pos=vdecode(blob,pos);columns=[]
    for _ in range(count):
        size,pos=vdecode(blob,pos);column=blob[pos:pos+size];pos+=size
        if len(column)!=size:raise ValueError('truncated column')
        columns.append(column)
    if pos!=len(blob):raise ValueError('trailing column bytes')
    positions=[0]*count;previous=[None]*count;out=bytearray();pos=0
    while pos<len(skeleton):
        value=skeleton[pos];pos+=1
        if value:out.append(value);continue
        if pos>=len(skeleton):raise ValueError('truncated skeleton escape')
        kind=skeleton[pos];pos+=1
        if kind==0:out.append(0);continue
        if kind not in (1,2):raise ValueError('invalid skeleton escape')
        group,pos=vdecode(skeleton,pos)
        if group>=count:raise ValueError('unknown column')
        if kind==2:
            if not blob[6] or previous[group] is None:raise ValueError('invalid repeated field')
            out.extend(previous[group]);continue
        size,pos=vdecode(skeleton,pos);start=positions[group];value=columns[group][start:start+size]
        if len(value)!=size:raise ValueError('column exhausted')
        positions[group]+=size;previous[group]=value;out.extend(value)
    if len(out)!=n or any(pos!=len(column) for pos,column in zip(positions,columns)):raise ValueError('markup reconstruction length mismatch')
    return bytes(out)
