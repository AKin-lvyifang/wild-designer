#!/usr/bin/env python3
"""Pure planning from verified capability evidence. Never calls apps or generates art."""
import copy
import json
from pathlib import Path
import sys

EDITABLE = {'new_layout', 'text', 'simple_vector', 'place_raster', 'readback'}
CANVAS = {'insert_image', 'readback', 'preview'}


def ready(adapter, required):
    tools = adapter.get('tools', {})
    probe = adapter.get('probe', {})
    return (adapter.get('adapterKnown') is True
            and adapter.get('targetResolved') is True
            and adapter.get('scopeAuthorized') is True
            and adapter.get('permissionDenied') is not True
            and probe.get('ok') is True and bool(probe.get('evidence'))
            and bool(probe.get('tool')) and probe['tool'] in tools.values()
            and all(isinstance(tools.get(key), str) and tools[key] for key in required))


def choose(adapters, preferred, order):
    return min(adapters, key=lambda a: (a['id'] != preferred,
               order.index(a['id']) if a['id'] in order else len(order), a['id'])) if adapters else None


def merge(base, override):
    result = copy.deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = merge(result[key], value)
        else:
            result[key] = copy.deepcopy(value)
    return result


def style_plan(style):
    helpers = style.get('helpers', {})
    explicit = bool(style.get('explicitStyle'))
    contract = style.get('existingContract', {})
    spec = style.get('projectSpec', {})
    changes = style.get('userChanges', {})
    # Library recommendations never silently revise an existing style contract/spec.
    tokens = copy.deepcopy(contract or spec or style.get('librarySuggestion', {}))
    tokens = merge(tokens, spec)
    tokens = merge(tokens, changes)
    sources = []
    if (explicit and style.get('matchedBrandReference') and helpers.get('design-md') is True
            and (style.get('referenceNeed') or not (contract or spec))):
        sources = ['design-md']
    elif style.get('referenceNeed') and helpers.get('ui-ux-pro-max') is True:
        sources = ['ui-ux-pro-max']
    elif style.get('referenceNeed') and helpers.get('design-md') is True:
        sources = ['design-md']
    mode = ('reuse_contract' if (contract or spec) else
            'reference_lookup' if sources else
            'apply_explicit_direction' if explicit else 'develop_design_directions')
    return {'mode': mode, 'sources': sources, 'constraints': tokens,
            'examples': 'inspected_reference_or_actual_generated_demo',
            'changesRequireUserDirection': True}


def route(data):
    result = {'creation': 'none', 'modelChoice': None, 'editable': None, 'preview': None,
              'previewPlacement': 'host-controlled', 'candidateStatus': 'proposed',
              'adoptionChanged': False, 'question': None,
              'style': style_plan(data.get('style', {}))}
    if data.get('designRequested') is not True:
        result['creation'] = 'brief_only'
        return result
    if data.get('criticalAmbiguity'):
        result['question'] = data['criticalAmbiguity']
        result['creation'] = 'await_one_material_answer'
        return result
    adapters = data.get('adapters', [])
    editors = [a for a in adapters if a.get('kind') == 'editable' and ready(a, EDITABLE)]
    editor = None if data.get('bitmapOnly') is True else choose(
        editors, data.get('preferredEditor'), ['paper', 'figma'])
    image = data.get('image', {})
    image_available = image.get('available') is True and bool(image.get('tool'))
    reusable_image = data.get('sourceImageAvailable') is True and data.get('reuseSource') is True
    result['creation'] = ('existing_image' if reusable_image else 'imagegen' if image_available
                          else 'native' if editor else 'brief_only')
    preferred_model = image.get('preferredModel')
    if (result['creation'] == 'imagegen' and isinstance(preferred_model, str)
            and preferred_model and image.get('modelSelector')
            and preferred_model in image.get('supportedModels', [])):
        result['modelChoice'] = {'parameter': image['modelSelector'], 'value': preferred_model}
    if editor and result['creation'] != 'brief_only':
        result['editable'] = editor['id']
        result['editableScope'] = ('layout_text_simple_vectors_with_raster_regions'
                                   if data.get('complexRaster') is True else 'native_reconstruction')
    has_bitmap = result['creation'] in {'existing_image', 'imagegen'}
    if has_bitmap or (editor and 'export_image' in editor.get('tools', {})):
        canvases = [a for a in adapters if a.get('kind') == 'canvas' and ready(a, CANVAS)]
        canvas = choose(canvases, data.get('activeCanvas'), ['cowart'])
        if canvas:
            result['preview'] = canvas['id']
    if not result['preview'] and editor and 'preview' in editor.get('tools', {}):
        result['preview'] = editor['id']
    result['delivery'] = 'actual_files_images_or_design_links'
    return result


if __name__ == '__main__':
    if len(sys.argv) != 2:
        raise SystemExit('Usage: route_design.py capabilities.json')
    result = route(json.loads(Path(sys.argv[1]).read_text(encoding='utf-8')))
    print(json.dumps(result, ensure_ascii=False, indent=2))
