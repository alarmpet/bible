import json
from lib.aligned_prompt_compiler import compile_aligned_prompt
from validate_image_requests import validate
def test_prompt_has_required_anchor_and_no_forced_year():
 p=compile_aligned_prompt({'shot_id':'S','visual_mode':'place_establishing','semantic_anchors':['서고'],'focal_subject':'서고','action':'사람들이 이동','place':'서고','era':'조선','camera':'wide'})
 assert p['semantic_anchors']==['서고']; assert '1701' not in p['submission_prompt']

def test_preflight_rejects_production_placeholder_brief(tmp_path):
 requests=[]
 for i in range(101):
  requests.append({'shot_id':f'S{i:03d}','visual_mode':'host_chapter_hinge' if i in range(0,100,10) else 'historical_reconstruction','semantic_anchors':['palace','official'],'submission_prompt':'narration-specific subject; depict the narrated action directly'})
 (tmp_path/'flow_image_prompts.json').write_text(json.dumps({'requests':requests}),encoding='utf-8')
 errors=validate(tmp_path)
 assert any('placeholder' in error for error in errors)

def test_preflight_rejects_hangul_text_anchors_and_generic_fallback(tmp_path):
 requests=[]
 for i in range(101):
  requests.append({
   'shot_id':f'S{i:03d}',
   'visual_mode':'host_chapter_hinge' if i in range(0,100,10) else 'historical_reconstruction',
   'semantic_anchors':['숙종의','거부는','처분'] if i==12 else ['palace gate','kneeling ministers','sealed command case'],
   'submission_prompt':'period-dressed palace figures perform the single concrete action described by the narration' if i==13 else 'one concrete palace scene',
  })
 (tmp_path/'flow_image_prompts.json').write_text(json.dumps({'requests':requests}),encoding='utf-8')
 errors=validate(tmp_path)
 assert any('hangul semantic anchor' in error for error in errors)
 assert any('placeholder' in error for error in errors)
