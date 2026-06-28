#!/usr/bin/env python3
# Knockout sanity-check. Prints each knockout match as PUBLISHED on the tracker (teams, score,
# advancing team) so you can eyeball it against what actually happened. If FOOTBALL_DATA_TOKEN is
# set, it also flags any mismatch vs the live API. Penalty/level-score games are flagged for an
# extra look (the advancing team is the one spot the feed can get subtly wrong).
#   Run:  FOOTBALL_DATA_TOKEN=xxxx python3 scripts/check_ko.py     (token optional)
import os, json, subprocess

SITE = "https://lfsegura.github.io/MAS-quiniela-2026/results.json"
def rnd(m): return 'R32' if m<=88 else 'R16' if m<=96 else 'QF' if m<=100 else 'SF' if m<=102 else ('3er puesto' if m==103 else 'Final')
def curl_json(url, headers=None):
    cmd=['curl','-s']+(sum((['-H',f'{k}: {v}'] for k,v in (headers or {}).items()),[]))+[url]
    out=subprocess.run(cmd,capture_output=True,text=True,timeout=30).stdout
    try: return json.loads(out)
    except Exception: return None

ko=(curl_json(SITE+'?ts='+str(os.getpid())) or {}).get('ko',{})
tok=os.environ.get('FOOTBALL_DATA_TOKEN'); api={}
if tok:
    data=curl_json('https://api.football-data.org/v4/competitions/WC/matches',{'X-Auth-Token':tok})
    if data:
        STAGE={'LAST_32':range(73,89),'LAST_16':range(89,97),'QUARTER_FINALS':range(97,101),
               'SEMI_FINALS':[101,102],'THIRD_PLACE':[103],'FINAL':[104]}
        for st,mids in STAGE.items():
            sm=sorted([m for m in data['matches'] if m['stage']==st],key=lambda m:(m['utcDate'],m['id']))
            for mid,m in zip(mids,sm):
                api[mid]={'st':m['status'],'ft':m['score']['fullTime']}

print("Auditoría de eliminatorias — lo PUBLICADO en el tablero:\n")
played=False
for mid in range(73,105):
    e=ko.get(str(mid))
    if not e: continue
    if e[2] is None:
        print(f"  {rnd(mid):11} mid{mid}: {e[0]} vs {e[1]}   (cruce definido, sin jugar)"); continue
    played=True
    adv=e[4] or ('—' if e[2]==e[3] else (e[0] if e[2]>e[3] else e[1]))
    line=f"  {rnd(mid):11} mid{mid}: {e[0]} {e[2]}-{e[3]} {e[1]}  · avanza: {adv}"
    if e[2]==e[3]: line+="   ⚠️ empate→penales: verifica quién avanza"
    a=api.get(mid)
    if a and a['st']=='FINISHED' and [a['ft']['home'],a['ft']['away']]!=[e[2],e[3]]:
        line+=f"   ⚠️ API dice {a['ft']['home']}-{a['ft']['away']} (override o desfase)"
    print(line)
if not played: print("  (aún no hay partidos de eliminatoria jugados)")
print("\nRevisa cada marcador contra el resultado real. Si algo está mal → edítalo en overrides.json.")
