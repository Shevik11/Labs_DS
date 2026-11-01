from pathlib import Path
import hashlib,json,zipfile
r=Path(__file__).resolve().parent
stem='ЛР14_Шевчук_ФЕІм-13с'
checks={
 '1_containers':dict(evidence=['Dockerfile','docker-compose.yml','results/container_evidence.json','results/import.json'],verified=True),
 '2_telemetry':dict(evidence=['results/load_summary.json','results/metrics_verification.json','results/metrics_after.prom','results/requests.jsonl'],verified=True),
 '3_drift':dict(evidence=['results/drift.json','results/weeks.json','data/reference_manifest.json','figures/psi_weeks.png'],verified=True),
 '4_alerts':dict(evidence=['results/alerts.json','results/false_alarms.json','results/fault_injection.json','results/tests.txt'],verified=True),
 '5_operations_plan':dict(evidence=['RUNBOOK.md','DEPLOYMENT.md','DATA_CONTRACT.md','AI_DECLARATION.md'],verified=True,scope='documents; blue-green is proposed, not deployed')}
for value in checks.values():
    assert all((r/name).is_file() for name in value['evidence'])
(r/'results/requirement_matrix.json').write_text(json.dumps(checks,ensure_ascii=False,indent=2),'utf-8')
p=r/'data/provenance.json';provenance=json.loads(p.read_text('utf-8'))
for item in provenance:
    item['destination_sha256']=hashlib.sha256((r/item['destination']).read_bytes()).hexdigest()
    item['modified_for_lab14']=item['destination_sha256']!=item['source_sha256']
p.write_text(json.dumps(provenance,ensure_ascii=False,indent=2),'utf-8')
roots=['README.md','RUNBOOK.md','DEPLOYMENT.md','DATA_CONTRACT.md','AI_DECLARATION.md',
 'Dockerfile','docker-compose.yml','.dockerignore','.gitignore','.env.example',
 'requirements.txt','requirements-lock.txt','requirements-report.txt',
 'app.py','engine.py','import_graph.py','download_models.py','telemetry.py','drift.py',
 'monitor.py','load_test.py','fault_injection.py','setup_env.py','verify_results.py',
 'build_report.py','render_pdf.py','package_lab.py',stem+'.pdf']
files=[r/name for name in roots]
for folder in ['data','index','static','figures','sources','tests','results']:
    files.extend(p for p in (r/folder).rglob('*') if p.is_file()
                 and '__pycache__' not in p.parts and '.pytest_cache' not in p.parts)
assert all(p.is_file() for p in files)
manifest={p.relative_to(r).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
(r/'MANIFEST.sha256.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),'utf-8')
files.append(r/'MANIFEST.sha256.json')
secret=dict(line.split('=',1) for line in (r/'.env').read_text('utf-8').splitlines() if '=' in line)['NEO4J_PASSWORD'].encode()
for path in files:
    assert path.name!='.env' and secret not in path.read_bytes(), 'Secret would enter ZIP'
archive=r/(stem+'.zip')
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
    for path in files:z.write(path,path.relative_to(r).as_posix())
with zipfile.ZipFile(archive) as z:
    assert z.testzip() is None
    assert '.env' not in z.namelist() and not any(n.startswith(('models/','work/')) for n in z.namelist())
    assert len(z.namelist())==len(set(z.namelist()))
    for name,digest in manifest.items():assert hashlib.sha256(z.read(name)).hexdigest()==digest
(r/'results/package_validation.json').write_text(json.dumps(dict(
 file_count=len(files),zip_bytes=archive.stat().st_size,crc_ok=True,
 hashes_verified=True,real_password_absent=True,model_weights_absent=True,
 work_files_absent=True),indent=2),'utf-8')
print('Verified ZIP:',len(files),'files,',round(archive.stat().st_size/1024**2,2),'MiB')
