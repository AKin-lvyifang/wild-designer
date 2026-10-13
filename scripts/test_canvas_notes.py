"""Synthetic contract tests. No real artwork, MCP, network, or image generation."""
import copy
import unittest
from canvas_notes import note_id, plan, verify


def fixture():
    state = {'projectDir': '/tmp/wild-designer-test', 'revision': 'r1',
             'snapshot': {'schema': {'schemaVersion': 2}, 'store': {
                 'page:one': {'id': 'page:one', 'typeName': 'page'},
                 'page:two': {'id': 'page:two', 'typeName': 'page'},
                 'shape:unrelated': {'id': 'shape:unrelated', 'typeName': 'shape',
                                     'type': 'draw', 'meta': {'user': 'keep'},
                                     'props': {'segments': [1, 2, 3]}}
             }}}
    operation = {'projectId': 'project-one', 'targetId': 'home', 'pageId': 'page:one',
                 'title': '首页', 'notePosition': {'x': 1000, 'y': 40},
                 'brief': {'originalIntent': '温暖、有手作感'}, 'nodes': []}
    return state, operation


def add_candidate(state, operation, number, parent=None):
    node_id, shape_id = 'node-' + str(number), 'shape:' + str(number)
    state['snapshot']['store'][shape_id] = {
        'id': shape_id, 'typeName': 'shape', 'type': 'image',
        'parentId': operation['pageId'], 'props': {'assetId': 'asset:' + str(number)},
        'x': number * 200, 'index': 'a1',
        'meta': {'unrelated': 'preserve', 'wildDesigner': {
            'projectId': operation['projectId'], 'targetId': operation['targetId'],
            'nodeId': node_id}}}
    state['snapshot']['store']['asset:' + str(number)] = {
        'typeName': 'asset', 'props': {'src': '/synthetic/image.png'}}
    node = {'id': node_id, 'shapeId': shape_id, 'label': 'v' + str(number),
            'intent': '增加留白', 'prompt': '完整首页，保留品牌蓝', 'stage': 'compose',
            'style': '编辑排版', 'sourceIds': [parent] if parent else [],
            'parentNodeId': parent, 'referenceIds': ['attachment:reference-one']}
    operation['nodes'].append(node)
    return node_id


def apply(state, operation):
    prepared = plan(state, operation)
    return {**state, 'snapshot': prepared['snapshot'], 'revision': 'r2'}, prepared


