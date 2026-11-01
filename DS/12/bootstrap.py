from pathlib import Path
import shutil,json
r=Path.cwd()
for d in ['data','index','static','tests','results','figures','work','runtime/conf','runtime/logs','runtime/data','runtime/run','runtime/plugins']:(r/d).mkdir(parents=True,exist_ok=True)
for name in ['nodes.json','relationships.json']:shutil.copy2(Path('D:/LNU/DS/8/data')/name,r/'data'/name)
for name in ['vectors.faiss','metadata.json']:shutil.copy2(Path('D:/LNU/DS/11/index/fixed')/name,r/'index'/name)
shutil.copy2('D:/LNU/DS/11/download_models.py',r/'download_models.py')
shutil.copy2('D:/downloads/ЛР12_завдання.pdf',r/'data/assignment12.pdf')
(r/'runtime/conf/neo4j.conf').write_text('''server.default_listen_address=127.0.0.1
server.bolt.enabled=true
server.bolt.listen_address=127.0.0.1:17692
server.bolt.advertised_address=127.0.0.1:17692
server.http.enabled=false
server.https.enabled=false
dbms.security.auth_enabled=false
server.memory.heap.initial_size=256m
server.memory.heap.max_size=768m
server.memory.pagecache.size=128m
dbms.usage_report.enabled=false
server.jvm.additional=-Dio.netty.noUnsafe=true
''')
print('Copied inherited corpus/index/graph')
