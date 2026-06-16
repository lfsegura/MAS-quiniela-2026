#!/usr/bin/env python3
# Pulls FINISHED World Cup group-stage match results from football-data.org and writes ../results.json
# Requires env FOOTBALL_DATA_TOKEN (free at https://www.football-data.org/client/register)
import os,json,unicodedata,urllib.request,sys
HERE=os.path.dirname(os.path.abspath(__file__)); ROOT=os.path.dirname(HERE)
cfg=json.load(open(os.path.join(HERE,'fixtures.json')))
FIX={int(k):v for k,v in cfg['fixtures'].items()}; ALIAS=cfg['alias']
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
    n=norm(name)
    if n in A2ES: return A2ES[n]
    for k,es in A2ES.items():
        if k and (k in n or n in k): return es
    return None
TOKEN=os.environ.get('FOOTBALL_DATA_TOKEN')
if not TOKEN: print('Missing FOOTBALL_DATA_TOKEN'); sys.exit(1)
req=urllib.request.Request('https://api.football-data.org/v4/competitions/WC/matches',headers={'X-Auth-Token':TOKEN})
api=json.load(urllib.request.urlopen(req,timeout=30))
# pair (home_es,away_es)->mid for fast lookup (both orientations)
pair2mid={}
for mid,(h,a) in FIX.items(): pair2mid[(h,a)]=mid
results=json.load(open(os.path.join(ROOT,'results.json')))  # keep existing, overlay new
added=0
for m in api.get('matches',[]):
    if m.get('status')!='FINISHED': continue
    h=match_team(m['homeTeam'].get('name') or ''); a=match_team(m['awayTeam'].get('name') or '')
    if not h or not a: continue
    ft=m.get('score',{}).get('fullTime',{}); hg,ag=ft.get('home'),ft.get('away')
    if hg is None or ag is None: continue
    if (h,a) in pair2mid: mid=pair2mid[(h,a)]; res=[hg,ag]
    elif (a,h) in pair2mid: mid=pair2mid[(a,h)]; res=[ag,hg]
    else: continue
    results[str(mid)]=res; added+=1
json.dump(results,open(os.path.join(ROOT,'results.json'),'w'),ensure_ascii=False,indent=0)
print(f'updated results.json ({added} finished matches matched, {len(results)} total)')
