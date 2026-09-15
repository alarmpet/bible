# -*- coding: utf-8 -*-
"""
벤치마크 30편('인류의 서재')의 자막 타임코드로 시간 위치별 내레이션 템포를 계산한다.
1차 소스: human_archive/research/human_library_top30/captions/*.json3 (단어 단위 tOffsetMs 보유, 30편)
보조 소스: D:/module/top_30_analyzed_data.json (VTT roll-up 형태 subtitles_parsed, 27편 겹침) -> 중복률 계산
길이 소스: popular_top30.json (30편 duration)
"""
import json, glob, os, re, statistics as st

R = 'D:/module/bible/human_archive/research/human_library_top30/'
CAP = R + 'captions/'
OUT = 'C:/Users/shs/AppData/Local/Temp/claude/D--module/0bdda2c5-f8cb-40d3-967f-5bbbad6204ea/scratchpad/quant_ref_result.json'

popular = json.load(open(R + 'popular_top30.json', encoding='utf-8'))
dur_by_id = {v['id']: v['duration'] for v in popular['videos']}
title_by_id = {v['id']: v['title'] for v in popular['videos']}
rank_by_id = {v['id']: v['rank'] for v in popular['videos']}
analyzed = json.load(open('D:/module/top_30_analyzed_data.json', encoding='utf-8'))
analyzed_by_id = {x['id']: x for x in analyzed}
ssm = json.load(open(R + 'script_structure_metrics.json', encoding='utf-8'))
sb = json.load(open(R + 'storyboard_metrics_cropped.json', encoding='utf-8'))
sb_by_id = {v['id']: v for v in sb['videos']}

PUNCT_END = re.compile(r'[.?!]$')
STRIP_PUNCT = re.compile(r'[.,?!"()\[\]:;]')
HEUR_END = ('다', '요', '죠', '까')
TRANSITIONS = {'그런데': ('그런데',), '근데': ('근데',), '하지만': ('하지만',), '왜': ('왜',), '사실': ('사실',), '놀랍게도': ('놀랍게도',)}
NUM_RE = re.compile(r'\d[\d,\.]*')
YEAR_RE = re.compile(r'(\d[\d,\.]*\s?(만|천|억)?\s?년|\d+\s?세기|기원전|BC|AD)')


def parse_json3(path):
    j = json.load(open(path, encoding='utf-8'))
    words, lines = [], []
    for e in j['events']:
        if 'segs' not in e or e.get('aAppend'):
            continue
        segs = e['segs']
        txt = ' '.join(s.get('utf8', '').strip() for s in segs if s.get('utf8', '').strip())
        if not txt:
            continue
        lines.append({'t': e['tStartMs'] / 1000.0, 'd': e.get('dDurationMs', 0) / 1000.0, 'text': txt})
        for s in segs:
            w = s.get('utf8', '').strip()
            if not w:
                continue
            t = (e['tStartMs'] + (s.get('tOffsetMs') or 0)) / 1000.0
            words.append({'t': t, 'w': w})
    words.sort(key=lambda x: x['t'])
    lines.sort(key=lambda x: x['t'])
    head_dur = None
    for e in j['events']:
        if 'segs' not in e and e.get('dDurationMs'):
            head_dur = e['dDurationMs'] / 1000.0
            break
    return words, lines, head_dur


def q(vals):
    vals = [v for v in vals if v is not None]
    if not vals:
        return None
    if len(vals) == 1:
        v = vals[0]
        return {'n': 1, 'mean': v, 'median': v, 'q1': v, 'q3': v, 'min': v, 'max': v}
    qs = st.quantiles(vals, n=4, method='inclusive')
    return {'n': len(vals), 'mean': round(st.mean(vals), 3), 'median': round(st.median(vals), 3),
            'q1': round(qs[0], 3), 'q3': round(qs[2], 3), 'min': round(min(vals), 3), 'max': round(max(vals), 3)}


def windows_for(D):
    return [('0-15s', 0, 15), ('15-60s', 15, 60), ('60-120s', 60, 120), ('120-300s', 120, 300),
            ('300-600s', 300, 600), ('600s-end-90s', 600, D - 90), ('last90s', D - 90, D)]


