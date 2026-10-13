#!/usr/bin/env python3
"""Prepare revision-guarded Cowart text-note updates; no direct canvas I/O."""
import argparse
import copy
import hashlib
import json
import math
from pathlib import Path

OWNER = 'wild-designer'
STAGES = {'brief', 'explore', 'compose', 'refine', 'integrate'}
LABELS = {'proposed': '备选', 'adopted': '已采用', 'superseded': '历史采用'}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def string(value, field, limit=256, empty=False):
    require(isinstance(value, str) and (empty or bool(value.strip()))
            and len(value) <= limit, 'Invalid ' + field)
    return value


def strings(value, field):
    require(isinstance(value, list), field + ' must be an array')
    require(len(value) <= 100, field + ' is too long')
    return list(dict.fromkeys(string(x, field, 500) for x in value))


def unwrap(value):
    require(isinstance(value, dict), 'Expected an object')
    return value.get('structuredContent', value)


def note_id(operation):
    identity = [operation['projectId'], operation['targetId']]
    key = hashlib.sha256(json.dumps(identity, ensure_ascii=False).encode()).hexdigest()[:24]
    return 'shape:wd-' + key


def page_for(store, shape_id):
    seen = set()
    current = shape_id
    while current in store and current not in seen:
        seen.add(current)
        record = store[current]
        if record.get('typeName') == 'page':
            return current
        current = record.get('parentId')
    return None


def normalize_node(raw):
    fields = {'id', 'shapeId', 'label', 'parentNodeId', 'sourceIds', 'referenceIds',
              'intent', 'prompt', 'stage', 'style'}
    require(isinstance(raw, dict) and set(raw) <= fields, 'Unknown node fields')
    node = {key: string(raw.get(key), key, 1200 if key == 'prompt' else 500)
            for key in ['id', 'shapeId', 'label', 'intent', 'prompt', 'stage', 'style']}
    require(node['stage'] in STAGES, 'Invalid node stage')
    node['parentNodeId'] = raw.get('parentNodeId')
    if node['parentNodeId'] is not None:
        string(node['parentNodeId'], 'parentNodeId')
    node['sourceIds'] = strings(raw.get('sourceIds', []), 'sourceIds')
    node['referenceIds'] = strings(raw.get('referenceIds', []), 'referenceIds')
    return node


def validate_nodes(ledger, store):
    nodes = ledger['nodes']
    shapes, labels = set(), set()
    for node_id, node in nodes.items():
        require(node_id == node['id'], 'Node identity mismatch')
        require(node['status'] in LABELS, 'Invalid node status')
        shape = store.get(node['shapeId'], {})
        require(shape.get('typeName') == 'shape' and shape.get('type') == 'image',
                'Candidate image is missing: ' + node['shapeId'])
        require(page_for(store, node['shapeId']) == ledger['pageId'],
                'Candidate belongs to another canvas page')
        provenance = shape.get('meta', {}).get('wildDesigner', {})
        require(all(provenance.get(k) == v for k, v in {
            'projectId': ledger['projectId'], 'targetId': ledger['targetId'],
            'nodeId': node_id}.items()), 'Candidate provenance mismatch')
        require(node['shapeId'] not in shapes and node['label'] not in labels,
                'Duplicate candidate shape or label')
        shapes.add(node['shapeId'])
        labels.add(node['label'])
        for ref in node['sourceIds'] + ([node['parentNodeId']] if node['parentNodeId'] else []):
            require(ref in nodes and ref != node_id, 'Unknown/self source node')
    visiting, visited = set(), set()
    def visit(node_id):
        require(node_id not in visiting, 'Cyclic provenance')
        if node_id in visited:
            return
        visiting.add(node_id)
        node = nodes[node_id]
        for ref in node['sourceIds'] + ([node['parentNodeId']] if node['parentNodeId'] else []):
            visit(ref)
        visiting.remove(node_id)
        visited.add(node_id)
    for node_id in nodes:
        visit(node_id)
    adopted = [key for key, value in nodes.items() if value['status'] == 'adopted']
    require(adopted == ([ledger['mainNodeId']] if ledger['mainNodeId'] else []),
            'Main image and adopted status disagree')


