import json, bisect
m=json.load(open('D:/module/bible/human_archive/runs/ep02_jang_huibin/full-v6-001/sentence_audio_manifest.json',encoding='utf-8'))
S=sorted(m['sentences'],key=lambda r:r['start_sec'])
T=m.get('total_duration_sec') or S[-1]['end_sec']
print('sentences',len(S),'T',T, 'mean dur', sum(r['end_sec']-r['start_sec'] for r in S)/len(S))
# chapter info from script? use sentence 'chapter' if present
has_ch = 'chapter' in S[0]
def interp(anchors, t):
    # anchors list of (t, dict)
    ts=[a[0] for a in anchors]
    if t<=ts[0]: return anchors[0][1]
    if t>=ts[-1]: return anchors[-1][1]
    i=bisect.bisect_right(ts,t)-1
    (t0,a),(t1,b)=anchors[i],anchors[i+1]
    f=(t-t0)/(t1-t0)
    out={}
    for k in a:
        if k=='ms': out[k]=int(a[k]+(b[k]-a[k])*f)  # floor
        elif k=='u': out[k]=a[k]+(b[k]-a[k])*f
        else: out[k]=a[k]+(b[k]-a[k])*f
    return out
def run(name, anchors):
    A=[(t if not isinstance(t,str) else (T-90 if t=='end-90' else T), v) for t,v in anchors]
    A.sort(key=lambda x:x[0])
    cuts=[]; i=0
    while i<len(S):
        st=S[i]['start_sec']; loc=interp(A,st); rows=[S[i]]; end=S[i]['end_sec']; j=i+1
        while j<len(S) and len(rows)<loc['ms']:
            if has_ch and S[j].get('chapter')!=S[i].get('chapter'): break
            cand=S[j]['end_sec']-st; cur=end-st
            if cand<=loc['target'] or (cur<loc['min'] and cand<=loc['hard']):
                rows.append(S[j]); end=S[j]['end_sec']; j+=1; continue
            break
        cuts.append((st,end,len(rows),loc.get('u',1.0)))
        i=j
    # zone stats
    def stat(lo,hi):
        c=[x for x in cuts if lo<=x[0]<hi]
        return len(c), (sum(x[1]-x[0] for x in c)/len(c) if c else 0)
    zones=[(0,15),(15,60),(60,120),(120,300),(300,600),(600,T-90),(T-90,T+1)]
    uniq=sum(x[3] for x in cuts)
    print(f'{name}: cuts={len(cuts)} unique~={uniq:.0f} first120={stat(0,120)[0]} over15={sum(1 for x in cuts if x[1]-x[0]>15)}')
    for lo,hi in zones:
        n,avg=stat(lo,hi); print(f'   [{lo:.0f},{hi:.0f}) n={n} avg={avg:.2f}')
# Retention: anchors t: min,target,max,hard,ms,u
ret=[(0,dict(min=2.5,target=3.5,hard=6,ms=1,u=1.0)),(15,dict(min=3,target=4.5,hard=7,ms=1,u=.8)),(40,dict(min=4,target=6,hard=9,ms=2,u=.6)),(120,dict(min=6,target=8,hard=12,ms=2,u=.7)),(300,dict(min=8,target=9.5,hard=15,ms=2,u=.65)),(600,dict(min=9,target=11,hard=15,ms=3,u=.5)),('end-90',dict(min=10,target=12.5,hard=15,ms=3,u=.45)),('end',dict(min=10,target=12.5,hard=15,ms=3,u=.45))]
bud=[(0,dict(min=2.5,target=3.5,hard=6,ms=1,u=.6)),(15,dict(min=3.5,target=4.5,hard=8,ms=2,u=.5)),(60,dict(min=4.5,target=6,hard=10,ms=2,u=.5)),(120,dict(min=6,target=8,hard=12,ms=2,u=.45)),(300,dict(min=9,target=10.5,hard=15,ms=2,u=.4)),(600,dict(min=10,target=12,hard=15,ms=2,u=.33)),('end-90',dict(min=10,target=13,hard=15,ms=3,u=.3)),('end',dict(min=10,target=13,hard=15,ms=3,u=.3))]
aut=[(0,dict(min=3,target=4,hard=6,ms=1,u=.7)),(15,dict(min=3.5,target=4.5,hard=8,ms=1,u=.65)),(60,dict(min=5,target=7,hard=10,ms=2,u=.55)),(120,dict(min=7,target=9,hard=15,ms=2,u=.75)),(300,dict(min=9,target=10.5,hard=15,ms=2,u=.7)),(600,dict(min=9,target=11.5,hard=15,ms=3,u=.55)),('end-90',dict(min=10,target=12,hard=15,ms=3,u=.55)),('end',dict(min=10,target=13,hard=15,ms=3,u=.55))]
uni=[(0,dict(min=9,target=10.5,hard=15,ms=2,u=1.0)),('end',dict(min=9,target=10.5,hard=15,ms=2,u=1.0))]
run('uniform_v1',uni); run('retention',ret); run('budget',bud); run('autonomy',aut)
