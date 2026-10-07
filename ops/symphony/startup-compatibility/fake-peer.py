#!/usr/bin/python3
"""Offline protocol peer; no model, provider, network or product worker."""
import json
import sys
from pathlib import Path

import jsonschema

schema = json.loads(Path('/home/user/src/cix-approved-migration/inventory/codex-01601-schema/v2/ThreadStartParams.json').read_text())
for line in sys.stdin:
    request = json.loads(line)
    method = request.get('method')
    if method == 'initialize':
        response = {'id': request['id'], 'result': {}}
    elif method == 'thread/start':
        errors = list(jsonschema.Draft7Validator(schema).iter_errors(request['params']))
        response = {'id': request['id'], 'error': {'code': -32602, 'message': 'synthetic-private-error'}} if errors else {'id': request['id'], 'result': {'thread': {'id': 'offline-focused-thread'}}}
    else:
        continue
    print(json.dumps(response), flush=True)
