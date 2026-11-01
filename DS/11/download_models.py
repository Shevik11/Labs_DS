from pathlib import Path
import os
os.environ['HF_HUB_DISABLE_XET']='1'
from huggingface_hub import snapshot_download
ROOT=Path(__file__).resolve().parent
MODELS=[
 ('sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2','embedding','e8f8c211226b894fcb81acc59f3b34ba3efd5f42'),
 ('google/flan-t5-small','llm','0fc9ddf78a1e988dac52e2dac162b0ede4fd74ab'),
]
for repo,folder,revision in MODELS:
    snapshot_download(repo,revision=revision,local_dir=ROOT/'models'/folder,
                      allow_patterns=['*.json','*.txt','*.model','*.safetensors','README.md'],
                      ignore_patterns=['onnx/*','openvino/*','tf_*','flax*'])
