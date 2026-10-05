'''
pip install transformers torch
pulled the ~250 MB model into your local cache (~/.cache/huggingface)
'''
from transformers import AutoTokenizer, AutoModel
tok = AutoTokenizer.from_pretrained("distilbert-base-cased")
model = AutoModel.from_pretrained("distilbert-base-cased")
print("loaded ok")