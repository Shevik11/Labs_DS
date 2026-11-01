from pathlib import Path
p=Path('engine.py');s=p.read_text('utf-8-sig').replace('self.index.search(v,min(k,self.index.ntotal))','self.index.search(v,self.index.ntotal)').replace("if i>=0]","if i>=0 and self.chunks[int(i)]['language']=='en'][:k]")
s=s.replace('|VISUALIZES|HAS_METRIC','').replace('budget=360','budget=260')
s=s.replace("text=self.tokenizer.decode(tokens[:room],skip_special_tokens=True)","offsets=self.tokenizer(text,add_special_tokens=False,return_offsets_mapping=True)['offset_mapping']\n    text=text[:offsets[room-1][1]]")
p.write_text(s,'utf-8')
