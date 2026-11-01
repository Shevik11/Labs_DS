"""Download only public model weights; all caches remain inside this lab."""
import os
from pathlib import Path
ROOT = Path(__file__).resolve().parent
os.environ['HF_HOME'] = str(ROOT / 'models' / 'cache')
os.environ['HF_HUB_DISABLE_XET'] = '1'
import json
from huggingface_hub import snapshot_download
models = {'encoder': 'intfloat/multilingual-e5-small', 'generator': 'Qwen/Qwen3-0.6B'}
metadata = {}
for folder, repo in models.items():
    print('Resolving', repo, flush=True)
    revision = {'encoder': '614241f622f53c4eeff9890bdc4f31cfecc418b3', 'generator': 'c1899de289a04d12100db370d81485cdf75e47ca'}[folder]
    snapshot_download(repo, revision=revision, local_dir=ROOT / 'models' / folder,
        allow_patterns=['*.json', '*.safetensors', 'tokenizer.model', 'sentencepiece.bpe.model', '*.txt', 'README.md'],
        max_workers=3)
    metadata[folder] = {'repo': repo, 'revision': revision}
    (ROOT / 'models' / 'metadata.json').write_text(json.dumps(metadata, indent=2), encoding='utf-8')
    print('Ready:', folder, revision, flush=True)