def window_metrics(words, lines, a, b):
    L = b - a
    if L <= 0:
        return None
    ws = [x for x in words if a <= x['t'] < b]
    ls = [x for x in lines if a <= x['t'] < b]
    n_words = len(ws)
    chars = sum(len(STRIP_PUNCT.sub('', x['w'])) for x in ws)
    punct_ends = [x['t'] for x in ws if PUNCT_END.search(x['w'])]
    heur_ends = [x['t'] for x in ws if PUNCT_END.search(x['w']) or STRIP_PUNCT.sub('', x['w']).endswith(HEUR_END)]
    n_q = sum(1 for x in ws if '?' in x['w'])
    tr = {k: 0 for k in TRANSITIONS}
    for x in ws:
        for k, pre in TRANSITIONS.items():
            if x['w'].startswith(pre):
                tr[k] += 1
    line_chars = [len(STRIP_PUNCT.sub('', x['text']).replace(' ', '')) for x in ls]
    line_gaps = [ls[i + 1]['t'] - ls[i]['t'] for i in range(len(ls) - 1)]
    line_durs = [x['d'] for x in ls]
    sent_gaps = [punct_ends[i + 1] - punct_ends[i] for i in range(len(punct_ends) - 1)]
    wgaps = [ws[i + 1]['t'] - ws[i]['t'] for i in range(len(ws) - 1)]
    silent = sum(g for g in wgaps if g > 1.5)
    return {
        'len_sec': L, 'n_words': n_words, 'n_chars': chars,
        'chars_per_sec': chars / L, 'words_per_sec': n_words / L,
        'n_sent_punct': len(punct_ends), 'sent_per_min_punct': len(punct_ends) / (L / 60.0),
        'n_sent_heur': len(heur_ends), 'sent_per_min_heur': len(heur_ends) / (L / 60.0),
        'sec_per_sentence_punct': (L / len(punct_ends)) if punct_ends else None,
        'sent_gap_median': st.median(sent_gaps) if sent_gaps else None,
        'sent_gap_p75': (st.quantiles(sent_gaps, n=4, method='inclusive')[2] if len(sent_gaps) >= 2 else None),
        'chars_per_sentence': (chars / len(punct_ends)) if punct_ends else None,
        'n_q': n_q, 'q_ratio': (n_q / len(punct_ends)) if punct_ends else None,
        'q_per_min': n_q / (L / 60.0),
        'transitions': tr, 'transitions_per_min': sum(tr.values()) / (L / 60.0),
        'transitions_per_min_ex_wae': (sum(tr.values()) - tr['왜']) / (L / 60.0),
        'n_lines': len(ls),
        'line_chars_mean': st.mean(line_chars) if line_chars else None,
        'line_onset_gap_mean': st.mean(line_gaps) if line_gaps else None,
        'line_dur_mean': st.mean(line_durs) if line_durs else None,
        'silent_gt1_5_ratio': silent / L,
        'sent_gaps': sent_gaps,
    }