def note_text(ledger):
    nodes = ledger['nodes']
    main = nodes.get(ledger['mainNodeId'], {}).get('label', '尚未采用')
    lines = [ledger['title'] + ' · Wild Designer',
             '原意：' + str(ledger['brief'].get('originalIntent', '待明确')),
             '阶段：' + ledger['stage'] + '　方向：' + (ledger['chosenStyle'] or '待选择'),
             '当前主稿：' + main]
    if ledger['constraints']:
        lines.append('保留：' + '；'.join(ledger['constraints']))
    for node in nodes.values():
        sources = list(dict.fromkeys(
            ([node['parentNodeId']] if node['parentNodeId'] else []) + node['sourceIds']))
        origin = ' + '.join(nodes[key]['label'] for key in sources)
        lines.append(node['label'] + ' · ' + LABELS[node['status']] + ' · ' + node['intent'])
        lines.append(('来源：' + origin + ' → ' + node['label'] if origin else '起始候选')
                     + '　图片：' + node['shapeId'])
    lines.append('下一步：' + (ledger['nextDecision'] or '等待用户决定'))
    return {'type': 'doc', 'content': [
        {'type': 'paragraph', 'content': [{'type': 'text', 'text': line}]}
        for line in lines]}


def plan(state, operation):
    state = unwrap(state)
    require(isinstance(operation, dict), 'Expected operation object')
    allowed = {'projectId', 'targetId', 'pageId', 'title', 'brief', 'stage', 'chosenStyle',
               'constraints', 'nextDecision', 'notePosition', 'nodes', 'adopt'}
    require(set(operation) <= allowed, 'Unknown operation fields')
    for key in ['projectId', 'targetId', 'pageId']:
        string(operation.get(key), key)
    revision = string(state.get('revision'), 'current revision')
    snapshot = state.get('snapshot')
    require(isinstance(snapshot, dict) and snapshot.get('schema')
            and isinstance(snapshot.get('store'), dict), 'Read a full current snapshot first')
    result = copy.deepcopy(snapshot)
    store = result['store']
    require(store.get(operation['pageId'], {}).get('typeName') == 'page', 'Unknown page')
    identity = note_id(operation)
    existing = store.get(identity)
    if existing is not None:
        ledger = existing.get('meta', {}).get('wildDesigner', {})
        require(existing.get('type') == 'text' and ledger.get('owner') == OWNER
                and ledger.get('schemaVersion') == 1, 'Note ID collision or unsupported schema')
        require(all(ledger.get(key) == operation[key] for key in ['projectId', 'targetId', 'pageId'])
                and existing.get('parentId') == operation['pageId'], 'Target/page identity changed')
        ledger = copy.deepcopy(ledger)
    else:
        ledger = {'owner': OWNER, 'schemaVersion': 1,
                  **{key: operation[key] for key in ['projectId', 'targetId', 'pageId']},
                  'title': operation.get('title', operation['targetId']), 'brief': {},
                  'stage': 'brief', 'chosenStyle': '', 'constraints': [], 'nextDecision': '',
                  'mainNodeId': None, 'nodes': {}, 'decisions': []}
    for key in ['title', 'stage', 'chosenStyle', 'nextDecision']:
        if key in operation:
            ledger[key] = string(operation[key], key, 1000, key in ['chosenStyle', 'nextDecision'])
    require(ledger['stage'] in STAGES, 'Unknown stage')
    if 'constraints' in operation:
        ledger['constraints'] = strings(operation['constraints'], 'constraints')
    if 'brief' in operation:
        require(isinstance(operation['brief'], dict), 'brief must be an object')
        old = ledger['brief'].get('originalIntent')
        require(old is None or operation['brief'].get('originalIntent', old) == old,
                'Preserve originalIntent; put revised intent in a separate brief field')
        ledger['brief'].update(copy.deepcopy(operation['brief']))
    raw_nodes = operation.get('nodes', [])
    require(isinstance(raw_nodes, list), 'nodes must be an array')
    for raw in raw_nodes:
        node = normalize_node(raw)
        previous = ledger['nodes'].get(node['id'])
        if previous:
            require({k: v for k, v in previous.items() if k != 'status'} == node,
                    'Existing candidate provenance is immutable')
        else:
            ledger['nodes'][node['id']] = {**node, 'status': 'proposed'}
    validate_nodes(ledger, store)
    if 'adopt' in operation:
        adopt = operation['adopt']
        require(isinstance(adopt, dict) and set(adopt) == {'nodeId', 'userSelection'},
                'Adoption requires an explicit nodeId and userSelection')
        node_id = string(adopt['nodeId'], 'adopt.nodeId')
        selection = string(adopt['userSelection'], 'actual user selection', 1000)
        require(node_id in ledger['nodes'], 'Adoption target not in this target/page')
        previous = ledger['mainNodeId']
        if previous != node_id:
            if previous:
                ledger['nodes'][previous]['status'] = 'superseded'
            ledger['nodes'][node_id]['status'] = 'adopted'
            ledger['mainNodeId'] = node_id
            ledger['decisions'].append({'from': previous, 'to': node_id, 'userSelection': selection})
    validate_nodes(ledger, store)
    rich_text = note_text(ledger)
    if existing is not None:
        require(isinstance(existing.get('props'), dict), 'Invalid existing text props')
        existing['props']['richText'] = rich_text
        existing['meta']['wildDesigner'] = ledger
    else:
        position = operation.get('notePosition', {})
        require(all(isinstance(position.get(k), (int, float))
                    and not isinstance(position[k], bool) and math.isfinite(position[k])
                    for k in ['x', 'y']), 'Choose a clear notePosition before creating a note')
        indices = {r.get('index') for r in store.values() if r.get('parentId') == operation['pageId']}
        index = 'a1'
        while index in indices:
            index += 'V'  # Valid base-62 fractional suffix, never a trailing zero.
        store[identity] = {
            'id': identity, 'typeName': 'shape', 'type': 'text',
            'parentId': operation['pageId'], 'x': position['x'], 'y': position['y'],
            'rotation': 0, 'index': index, 'isLocked': False, 'opacity': 1,
            'props': {'color': 'black', 'size': 's', 'w': 720, 'font': 'sans',
                      'textAlign': 'start', 'autoSize': False, 'scale': 1, 'richText': rich_text},
            'meta': {'wildDesigner': ledger},
        }
    # The helper can only create/update one owned text record, never images/assets/pages.
    require(all(store[key] == value for key, value in snapshot['store'].items() if key != identity),
            'Unrelated record changed')
    args = {'snapshot': result, 'expectedRevision': revision, 'protectImageRecords': True}
    for key in ['projectDir', 'canvasDir']:
        if key in state:
            string(state[key], key, 4096)
            require(Path(state[key]).is_absolute(), 'Storage paths must be absolute')
            args[key] = state[key]
    require('projectDir' in args or 'canvasDir' in args, 'Missing returned canvas storage path')
    return args


