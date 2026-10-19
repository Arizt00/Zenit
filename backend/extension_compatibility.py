"""Evidence is scoped to the exact reviewed VSIX, never inferred from activation."""
import json
from functools import lru_cache
from pathlib import Path

@lru_cache(maxsize=1)
def matrix():
 try:
  file=Path(__file__).resolve().parents[1]/'config/extension-compatibility.json'
  if file.stat().st_size>1000000:return {}
  data=json.loads(file.read_text(encoding='utf-8'));return {row['id'].casefold():row for row in data['packages']}
 except (OSError,ValueError,KeyError,TypeError):return {}
def evidence(item):
 row=matrix().get(str(item.get('id','')).casefold())
 if row and row.get('version')==item.get('version') and row.get('sha256')==item.get('sha256'):return row
 return {'verified':False,'tested':[],'notVerified':['Esta versión y huella del paquete no tienen pruebas registradas en esta entrega.']}
