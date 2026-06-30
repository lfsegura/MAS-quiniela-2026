#!/usr/bin/env python3
# Pulls FINISHED World Cup results from football-data.org and writes ../results.json
#   results.json = {"group": {"<mid>":[h,a]}, "ko": {"<mid>":[homeES,awayES,h,a,advES(,penH,penA)]}}
#   Knockout scoreline (h,a) = on-pitch result (regulation+extra time), NEVER the penalty-inflated
#   fullTime. A shootout is recorded as the level draw + optional [penH,penA] tally (FIFA "1(4)").
#   advES = advancing team (penalty winner); left null if the feed's shootout is tied/undecided.
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
        out.append({'h':h,'a':a,'score':m.get('score',{}) or {},'st':m.get('status')})
    return out
API_STAGE={st:api_by_stage(st) for st in set(MID_STAGE.values())}
# Load knockout overrides early so the bracket wiring sees a manually-set advancer and propagates it
# into later rounds (e.g. a penalty winner we fixed by hand). The values are also applied at the end.
try: OVK={str(k):v for k,v in ((json.load(open(os.path.join(ROOT,'overrides.json'))).get('ko')) or {}).items()}
except Exception: OVK={}
def _slot(mid): return OVK.get(str(mid)) or ko.get(str(mid))   # manual override wins over API-derived
def adv_of(mid):                     # advancing team recorded for a slot (None if undecided)
    e=_slot(mid); return e[4] if (e and len(e)>4) else None
def loser_of(mid):
    e=_slot(mid)
    if not e or len(e)<5 or e[4] is None: return None
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
    if not home_exp: continue        # feeding round not resolved yet -> slot stays empty
    is_r32 = mid in R32_HOME
    # find the API match (this round) containing the known home team (used for the SCORE; and for
    # R32 teams). May not exist yet for later rounds -> we still show the pairing from the wiring.
    m=next((x for x in API_STAGE[stage] if home_exp in (x['h'],x['a'])),None)
    s=m['score'] if m else {}; st=m['st'] if m else None; swap=bool(m) and (m['a']==home_exp)
    def ori(d):                      # read a score sub-dict in the wiring's home/away orientation
        d=d or {}; hv,av=d.get('home'),d.get('away'); return (av,hv) if swap else (hv,av)
    # MATCHUP TEAMS: R32 come from the API fixture (3rd-place slots resolved by FIFA's allocation);
    # R16+ come from our own bracket wiring (the feeder winners), so a pairing shows the moment both
    # feeder games are decided -- the feed often lags and leaves the next round's away team blank.
    if is_r32:
        H,A=(m['a'],m['h']) if swap else (m['h'],m['a']) if m else (home_exp,None)
    else:
        H,A=home_exp, (away_exp or ((m['h'] if swap else m['a']) if m else None))
    if st=='FINISHED':
        # SCORELINE = on-pitch result (regulation + extra time), NOT the penalty-inflated fullTime.
        # This is what the Excel grades (sign/goals/exact); a shootout shows as the level draw.
        rh,ra=ori(s.get('regularTime')); eh,ea=ori(s.get('extraTime')); fh,fa=ori(s.get('fullTime'))
        w=s.get('winner')
        if swap: w={'HOME_TEAM':'AWAY_TEAM','AWAY_TEAM':'HOME_TEAM'}.get(w,w)
        if rh is not None: hg,ag=rh+(eh or 0),ra+(ea or 0)
        else: hg,ag=fh,fa
        if hg is None or ag is None:
            if H and A: ko[str(mid)]=[H,A,None,None,None]; k_sched+=1
            continue
        adv=H if w=='HOME_TEAM' else A if w=='AWAY_TEAM' else None
        # penalty shootout: tally = fullTime - on-pitch, recorded only when level AND decided.
        # If the feed gives a tied/invalid shootout, leave pens+adv blank (don't guess a winner).
        penH=penA=None
        shootout=(s.get('duration')=='PENALTY_SHOOTOUT') or (hg==ag and fh is not None and (fh,fa)!=(hg,ag))
        if shootout and fh is not None:
            ph,pa=fh-hg,fa-ag
            if ph>=0 and pa>=0 and ph!=pa:
                penH,penA=ph,pa
                if adv is None: adv=H if ph>pa else A
        if adv is None and hg!=ag: adv=H if hg>ag else A
        entry=[H,A,hg,ag,adv]+([penH,penA] if penH is not None else [])
        ko[str(mid)]=entry; k_added+=1; api_final_ko[str(mid)]=entry
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
