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
GROUPS=cfg['groups']                      # {group letter: [4 team names]}
WIR=cfg['ko_wiring']                       # bracket wiring (positions / feeder mids)
R32_HOME={int(k):v for k,v in WIR['r32'].items()}        # mid -> home group-position code e.g. "1I"
FEEDERS={int(k):v for k,v in WIR['feeders'].items()}     # mid -> [homeFeederMid, awayFeederMid]
THIRD={int(k):v for k,v in WIR['third'].items()}         # mid -> [sfMidA, sfMidB] (losers)
FINAL={int(k):v for k,v in WIR['final'].items()}         # mid -> [sfMidA, sfMidB] (winners)

# Which stage each knockout mid belongs to (used to pick the right API matches).
MID_STAGE={**{m:'LAST_32' for m in range(73,89)},**{m:'LAST_16' for m in range(89,97)},
           **{m:'QUARTER_FINALS' for m in range(97,101)},101:'SEMI_FINALS',102:'SEMI_FINALS',
           103:'THIRD_PLACE',104:'FINAL'}
# Process knockout slots in bracket order so feeder winners are known before later rounds.
KO_ORDER=list(range(73,105))

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
g_added=0; api_final_group={}   # mid -> [h,a] for matches the API reports FINISHED (used to auto-prune overrides)
for m in matches:
    if m.get('stage')!='GROUP_STAGE' or m.get('status')!='FINISHED': continue
    h=match_team(m['homeTeam'].get('name')); a=match_team(m['awayTeam'].get('name'))
    if not h or not a: continue
    ft=m.get('score',{}).get('fullTime',{}); hg,ag=ft.get('home'),ft.get('away')
    if hg is None or ag is None: continue
    if (h,a) in pair2mid: mid=pair2mid[(h,a)]; res=[hg,ag]
    elif (a,h) in pair2mid: mid=pair2mid[(a,h)]; res=[ag,hg]
    else: continue
    group[str(mid)]=res; g_added+=1; api_final_group[str(mid)]=res

# --- group standings (FIFA order: pts, GD, GF, then head-to-head, then name) -> position codes ---
#     Needed to anchor R32 slots: each slot's HOME is a fixed group position (e.g. "1I" = winner I).
def standings(g):
    teams=GROUPS[g]; T={t:{'pts':0,'gf':0,'ga':0} for t in teams}; ms=[]
    for mid,(h,a) in FIX.items():
        if h in T and a in T and str(mid) in group:
            hg,ag=group[str(mid)]; ms.append((h,a,hg,ag))
            T[h]['gf']+=hg;T[h]['ga']+=ag;T[a]['gf']+=ag;T[a]['ga']+=hg
            if hg>ag:T[h]['pts']+=3
            elif ag>hg:T[a]['pts']+=3
            else:T[h]['pts']+=1;T[a]['pts']+=1
    if len(ms)<6: return None        # group not complete yet
    for t in T: T[t]['gd']=T[t]['gf']-T[t]['ga']
    order=sorted(teams,key=lambda t:(-T[t]['pts'],-T[t]['gd'],-T[t]['gf'],t))
    i=0                              # break pts/GD/GF ties by head-to-head among the tied teams
    while i<len(order):
        j=i+1
        while j<len(order) and (T[order[j]]['pts'],T[order[j]]['gd'],T[order[j]]['gf'])==(T[order[i]]['pts'],T[order[i]]['gd'],T[order[i]]['gf']): j+=1
        if j-i>1:
            cl=order[i:j]; M={t:{'p':0,'gd':0,'gf':0} for t in cl}
            for h,a,hg,ag in ms:
                if h in M and a in M:
                    M[h]['gf']+=hg;M[h]['gd']+=hg-ag;M[a]['gf']+=ag;M[a]['gd']+=ag-hg
                    if hg>ag:M[h]['p']+=3
                    elif ag>hg:M[a]['p']+=3
                    else:M[h]['p']+=1;M[a]['p']+=1
            order[i:j]=sorted(cl,key=lambda t:(-M[t]['p'],-M[t]['gd'],-M[t]['gf'],t))
        i=j
    return order
POS={}                               # "1A"/"2A"/"3A" -> team (for completed groups)
for g in GROUPS:
    o=standings(g)
    if o: POS['1'+g],POS['2'+g],POS['3'+g]=o[0],o[1],o[2]

# --- knockouts: key each slot by BRACKET POSITION (not kickoff order) so a prediction and its
#     actual refer to the SAME bracket pairing. Resolve each slot's expected HOME team, then find
#     the API match (of that round) containing it and orient home/away to the wiring. ---
def api_by_stage(stage):
    out=[]
    for m in matches:
        if m.get('stage')!=stage: continue
        h=match_team(m['homeTeam'].get('name')); a=match_team(m['awayTeam'].get('name'))
        ft=m.get('score',{}).get('fullTime',{}); w=m.get('score',{}).get('winner')
        out.append({'h':h,'a':a,'hg':ft.get('home'),'ag':ft.get('away'),'w':w,'st':m.get('status')})
    return out