class NotesTests(unittest.TestCase):
    def test_preserve_every_unrelated_record_and_input(self):
        state, operation = fixture()
        add_candidate(state, operation, 1)
        before = copy.deepcopy(state)
        prepared = plan(state, operation)
        self.assertEqual(state, before)
        for key, record in before['snapshot']['store'].items():
            self.assertEqual(prepared['snapshot']['store'][key], record)
        self.assertEqual(prepared['expectedRevision'], 'r1')
        self.assertTrue(prepared['protectImageRecords'])

    def test_repeat_invocation_is_idempotent(self):
        state, operation = fixture()
        add_candidate(state, operation, 1)
        current, first = apply(state, operation)
        self.assertEqual(plan(current, operation)['snapshot'], first['snapshot'])

    def test_preserve_user_note_position_and_other_meta(self):
        state, operation = fixture()
        state, _ = apply(state, operation)
        record = state['snapshot']['store'][note_id(operation)]
        record['x'] = 9000
        record['meta']['userLabel'] = '我的备注'
        operation['nextDecision'] = '选字体'
        output = plan(state, operation)['snapshot']['store'][note_id(operation)]
        self.assertEqual(output['x'], 9000)
        self.assertEqual(output['meta']['userLabel'], '我的备注')

    def test_adoption_and_historical_status(self):
        state, operation = fixture()
        add_candidate(state, operation, 1)
        add_candidate(state, operation, 2, 'node-1')
        operation['adopt'] = {'nodeId': 'node-1', 'userSelection': '首页采用第一版'}
        state, _ = apply(state, operation)
        operation['adopt'] = {'nodeId': 'node-2', 'userSelection': '首页采用第二版'}
        state, prepared = apply(state, operation)
        ledger = prepared['snapshot']['store'][note_id(operation)]['meta']['wildDesigner']
        self.assertEqual(ledger['mainNodeId'], 'node-2')
        self.assertEqual(ledger['nodes']['node-1']['status'], 'superseded')
        self.assertEqual(ledger['nodes']['node-2']['status'], 'adopted')
        self.assertEqual(len(ledger['decisions']), 2)
        self.assertEqual(plan(state, operation)['snapshot'], prepared['snapshot'])

    def test_new_branch_preserves_main_and_first_version_parent(self):
        state, operation = fixture()
        add_candidate(state, operation, 1)
        add_candidate(state, operation, 2, 'node-1')
        operation['adopt'] = {'nodeId': 'node-2', 'userSelection': '采用第二版'}
        state, _ = apply(state, operation)
        del operation['adopt']
        add_candidate(state, operation, 3, 'node-1')
        prepared = plan(state, operation)
        ledger = prepared['snapshot']['store'][note_id(operation)]['meta']['wildDesigner']
        self.assertEqual(ledger['mainNodeId'], 'node-2')
        self.assertEqual(ledger['nodes']['node-3']['status'], 'proposed')
        self.assertEqual(ledger['nodes']['node-3']['parentNodeId'], 'node-1')
        self.assertEqual(ledger['nodes']['node-3']['referenceIds'], ['attachment:reference-one'])

    def test_refuse_implicit_adoption(self):
        state, operation = fixture()
        add_candidate(state, operation, 1)
        operation['adopt'] = {'nodeId': 'node-1'}
        with self.assertRaises(ValueError):
            plan(state, operation)

    def test_refuse_cross_page_or_wrong_provenance(self):
        for key, value in [('parentId', 'page:two'), ('meta', {})]:
            state, operation = fixture()
            add_candidate(state, operation, 1)
            state['snapshot']['store']['shape:1'][key] = value
            with self.assertRaises(ValueError):
                plan(state, operation)

    def test_refuse_collision_revisionless_and_unknown_source(self):
        for scenario in ['collision', 'revision', 'source']:
            state, operation = fixture()
            add_candidate(state, operation, 1)
            if scenario == 'collision':
                state['snapshot']['store'][note_id(operation)] = {'type': 'text', 'meta': {}}
            elif scenario == 'revision':
                del state['revision']
            else:
                operation['nodes'][0]['sourceIds'] = ['missing']
            with self.assertRaises(ValueError):
                plan(state, operation)

    def test_provenance_and_original_intent_are_immutable(self):
        state, operation = fixture()
        add_candidate(state, operation, 1)
        state, _ = apply(state, operation)
        changed = copy.deepcopy(operation)
        changed['nodes'][0]['prompt'] = '覆盖旧prompt'
        with self.assertRaises(ValueError):
            plan(state, changed)
        changed = copy.deepcopy(operation)
        changed['brief']['originalIntent'] = '改写用户原话'
        with self.assertRaises(ValueError):
            plan(state, changed)

    def test_no_cross_target_adoption(self):
        state, operation = fixture()
        add_candidate(state, operation, 1)
        operation['adopt'] = {'nodeId': 'other-target-node', 'userSelection': '采用另一页'}
        with self.assertRaises(ValueError):
            plan(state, operation)

    def test_verify_rejects_skips_losses_and_note_changes(self):
        state, operation = fixture()
        state, prepared = apply(state, operation)
        receipt = {'ok': True, 'skippedRecords': []}
        self.assertTrue(verify(prepared, operation, receipt, state)['ok'])
        with self.assertRaises(ValueError):
            verify(prepared, operation, {'ok': True, 'skippedRecords': ['bad']}, state)
        missing = copy.deepcopy(state)
        del missing['snapshot']['store']['shape:unrelated']
        with self.assertRaises(ValueError):
            verify(prepared, operation, receipt, missing)
        changed = copy.deepcopy(state)
        changed['snapshot']['store'][note_id(operation)]['x'] = 0
        with self.assertRaises(ValueError):
            verify(prepared, operation, receipt, changed)

    def test_cycle_rejected(self):
        state, operation = fixture()
        add_candidate(state, operation, 1, 'node-2')
        add_candidate(state, operation, 2, 'node-1')
        with self.assertRaises(ValueError):
            plan(state, operation)


if __name__ == '__main__':
    unittest.main()
