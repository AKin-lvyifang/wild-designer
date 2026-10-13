"""Simulated evidence only. No network, image generation, or design document writes."""
import copy
import unittest
from route_design import route


def base():
    return {'designRequested': True, 'image': {'tool': 'fixture.imagegen', 'available': True},
            'adapters': []}


def adapter(name, kind='editable'):
    capabilities = (['new_layout', 'text', 'simple_vector', 'place_raster', 'readback', 'preview']
                    if kind == 'editable' else ['insert_image', 'readback', 'preview'])
    tools = {key: 'fixture.' + name + '.' + key for key in capabilities}
    return {'id': name, 'kind': kind, 'adapterKnown': True, 'targetResolved': True,
            'scopeAuthorized': True, 'tools': tools,
            'probe': {'tool': tools['readback'], 'ok': True, 'evidence': 'synthetic-read-result'}}


class RouteTests(unittest.TestCase):
    def test_pure_gpt(self):
        actual = route(base())
        self.assertEqual(actual['creation'], 'imagegen')
        self.assertIsNone(actual['editable'])
        self.assertIsNone(actual['preview'])
        self.assertIsNone(actual['question'])

    def test_gpt_with_cowart(self):
        data = base()
        data['adapters'] = [adapter('cowart', 'canvas')]
        actual = route(data)
        self.assertEqual(actual['preview'], 'cowart')
        self.assertEqual(actual['previewPlacement'], 'host-controlled')
        self.assertFalse(actual['adoptionChanged'])

    def test_paper_ready(self):
        data = base()
        data['adapters'] = [adapter('paper')]
        actual = route(data)
        self.assertEqual(actual['editable'], 'paper')
        self.assertEqual(actual['creation'], 'imagegen')
        self.assertIsNone(actual['question'])

    def test_figma_ready(self):
        data = base()
        data['adapters'] = [adapter('figma')]
        actual = route(data)
        self.assertEqual(actual['editable'], 'figma')
        self.assertEqual(actual['preview'], 'figma')

    def test_app_open_but_mcp_offline(self):
        data = base()
        paper = adapter('paper')
        paper['appOpen'] = True
        paper['probe']['ok'] = False
        data['adapters'] = [paper]
        actual = route(data)
        self.assertEqual(actual['creation'], 'imagegen')
        self.assertIsNone(actual['editable'])

    def test_cannot_select_model(self):
        data = base()
        data['image']['supportedModels'] = ['requested-model']
        data['image']['preferredModel'] = 'requested-model'
        self.assertIsNone(route(data)['modelChoice'])
        data['image']['modelSelector'] = 'model'
        self.assertEqual(route(data)['modelChoice'], {'parameter': 'model', 'value': 'requested-model'})
        data['image']['supportedModels'] = ['some-other-model']
        self.assertIsNone(route(data)['modelChoice'])

    def test_no_model_preference_uses_host_default(self):
        data = base()
        data['image'].update({'modelSelector': 'model', 'supportedModels': ['image-2.5']})
        self.assertIsNone(route(data)['modelChoice'])

    def test_complex_photograph_keeps_raster_regions(self):
        data = base()
        data['complexRaster'] = True
        data['adapters'] = [adapter('figma')]
        actual = route(data)
        self.assertEqual(actual['editableScope'], 'layout_text_simple_vectors_with_raster_regions')

    def test_missing_material_context_asks_one(self):
        data = base()
        data['criticalAmbiguity'] = '这次是活动封面还是产品首页？'
        actual = route(data)
        self.assertEqual(actual['question'], data['criticalAmbiguity'])
        self.assertEqual(actual['creation'], 'await_one_material_answer')
        self.assertIsNone(actual['editable'])

    def test_online_does_not_grant_scope_or_permissions(self):
        for key, value in [('scopeAuthorized', False), ('targetResolved', False), ('permissionDenied', True)]:
            data = base()
            paper = adapter('paper')
            paper[key] = value
            data['adapters'] = [paper]
            self.assertIsNone(route(data)['editable'])

    def test_no_writable_operation_is_not_editable(self):
        data = base()
        figma = adapter('figma')
        del figma['tools']['text']
        data['adapters'] = [figma]
        self.assertIsNone(route(data)['editable'])

    def test_unknown_canvas_requires_adapter(self):
        data = base()
        canvas = adapter('unknown-canvas', 'canvas')
        canvas['adapterKnown'] = False
        data['adapters'] = [canvas]
        self.assertIsNone(route(data)['preview'])
        canvas['adapterKnown'] = True
        self.assertEqual(route(data)['preview'], 'unknown-canvas')

    def test_one_editor_and_context_preference(self):
        data = base()
        data['adapters'] = [adapter('figma'), adapter('paper')]
        self.assertEqual(route(data)['editable'], 'paper')
        data['preferredEditor'] = 'figma'
        self.assertEqual(route(data)['editable'], 'figma')

    def test_known_reference_is_not_automatically_reused(self):
        data = base()
        data['sourceImageAvailable'] = True
        self.assertEqual(route(data)['creation'], 'imagegen')
        data['reuseSource'] = True
        self.assertEqual(route(data)['creation'], 'existing_image')

    def test_brief_only_and_bitmap_only(self):
        data = base()
        data['adapters'] = [adapter('paper')]
        data['designRequested'] = False
        self.assertEqual(route(data)['creation'], 'brief_only')
        self.assertIsNone(route(data)['editable'])
        data['designRequested'] = True
        data['bitmapOnly'] = True
        self.assertIsNone(route(data)['editable'])

    def test_missing_imagegen_uses_native_or_brief(self):
        data = base()
        data['image']['available'] = False
        self.assertEqual(route(data)['creation'], 'brief_only')
        data['adapters'] = [adapter('paper'), adapter('cowart', 'canvas')]
        self.assertEqual(route(data)['creation'], 'native')
        self.assertEqual(route(data)['preview'], 'paper')  # No bitmap export capability.

    def test_available_helpers_do_not_replace_design_judgment(self):
        data = base()
        data['style'] = {'helpers': {'ui-ux-pro-max': True, 'design-md': True}}
        actual = route(data)
        self.assertEqual(actual['style']['mode'], 'develop_design_directions')
        self.assertEqual(actual['style']['sources'], [])
        self.assertIsNone(actual['question'])
        self.assertEqual(actual['candidateStatus'], 'proposed')

    def test_concrete_reference_gap_uses_available_helper(self):
        data = base()
        contract = {'styleId': 'brand', 'colors': {'accent': 'blue'}}
        data['style'] = {'helpers': {'ui-ux-pro-max': True}, 'existingContract': contract,
                         'referenceNeed': '补足中文标题字体候选'}
        actual = route(data)['style']
        self.assertEqual(actual['mode'], 'reuse_contract')
        self.assertEqual(actual['sources'], ['ui-ux-pro-max'])
        self.assertEqual(actual['constraints'], contract)

    def test_explicit_brand_looks_up_spec_not_new_style(self):
        data = base()
        data['style'] = {'explicitStyle': 'Linear', 'matchedBrandReference': 'references/linear-app/DESIGN.md',
                         'helpers': {'ui-ux-pro-max': True, 'design-md': True}}
        actual = route(data)['style']
        self.assertEqual(actual['mode'], 'reference_lookup')
        self.assertEqual(actual['sources'], ['design-md'])

    def test_existing_brand_contract_needs_no_repeat_lookup(self):
        data = base()
        data['style'] = {'explicitStyle': 'brand', 'matchedBrandReference': 'brand/DESIGN.md',
                         'helpers': {'design-md': True, 'ui-ux-pro-max': True},
                         'existingContract': {'styleId': 'selected-brand'}}
        actual = route(data)['style']
        self.assertEqual(actual['mode'], 'reuse_contract')
        self.assertEqual(actual['sources'], [])

    def test_missing_style_helpers_never_blocks_creation(self):
        data = base()
        data['style'] = {'helpers': {}, 'explicitStyle': '温暖的编辑风'}
        actual = route(data)
        self.assertEqual(actual['creation'], 'imagegen')
        self.assertEqual(actual['style']['sources'], [])
        self.assertEqual(actual['style']['mode'], 'apply_explicit_direction')

    def test_project_spec_over_library_and_current_user_over_spec(self):
        data = base()
        data['style'] = {'librarySuggestion': {'colors': {'accent': 'purple'}, 'stack': 'tailwind'},
                         'projectSpec': {'colors': {'accent': 'blue', 'background': 'white'}, 'stack': 'swiftui'},
                         'userChanges': {'colors': {'accent': 'orange'}}}
        actual = route(data)['style']['constraints']
        self.assertEqual(actual['colors'], {'accent': 'orange', 'background': 'white'})
        self.assertEqual(actual['stack'], 'swiftui')

    def test_cross_page_contract_consistency_and_nonmutation(self):
        data = base()
        contract = {'styleId': 'style-one', 'revision': 3, 'colors': {'accent': 'blue'},
                    'typography': {'body': 'sans'}, 'density': 'calm', 'radius': 8}
        data['style'] = {'existingContract': contract,
                         'librarySuggestion': {'colors': {'accent': 'purple'}, 'density': 'dense', 'extra': 'new'}}
        before = copy.deepcopy(data)
        home = route(data)['style']
        data['target'] = 'details'
        detail = route(data)['style']
        self.assertEqual(home['constraints'], contract)
        self.assertEqual(detail['constraints'], home['constraints'])
        self.assertEqual(home['mode'], 'reuse_contract')
        self.assertEqual(data['style'], before['style'])


if __name__ == '__main__':
    unittest.main()
