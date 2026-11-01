from pathlib import Path
import json,subprocess,urllib.request,hashlib,statistics
import numpy as np
from prometheus_client.parser import text_string_to_metric_families
R=Path(__file__).resolve().parent

def docker(*args):
    return subprocess.check_output(['docker',*args],cwd=R,text=True,encoding='utf-8')
def save(name,value):
    (R/name).write_text(json.dumps(value,ensure_ascii=False,indent=2),'utf-8')
def samples(name):
    return {(s.name,tuple(sorted(s.labels.items()))):s.value
            for f in text_string_to_metric_families((R/name).read_text('utf-8')) for s in f.samples}
rows=json.loads((R/'results/load_requests.json').read_text('utf-8'))
summary=json.loads((R/'results/load_summary.json').read_text('utf-8'))
good=[r['seconds'] for r in rows if r['status']==200]
summary.update(success_p95_seconds=float(np.quantile(good,.95)),
               success_mean_seconds=statistics.mean(good),
               first_request_seconds=rows[0]['seconds'],
               design='50 serial HTTP requests inside API container; 45 real generations + 5 intentional 422; models loaded, first inference not warmed separately')
save('results/load_summary.json',summary)
before=samples('results/metrics_before.prom'); after=samples('results/metrics_after.prom')
def delta(name,**labels):
    key=(name,tuple(sorted(labels.items())))
    return after.get(key,0)-before.get(key,0)
assert delta('lab14_requests_total',route='/ask',status='200')==45
assert delta('lab14_requests_total',route='/ask',status='422')==5
assert delta('lab14_errors_total',route='/ask',status='422')==5
assert delta('lab14_latency_seconds_count',route='/ask')==50
assert delta('lab14_tokens_total',kind='input')==summary['input_tokens']
assert delta('lab14_tokens_total',kind='output')==summary['output_tokens']
logs=[json.loads(line) for line in (R/'results/requests.jsonl').read_text('utf-8').splitlines()]
byid={line['request_id']:line for line in logs}
assert len(rows)==50 and all(row['status']==row['expected_status'] for row in rows)
for row in rows:
    entry=byid[row['response']['request_id']]
    assert entry['status']==row['status']
    assert all(key in entry for key in ['timestamp','request_id','model_version','prompt_version','duration_ms','tokens'])
    assert entry['tokens']==row['response'].get('prompt_tokens',0)+row['response'].get('output_tokens',0)
    assert not {'question','answer','password'}&entry.keys()
health=json.loads(urllib.request.urlopen('http://127.0.0.1:8144/health',timeout=20).read())
assert health['status']=='ok' and health['faiss']==38
save('results/metrics_verification.json',dict(passed=True,matched_requests=50,
     delta_requests_200=45,delta_requests_422=5,delta_histogram_count=50,
     input_tokens=summary['input_tokens'],output_tokens=summary['output_tokens'],
     request_id_join='all 50 API responses match JSON logs',health=health))
ps=[json.loads(line) for line in docker('compose','-p','lnu-ds14','ps','--format','json').splitlines() if line.strip()]
images={}
for tag in ['lnu-ds14-api:1.0','neo4j:5.26.32-community']:
    info=json.loads(docker('image','inspect',tag))[0]
    images[tag]=dict(id=info['Id'],repo_digests=info.get('RepoDigests',[]),user=info['Config'].get('User'))
save('results/container_evidence.json',dict(containers=ps,images=images,
     engine=docker('version','--format','{{.Server.Version}}').strip(),
     docker_data_location='D:/DockerDesktop/wsl/disk/docker_data.vhdx',
     published_health=health,
     files={n:hashlib.sha256((R/n).read_bytes()).hexdigest()
            for n in ['Dockerfile','docker-compose.yml','index/vectors.faiss','data/nodes.json','data/relationships.json']}))
lock=R/'results/requirements-lock.txt'
(R/'requirements-lock.txt').write_text(lock.read_text('utf-8'),'utf-8')
print(json.dumps(summary,indent=2)); print('Metric counters, histogram, tokens and logs verified')

