from pathlib import Path
import argparse
import secrets

p = argparse.ArgumentParser()
p.add_argument('--models-dir', default='./models')
args = p.parse_args()
path = Path(__file__).parent / '.env'
if path.exists():
    raise SystemExit('.env already exists; preserved without changes')
path.write_text('NEO4J_PASSWORD=' + secrets.token_hex(24) +
                '\nNEO4J_USER=neo4j\nNEO4J_DATABASE=neo4j\nMODELS_DIR=' +
                args.models_dir.replace('\\', '/') + '\n', encoding='utf-8')
print('Created .env; password was not printed')