def verify(planned, operation, receipt, readback):
    require(not receipt.get('isError'), 'Cowart returned an error')
    receipt, readback = unwrap(receipt), unwrap(readback)
    require(receipt.get('ok') is True and not receipt.get('skippedRecords'),
            'Save failed or skipped records; do not claim success')
    require(bool(readback.get('revision')), 'Missing readback revision')
    expected = planned['snapshot']['store']
    actual = readback.get('snapshot', {}).get('store', {})
    identity = note_id(operation)
    require(actual.get(identity) == expected.get(identity) and identity in actual,
            'Owned note readback mismatch; reread before another operation')
    require(set(expected) <= set(actual), 'Records missing from readback; inspect without rollback')
    return {'ok': True, 'noteId': identity, 'revision': readback['revision']}


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    prepare = sub.add_parser('plan')
    for name in ['state', 'operation', 'out']:
        prepare.add_argument('--' + name, required=True)
    check = sub.add_parser('verify')
    for name in ['plan', 'operation', 'receipt', 'readback']:
        check.add_argument('--' + name, required=True)
    args = parser.parse_args()
    try:
        if args.command == 'plan':
            output = plan(read(args.state), read(args.operation))
            # Exclusive creation prevents overwriting a user's existing file.
            with Path(args.out).open('x', encoding='utf-8') as stream:
                json.dump(output, stream, ensure_ascii=False, indent=2, allow_nan=False)
            print(json.dumps({'prepared': True, 'noteId': note_id(read(args.operation))}))
        else:
            print(json.dumps(verify(read(args.plan), read(args.operation),
                                    read(args.receipt), read(args.readback))))
    except (ValueError, KeyError, TypeError, OSError) as error:
        parser.exit(1, 'Refused: ' + str(error) + '\n')


if __name__ == '__main__':
    main()