API_STAGE={st:api_by_stage(st) for st in set(MID_STAGE.values())}
def adv_of(mid):                     # advancing team recorded for a slot (None if undecided)
    e=ko.get(str(mid)); return e[4] if e else None
def loser_of(mid):
    e=ko.get(str(mid))
    if not e or e[4] is None: return None
    return e[1] if e[4]==e[0] else e[0]

k_added=0; unmatched_team=0; k_sched=0; api_final_ko={}
for mid in KO_ORDER:
    stage=MID_STAGE[mid]
    # expected HOME (and, for 3rd/final, AWAY) team for this slot, from the bracket wiring
    if mid in R32_HOME: home_exp,away_exp=POS.get(R32_HOME[mid]),None
    elif mid in FEEDERS: home_exp,away_exp=adv_of(FEEDERS[mid][0]),adv_of(FEEDERS[mid][1])
    elif mid in THIRD: home_exp,away_exp=loser_of(THIRD[mid][0]),loser_of(THIRD[mid][1])
    elif mid in FINAL: home_exp,away_exp=adv_of(FINAL[mid][0]),adv_of(FINAL[mid][1])
    else: continue
    if not home_exp: continue        # feeders/group not resolved yet -> slot stays empty
    # find the API match (this round) that contains the expected home team
    m=next((x for x in API_STAGE[stage] if home_exp in (x['h'],x['a'])),None)
    if not m: continue
    H,A=m['h'],m['a']; hg,ag,w=m['hg'],m['ag'],m['w']
    if A==home_exp:                  # orient to wiring's home/away (swap API orientation if needed)
        H,A=A,H
        if hg is not None: hg,ag=ag,hg
        w={'HOME_TEAM':'AWAY_TEAM','AWAY_TEAM':'HOME_TEAM'}.get(w,w)
    if m['st']=='FINISHED' and hg is not None and ag is not None:
        adv=H if w=='HOME_TEAM' else A if w=='AWAY_TEAM' else None
        ko[str(mid)]=[H,A,hg,ag,adv]; k_added+=1; api_final_ko[str(mid)]=[H,A,hg,ag,adv]
    elif H and A:                    # matchup set but not played -> show teams, no score
        ko[str(mid)]=[H,A,None,None,None]; k_sched+=1

# --- manual overrides: corrections for API errors / early-show. Applied LAST so they win and
#     persist across fetches. Edit overrides.json to add; see its _comment for the format.
#     AUTO-PRUNE RULE: an override is removed automatically once the API reports that match
#     FINISHED *and* with a score matching the override (then the API serves it on its own).
#     An override over a still-wrong-but-FINISHED API value is kept (API disagrees). ---
ov_g=ov_k=0; pruned=[]
try:
    ov=json.load(open(os.path.join(ROOT,'overrides.json')))
    og=ov.get('group') or {}; ok=ov.get('ko') or {}
    for mid in list(og.keys()):
        if api_final_group.get(str(mid))==og[mid]: pruned.append('group/'+str(mid)); del og[mid]
        else: group[str(mid)]=og[mid]; ov_g+=1
    for mid in list(ok.keys()):
        if api_final_ko.get(str(mid))==ok[mid]: pruned.append('ko/'+str(mid)); del ok[mid]
        else: ko[str(mid)]=ok[mid]; ov_k+=1
    if pruned:                      # rewrite overrides.json without the now-redundant entries
        ov['group']=og; ov['ko']=ok
        json.dump(ov, open(os.path.join(ROOT,'overrides.json'),'w'), ensure_ascii=False, indent=2)
        open(os.path.join(ROOT,'overrides.json'),'a').write('\n')
except FileNotFoundError:
    pass
except Exception as e:
    print('WARNING: overrides.json present but unreadable, ignoring:', e)

out={'group':group,'ko':ko}
json.dump(out,open(os.path.join(ROOT,'results.json'),'w'),ensure_ascii=False,indent=0)
print(f'updated results.json — group: {g_added} matched ({len(group)} total) · '
      f'ko: {k_added} played, {k_sched} matchups scheduled ({len(ko)} total)'
      + (f' · overrides applied: {ov_g} group, {ov_k} ko' if (ov_g or ov_k) else '')
      + (f' · overrides auto-removed (API now final & matching): {", ".join(pruned)}' if pruned else '')
      + (f' · {unmatched_team} ko match(es) had unrecognized team names' if unmatched_team else ''))