per_video = []
files = sorted(glob.glob(CAP + '*.json3'))
for f in files:
    vid = os.path.basename(f).split('.')[0]
    words, lines, head_dur = parse_json3(f)
    D = dur_by_id.get(vid) or head_dur
    row = {'id': vid, 'rank': rank_by_id.get(vid), 'title': title_by_id.get(vid), 'duration': D,
           'json3_head_dur': head_dur, 'n_words': len(words), 'n_lines': len(lines),
           'last_word_t': words[-1]['t'] if words else None, 'windows': {}}
    for name, a, b in windows_for(D):
        row['windows'][name] = window_metrics(words, lines, a, b)
    row['whole'] = window_metrics(words, lines, 0, D)
    row['bins60'] = []
    for i in range(0, int(D // 60) + 1):
        a, b = i * 60, min((i + 1) * 60, D)
        if b - a < 20:
            break
        m = window_metrics(words, lines, a, b)
        row['bins60'].append({'bin': i, 'chars_per_sec': m['chars_per_sec'], 'sent_per_min_punct': m['sent_per_min_punct'],
                              'q_per_min': m['q_per_min'], 'sent_gap_median': m['sent_gap_median'], 'transitions_per_min': m['transitions_per_min']})
    row['bins_norm10'] = []
    for i in range(10):
        a, b = D * i / 10.0, D * (i + 1) / 10.0
        m = window_metrics(words, lines, a, b)
        row['bins_norm10'].append({'bin': i, 'chars_per_sec': m['chars_per_sec'], 'sent_per_min_punct': m['sent_per_min_punct'],
                                   'q_per_min': m['q_per_min'], 'sent_gap_median': m['sent_gap_median'], 'transitions_per_min': m['transitions_per_min']})
    txt90 = ' '.join(x['w'] for x in words if x['t'] < 90)
    row['first90_numbers'] = len(NUM_RE.findall(txt90))
    row['first90_years'] = len(YEAR_RE.findall(txt90))
    row['first90_text'] = txt90[:400]
    row['first15_text'] = ' '.join(x['w'] for x in words if x['t'] < 15)
    pe = [x['t'] for x in words if PUNCT_END.search(x['w'])]
    row['first_sentence_end_sec'] = pe[0] if pe else None
    row['first_question_sec'] = next((x['t'] for x in words if '?' in x['w']), None)
    row['sentences_in_first_30s'] = sum(1 for t in pe if t < 30)
    row['sentences_in_first_60s'] = sum(1 for t in pe if t < 60)
    row['brand_signoff_last90'] = ('인류의 서재' in ' '.join(x['w'] for x in words if x['t'] >= D - 90))
    row['storyboard'] = sb_by_id.get(vid)
    row['stage_bounds_sec'] = {'p10': D * 0.10, 'p30': D * 0.30, 'p70': D * 0.70, 'p90': D * 0.90}
    per_video.append(row)

WIN_NAMES = [w[0] for w in windows_for(1200)]
METRICS = ['chars_per_sec', 'words_per_sec', 'sent_per_min_punct', 'sent_per_min_heur', 'sec_per_sentence_punct',
           'sent_gap_median', 'sent_gap_p75', 'chars_per_sentence', 'q_ratio', 'q_per_min', 'transitions_per_min',
           'transitions_per_min_ex_wae', 'line_chars_mean', 'line_onset_gap_mean', 'line_dur_mean', 'silent_gt1_5_ratio']
agg = {}
for wn in WIN_NAMES:
    agg[wn] = {}
    for m in METRICS:
        agg[wn][m] = q([r['windows'][wn][m] for r in per_video if r['windows'][wn]])
    agg[wn]['transition_per_min_by_word'] = {}
    for k in TRANSITIONS:
        vals = [r['windows'][wn]['transitions'][k] / (r['windows'][wn]['len_sec'] / 60.0) for r in per_video if r['windows'][wn]]
        agg[wn]['transition_per_min_by_word'][k] = q(vals)
    pooled = [g for r in per_video if r['windows'][wn] for g in r['windows'][wn]['sent_gaps']]
    if len(pooled) >= 4:
        q4 = st.quantiles(pooled, n=4, method='inclusive')
        q10 = st.quantiles(pooled, n=10, method='inclusive')
        agg[wn]['pooled_sentence_gap_sec'] = {'n': len(pooled), 'mean': round(st.mean(pooled), 3), 'p10': round(q10[0], 3), 'p25': round(q4[0], 3),
                                              'median': round(st.median(pooled), 3), 'p75': round(q4[2], 3), 'p90': round(q10[8], 3),
                                              'share_le_3s': round(sum(1 for g in pooled if g <= 3) / len(pooled), 3),
                                              'share_le_5s': round(sum(1 for g in pooled if g <= 5) / len(pooled), 3),
                                              'share_gt_8s': round(sum(1 for g in pooled if g > 8) / len(pooled), 3)}
    two = []
    for r in per_video:
        g = r['windows'][wn]['sent_gaps'] if r['windows'][wn] else []
        two += [g[i] + g[i + 1] for i in range(0, len(g) - 1, 2)]
    if len(two) >= 4:
        q4 = st.quantiles(two, n=4, method='inclusive')
        agg[wn]['pooled_two_sentence_span_sec'] = {'n': len(two), 'mean': round(st.mean(two), 3), 'median': round(st.median(two), 3),
                                                   'p25': round(q4[0], 3), 'p75': round(q4[2], 3),
                                                   'share_gt_12s': round(sum(1 for g in two if g > 12) / len(two), 3),
                                                   'share_gt_15s': round(sum(1 for g in two if g > 15) / len(two), 3)}

whole = {m: q([r['whole'][m] for r in per_video]) for m in METRICS}

curve60 = []
for i in range(0, 31):
    vals = [b for r in per_video for b in r['bins60'] if b['bin'] == i]
    if len(vals) < 5:
        break
    curve60.append({'bin_start_sec': i * 60, 'n_videos': len(vals),
                    'chars_per_sec_mean': round(st.mean(v['chars_per_sec'] for v in vals), 3),
                    'sent_per_min_mean': round(st.mean(v['sent_per_min_punct'] for v in vals), 3),
                    'sent_gap_median_mean': round(st.mean(v['sent_gap_median'] for v in vals if v['sent_gap_median'] is not None), 3),
                    'q_per_min_mean': round(st.mean(v['q_per_min'] for v in vals), 3),
                    'transitions_per_min_mean': round(st.mean(v['transitions_per_min'] for v in vals), 3)})
curve_norm = []
for i in range(10):
    vals = [b for r in per_video for b in r['bins_norm10'] if b['bin'] == i]
    curve_norm.append({'norm_bin': f'{i*10}-{(i+1)*10}%', 'n_videos': len(vals),
                       'chars_per_sec_mean': round(st.mean(v['chars_per_sec'] for v in vals), 3),
                       'sent_per_min_mean': round(st.mean(v['sent_per_min_punct'] for v in vals), 3),
                       'sent_gap_median_mean': round(st.mean(v['sent_gap_median'] for v in vals if v['sent_gap_median'] is not None), 3),
                       'q_per_min_mean': round(st.mean(v['q_per_min'] for v in vals), 3),
                       'transitions_per_min_mean': round(st.mean(v['transitions_per_min'] for v in vals), 3)})

durs = [r['duration'] for r in per_video]
stage = {k: q([r['stage_bounds_sec'][k] for r in per_video]) for k in ['p10', 'p30', 'p70', 'p90']}
first90 = {'numbers': q([r['first90_numbers'] for r in per_video]), 'years': q([r['first90_years'] for r in per_video]),
           'videos_with_ge1_number': sum(1 for r in per_video if r['first90_numbers'] >= 1),
           'videos_with_ge3_numbers': sum(1 for r in per_video if r['first90_numbers'] >= 3),
           'videos_with_ge1_year': sum(1 for r in per_video if r['first90_years'] >= 1),
           'first_sentence_end_sec': q([r['first_sentence_end_sec'] for r in per_video]),
           'first_question_sec': q([r['first_question_sec'] for r in per_video]),
           'videos_with_question_in_60s': sum(1 for r in per_video if r['first_question_sec'] is not None and r['first_question_sec'] < 60),
           'videos_with_question_in_120s': sum(1 for r in per_video if r['first_question_sec'] is not None and r['first_question_sec'] < 120),
           'sentences_in_first_30s': q([r['sentences_in_first_30s'] for r in per_video]),
           'sentences_in_first_60s': q([r['sentences_in_first_60s'] for r in per_video]),
           'brand_signoff_last90_count': sum(1 for r in per_video if r['brand_signoff_last90'])}

dup_rows = []


def ts(s):
    h, m, sec = s.split(':')
    return int(h) * 3600 + int(m) * 60 + float(sec)


for vid, x in analyzed_by_id.items():
    cues = x.get('subtitles_parsed') or []
    if not cues:
        continue
    n = len(cues)
    bridge = sum(1 for c in cues if ts(c['end']) - ts(c['start']) <= 0.02)
    contained = 0
    exact_same = 0
    for i, c in enumerate(cues):
        t = c['text'].strip()
        prev = cues[i - 1]['text'].strip() if i > 0 else ''
        nxt = cues[i + 1]['text'].strip() if i + 1 < n else ''
        if t and ((prev and t in prev) or (nxt and t in nxt)):
            contained += 1
        if t and t == prev:
            exact_same += 1
    total_chars = sum(len(c['text'].replace(' ', '')) for c in cues)
    uniq = 0
    prev = ''
    for c in cues:
        t = c['text'].strip()
        if prev and t.startswith(prev):
            new = t[len(prev):]
        elif prev and prev.endswith(t):
            new = ''
        else:
            k = 0
            for L in range(min(len(prev), len(t)), 0, -1):
                if prev.endswith(t[:L]):
                    k = L
                    break
            new = t[k:]
        uniq += len(new.replace(' ', ''))
        prev = t
    pv = next((r for r in per_video if r['id'] == vid), None)
    json3_chars = pv['whole']['n_chars'] if pv else None
    ft = x.get('full_transcript') or ''
    dup_rows.append({'id': vid, 'n_cues': n, 'bridge_cue_ratio': bridge / n, 'contained_in_neighbor_ratio': contained / n,
                     'exact_same_as_prev_ratio': exact_same / n, 'total_cue_chars': total_chars, 'dedup_chars_est': uniq,
                     'inflation_vs_dedup': total_chars / uniq if uniq else None,
                     'full_transcript_chars': len(ft.replace(' ', '')),
                     'inflation_full_transcript_vs_json3': (len(ft.replace(' ', '')) / json3_chars) if json3_chars else None,
                     'in_json3_set': pv is not None})
j3_same = []
for f in files:
    _, lines, _ = parse_json3(f)
    s = sum(1 for i in range(1, len(lines)) if lines[i]['text'] == lines[i - 1]['text'])
    j3_same.append(s / max(1, len(lines)))
dup = {'n_videos_analyzed_json': len(dup_rows), 'n_overlap_with_json3': sum(1 for r in dup_rows if r['in_json3_set']),
       'bridge_cue_ratio': q([r['bridge_cue_ratio'] for r in dup_rows]),
       'contained_in_neighbor_ratio': q([r['contained_in_neighbor_ratio'] for r in dup_rows]),
       'exact_same_as_prev_ratio': q([r['exact_same_as_prev_ratio'] for r in dup_rows]),
       'inflation_vs_dedup': q([r['inflation_vs_dedup'] for r in dup_rows]),
       'inflation_full_transcript_vs_json3': q([r['inflation_full_transcript_vs_json3'] for r in dup_rows if r['inflation_full_transcript_vs_json3']]),
       'json3_consecutive_identical_line_ratio': q(j3_same),
       'json3_aAppend_note': 'json3의 aAppend 이벤트는 줄바꿈 롤업 마커이며 텍스트 중복이 아님. 본 계산은 aAppend 제외.'}
sbq = {'interval_sec': q([r['storyboard']['interval_sec'] for r in per_video if r['storyboard']]),
       'strong_change_ratio_ge_14': q([r['storyboard']['strong_change_ratio_ge_14'] for r in per_video if r['storyboard']]),
       'near_duplicate_ratio_le_6': q([r['storyboard']['near_duplicate_ratio_le_6'] for r in per_video if r['storyboard']]),
       'note': '고정 간격(약 9.8초) 스토리보드 프레임 간 pHash 거리이며 실제 컷 경계 타임코드는 데이터에 없음.'}
ssm_cmp = {'chars_per_second': q([v['chars_per_second'] for v in ssm['videos']]),
           'sentences_per_minute': q([v['sentences_per_minute'] for v in ssm['videos']]),
           'question_per_minute': q([v['question_per_minute'] for v in ssm['videos']])}

result = {
    'meta': {'n_videos_json3': len(per_video),
             'sources': {'captions_json3': CAP, 'popular': R + 'popular_top30.json', 'analyzed_vtt_rollup': 'D:/module/top_30_analyzed_data.json'},
             'window_defs': WIN_NAMES,
             'sentence_end_rule': 'punct: 단어 토큰이 . ? ! 로 끝남 / heur: punct 또는 토큰이 다·요·죠·까로 끝남',
             'transition_words': list(TRANSITIONS.keys()),
             'note_no_cut_boundaries': '실제 컷(화면 전환) 경계 타임코드는 어떤 데이터에도 없음. 스토리보드 pHash는 9.8초 고정 간격 관찰치.'},
    'durations_sec': q(durs), 'stage_boundaries_sec': stage, 'windows': agg, 'whole_video': whole,
    'curve_60s_bins': curve60, 'curve_norm10': curve_norm, 'first90': first90, 'duplication': dup,
    'storyboard_phash': sbq, 'script_structure_metrics_crosscheck': ssm_cmp,
    'per_video': [{k: v for k, v in r.items() if k not in ('bins60', 'bins_norm10', 'first90_text')} for r in per_video],
    'per_video_dup': dup_rows,
}
for r in result['per_video']:
    for wn, m in r['windows'].items():
        if m:
            m.pop('sent_gaps', None)
    r['whole'].pop('sent_gaps', None)
json.dump(result, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=0)

print('videos', len(per_video), 'durations', result['durations_sec'])
print('stage', stage)
hdr = '%-13s %8s %8s %8s %8s %8s %8s %8s %8s %8s' % ('window', 'cps', 'sent/min', 'sec/sent', 'gapMed', 'gapP75', 'q/min', 'q_ratio', 'trans/m', 'lineGap')
for key in ('median', 'mean'):
    print('\n(%s)\n%s' % (key, hdr))
    for wn in WIN_NAMES:
        a = agg[wn]

        def f(m):
            v = a[m]
            return '%8.2f' % v[key] if v and v.get(key) is not None else '     n/a'
        print('%-13s %s %s %s %s %s %s %s %s %s' % (wn, f('chars_per_sec'), f('sent_per_min_punct'), f('sec_per_sentence_punct'), f('sent_gap_median'), f('sent_gap_p75'), f('q_per_min'), f('q_ratio'), f('transitions_per_min'), f('line_onset_gap_mean')))
print('\npooled sentence gaps:')
for wn in WIN_NAMES:
    print(wn, agg[wn].get('pooled_sentence_gap_sec'))
    print('   two-sentence:', agg[wn].get('pooled_two_sentence_span_sec'))
print('\ntransition words per min (mean) by window:')
for wn in WIN_NAMES:
    print(wn, {k: v['mean'] for k, v in agg[wn]['transition_per_min_by_word'].items()})
print('\ncurve60:')
for c in curve60:
    print(c)
print('\ncurve_norm10:')
for c in curve_norm:
    print(c)
print('\nfirst90', json.dumps(first90, ensure_ascii=False))
print('\ndup', json.dumps(dup, ensure_ascii=False))
print('\nstoryboard', json.dumps(sbq, ensure_ascii=False))
print('\nssm crosscheck', json.dumps(ssm_cmp, ensure_ascii=False))
print('\nwhole', json.dumps({k: whole[k] for k in ['chars_per_sec', 'sent_per_min_punct', 'sent_per_min_heur', 'sec_per_sentence_punct', 'q_ratio', 'silent_gt1_5_ratio', 'line_onset_gap_mean', 'line_chars_mean']}, ensure_ascii=False))
print('\nper-video sanity:')
for r in per_video:
    print(r['rank'], r['id'], r['duration'], r['json3_head_dur'], 'words', r['n_words'], 'lines', r['n_lines'], 'lastw', round(r['last_word_t'], 1),
          'cps0-15', round(r['windows']['0-15s']['chars_per_sec'], 2), 'cps300-600', round(r['windows']['300-600s']['chars_per_sec'], 2),
          'n90', r['first90_numbers'], 'y90', r['first90_years'], 'firstQ', r['first_question_sec'], 'sent30', r['sentences_in_first_30s'])
print('\nfirst15 texts:')
for r in per_video:
    print(r['rank'], '|', r['first15_text'][:110])
