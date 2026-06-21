#!/usr/bin/env python3
# Pulls FINISHED World Cup results from football-data.org and writes ../results.json
#   results.json = {"group": {"<mid>":[h,a]}, "ko": {"<mid>":[homeES,awayES,h,a,advES]}}
# Group matches (mid 1-72) are matched by team pair. Knockout matches (mid 73-104) are
# matched by stage + chronological order (teams are unknown until the bracket resolves, so
# we map each stage's API matches, sorted by kickoff, onto that round's fixed mid slots).
# Requires env FOOTBALL_DATA_TOKEN (free at https://www.football-data.org/client/register).
# For local testing without network, set FOOTBALL_DATA_FILE to a saved matches JSON.
import os,json,unicodedata,urllib.request,sys
HERE=os.path.dirname(os.path.abspath(__file__)); ROOT=os.path.dirname(HERE)
cfg=json.load(open(os.path.join(HERE,'fixtures.json')))
FIX={int(k):v for k,v in cfg['fixtures'].items()}; ALIAS=cfg['alias']

# Knockout stage -> the mid slots it fills, in chronological (kickoff) order.
STAGE_MIDS={
 'LAST_32':list(range(73,89)),   # 16 matches  -> R32  (mid 73-88)
 'LAST_16':list(range(89,97)),   #  8 matches  -> R16  (mid 89-96)
 'QUARTER_FINALS':list(range(97,101)),  # 4 -> QF (mid 97-100)
 'SEMI_FINALS':[101,102],        #  2 matches  -> SF   (mid 101-102)
 'THIRD_PLACE':[103],            #  1 match    -> 3rd  (mid 103)
 'FINAL':[104],                  #  1 match    -> Final(mid 104)
}

def norm(x):
    x=unicodedata.normalize('NFKD',x).encode('ascii','ignore').decode().lower()
    for ch in "-.,'’ ": x=x.replace(ch,' ')
    return ' '.join(x.split())
# build normalized-alias -> spanish-name
A2ES={}
for es,al in ALIAS.items():
    A2ES[norm(es)]=es
    for a in al: A2ES[norm(a)]=es
def match_team(name):
    n=norm(name or '')
    if not n: return None        # empty/None team name -> no match (avoid '' substring matching everything)
    if n in A2ES: return A2ES[n]
    for k,es in A2ES.items():
        if k and (k in n or n in k): return es
    return None

# --- load match data (API, or a local file for testing) ---
local=os.environ.get('FOOTBALL_DATA_FILE')
if local:
    api=json.load(open(local))
else:
    TOKEN=os.environ.get('FOOTBALL_DATA_TOKEN')
    if not TOKEN: print('Missing FOOTBALL_DATA_TOKEN'); sys.exit(1)
    req=urllib.request.Request('https://api.football-data.org/v4/competitions/WC/matches',headers={'X-Auth-Token':TOKEN})
    api=json.load(urllib.request.urlopen(req,timeout=30))
matches=api.get('matches',[])

# --- read existing results.json, accepting the legacy flat {mid:[h,a]} shape too ---
try: prev=json.load(open(os.path.join(ROOT,'results.json')))
except Exception: prev={}
group=dict(prev.get('group', prev if 'group' not in prev and 'ko' not in prev else {}))
ko=dict(prev.get('ko', {}))

# --- group stage: match by team pair (both orientations) ---
pair2mid={}
for mid,(h,a) in FIX.items(): pair2mid[(h,a)]=mid
g_added=0
for m in matches:
    if m.get('stage')!='GROUP_STAGE' or m.get('status')!='FINISHED': continue
    h=match_team(m['homeTeam'].get('name')); a=match_team(m['awayTeam'].get('name'))
    if not h or not a: continue
    ft=m.get('score',{}).get('fullTime',{}); hg,ag=ft.get('home'),ft.get('away')
    if hg is None or ag is None: continue
    if (h,a) in pair2mid: mid=pair2mid[(h,a)]; res=[hg,ag]
    elif (a,h) in pair2mid: mid=pair2mid[(a,h)]; res=[ag,hg]
    else: continue
    group[str(mid)]=res; g_added+=1

# --- knockouts: assign each stage's matches to its mid slots in kickoff order ---
k_added=0; unmatched_team=0
for stage,mids in STAGE_MIDS.items():
    stage_matches=sorted([m for m in matches if m.get('stage')==stage],
                         key=lambda m:(m.get('utcDate') or '', m.get('id') or 0))
    for mid,m in zip(mids, stage_matches):
        if m.get('status')!='FINISHED': continue
        h=match_team(m['homeTeam'].get('name')); a=match_team(m['awayTeam'].get('name'))
        ft=m.get('score',{}).get('fullTime',{}); hg,ag=ft.get('home'),ft.get('away')
        if hg is None or ag is None: continue
        if not h or not a: unmatched_team+=1; continue
        w=m.get('score',{}).get('winner')   # HOME_TEAM / AWAY_TEAM / DRAW
        adv=h if w=='HOME_TEAM' else a if w=='AWAY_TEAM' else None
        ko[str(mid)]=[h,a,hg,ag,adv]; k_added+=1

# --- manual overrides: corrections for API errors. Applied LAST so they win and persist
#     across every fetch. Edit overrides.json to add/remove; see its _comment for the format. ---
ov_g=ov_k=0
try:
    ov=json.load(open(os.path.join(ROOT,'overrides.json')))
    for mid,val in (ov.get('group') or {}).items(): group[str(mid)]=val; ov_g+=1
    for mid,val in (ov.get('ko') or {}).items(): ko[str(mid)]=val; ov_k+=1
except FileNotFoundError:
    pass
except Exception as e:
    print('WARNING: overrides.json present but unreadable, ignoring:', e)

out={'group':group,'ko':ko}
json.dump(out,open(os.path.join(ROOT,'results.json'),'w'),ensure_ascii=False,indent=0)
print(f'updated results.json — group: {g_added} matched ({len(group)} total) · '
      f'ko: {k_added} matched ({len(ko)} total)'
      + (f' · overrides applied: {ov_g} group, {ov_k} ko' if (ov_g or ov_k) else '')
      + (f' · {unmatched_team} ko match(es) had unrecognized team names' if unmatched_team else ''))
