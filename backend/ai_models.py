"""Pinned optional GGUF catalog, using Zénit's resumable, hash-verified downloads."""
from pathlib import Path

MODEL_CATALOG = ({
    'id': 'Qwen3.8-27B-Uncensored-Q4_K_M',
    'name': 'Qwen 3.8 · 27B Uncensored',
    'file': 'Qwen3.8-27B-Uncensored-Q4_K_M.gguf',
    'repository': 'JonathanColetti/Qwen3.8-27B-Uncensored-GGUF',
    'revision': '45d0fc0ad6cfcf9eeee6008ddaea925536409b18',
    'sha256': '4c5e2db039e9325ac7724c8846c71356a24ad1cdfa28002d73ecb6be645f9675',
    'bytes': 16810714528,
    'parameters': '27B', 'quantization': 'Q4_K_M', 'license': 'Apache-2.0',
},)


class AIModels:
    def __init__(self, downloads):
        self.downloads = downloads

    def entry(self, ident):
        model = next((model for model in MODEL_CATALOG if model['id'] == ident), None)
        if model is None:raise ValueError('Modelo local desconocido.')
        return dict(model)

    @staticmethod
    def url(model):
        return f"https://huggingface.co/{model['repository']}/resolve/{model['revision']}/{model['file']}"

    def download(self, model):
        return next((item for item in self.downloads.snapshot()['items']
                     if item['name'] == model['file'] and item['url'] == self.url(model)
                     and item['sha256'] == model['sha256']), None)

    def ready(self, model, download):
        if not download or download['status'] != 'complete':return False
        try:
            file = Path(download['path']);stat = file.stat()
            if (stat.st_size != model['bytes'] or download.get('verifiedSize') != stat.st_size
                    or download.get('verifiedMtimeNs') != stat.st_mtime_ns):return False
            with file.open('rb') as stream:return stream.read(4) == b'GGUF'
        except (OSError, KeyError):return False

    def status(self):
        entries = []
        for model in MODEL_CATALOG:
            download = self.download(model);ready = self.ready(model, download)
            entries.append({**model, 'source': f"https://huggingface.co/{model['repository']}",
                            'ready': ready, 'download': download,
                            'ollama': f"hf.co/{model['repository']}:Q4_K_M"})
        return {'models': entries}

    def specifications(self):
        return [{**model, 'path': model['download']['path']} for model in self.status()['models'] if model['ready']]

    def specification(self, ident):
        if not any(model['id'] == ident for model in MODEL_CATALOG):return None
        model = self.entry(ident);download = self.download(model)
        if not self.ready(model, download):
            raise ValueError('Descarga y verifica este GGUF en Ajustes → Inteligencia artificial → Modelos locales antes de usarlo.')
        return {**model, 'path': download['path']}

    def start(self, ident, consent=False):
        if consent is not True:raise PermissionError('Autoriza la descarga del modelo local.')
        model = self.entry(ident);download = self.download(model)
        if download:
            if download['status'] in ('paused', 'error'):return self.downloads.resume(download['id'])
            if download['status'] == 'complete' and not self.ready(model, download):
                raise ValueError('El GGUF descargado cambió. Conserva el archivo y descarga una copia verificada con el gestor de descargas.')
            return download
        return self.downloads.start(self.url(model), model['file'], model['sha256'])
