"""Five evidence tools; local calculations precede optional AI consultation."""
import ast
import difflib
import hashlib
import json
import re
import time


def research(ws, body):
    action = body.get('action'); path = body.get('path'); content = body.get('content')
    if action not in ('capsule', 'drift', 'impact', 'faults', 'handoff'):
        raise ValueError('Unknown Melody tool.')
    if not isinstance(path, str) or not isinstance(content, str) or len(content.encode('utf-8')) > 300000:
        raise ValueError('Open a text file up to 300 kB to use this tool.')
    ws.resolve(path)
    diagnostics = body.get('diagnostics', [])
    if not isinstance(diagnostics, list) or len(diagnostics) > 500:
        raise ValueError('Too many diagnostics.')
    diagnostics = [{k: str(d.get(k, ''))[:1000] for k in ('message', 'line', 'severity', 'path')}
                   for d in diagnostics if isinstance(d, dict)]
    digest = hashlib.sha256(content.encode()).hexdigest()
    ws.private_dir('melody')
    storage = ws.resolve('.lumen/melody/capsules.json', must_exist=False)
    with ws.lock:
        if storage.exists() and storage.stat().st_size > 5_000_000:
            raise ValueError('The capsule store exceeds its size limit.')
        try:
            capsules = json.loads(storage.read_text('utf-8')) if storage.exists() else []
            if not isinstance(capsules, list): capsules = []
        except (OSError, ValueError): capsules = []
        capsules = [x for x in capsules[-12:] if isinstance(x, dict) and isinstance(x.get('path'), str)
                    and isinstance(x.get('content'), str) and len(x['content'].encode()) <= 300000
                    and isinstance(x.get('id'), str) and isinstance(x.get('sha256'), str)]
        previous = next((x for x in reversed(capsules) if x.get('path') == path), None)
        base = {'tool': action, 'path': path, 'sha256': digest, 'unsavedBuffer': True}
        if action == 'capsule':
            capsule = {**base, 'id': str(time.time_ns()), 'created': time.time(), 'content': content,
                       'diagnostics': diagnostics, 'output': str(body.get('output', ''))[-6000:]}
            capsules = (capsules + [capsule])[-12:]
            from .preferences import atomic_json
            atomic_json(storage, capsules)
            return {**base, 'id': capsule['id'], 'summary': 'Frozen source, diagnostics and output. Kept locally in this project.', 'stored': len(capsules)}
        if action == 'drift':
            if not previous: raise ValueError('Freeze an evidence capsule for this file first.')
            lines = list(difflib.unified_diff(previous['content'].splitlines(), content.splitlines(), fromfile='capsule', tofile='current buffer', n=3))
            return {**base, 'capsule': previous['id'], 'changed': digest != previous['sha256'], 'diff': '\n'.join(lines)[:60000], 'truncated': len('\n'.join(lines)) > 60000,
                    'summary': 'Exact source changes since the latest capsule; no files changed.'}
        if action == 'faults':
            groups = {}
            for item in diagnostics:
                key = re.sub(r'\d+', '#', item['message']).strip()
                groups.setdefault(key, []).append(item)
            output = str(body.get('output', ''))[-6000:]
            return {**base, 'groups': [{'signature': key, 'evidence': rows} for key, rows in groups.items()],
                    'outputSignals': [line for line in output.splitlines() if re.search(r'error|exception|failed|traceback', line, re.I)][:30],
                    'summary': 'Grouped observed diagnostics and execution signals. These are evidence, not a root-cause verdict.'}
        if action == 'handoff':
            brief = f'# Session handoff\n\nFile: `{path}`\nBuffer SHA-256: `{digest}`\n\n'
            brief += ('Latest capsule: ' + previous['id'] + (' · source changed' if previous['sha256'] != digest else ' · source unchanged') + '\n\n') if previous else 'No baseline capsule.\n\n'
            brief += '## Open diagnostics\n' + ('\n'.join('- ' + d['severity'] + ' · line ' + d['line'] + ': ' + d['message'] for d in diagnostics) or 'No editor diagnostics supplied.')
            brief += '\n\n## Execution evidence\n```text\n' + str(body.get('output', ''))[-6000:].replace('```', "'''") + '\n```\n\n## Next decision\nRecord the intended behavior and the next verification before handing this session over.\n'
            return {**base, 'brief': brief, 'summary': 'A portable, editable brief from current evidence. Copy it when ready.'}
    # Bounded static relation scan. Python imports use the AST; other languages
    # expose literal reference evidence, never claimed runtime dependencies.
    stem = path.replace('\\', '/').split('/')[-1].rsplit('.', 1)[0]
    relations = []; files = ws.files(); scanned = 0
    for name in files:
        if scanned >= 120 or len(relations) >= 80: break
        if not re.search(r'\.(py|pyw|js|ts|jsx|tsx|java|cs|c|h|cpp|rs|go|nc|n)$', name, re.I): continue
        scanned += 1
        try: text = content if name == path else ws.read(name)['content']
        except (OSError, ValueError): continue
        if name.endswith(('.py', '.pyw')):
            try:
                for node in ast.walk(ast.parse(text)):
                    modules = [x.name for x in node.names] if isinstance(node, ast.Import) else [node.module or ''] if isinstance(node, ast.ImportFrom) else []
                    for module in modules:
                        if name == path or stem in module.split('.'):
                            relations.append({'path': name, 'line': node.lineno, 'reference': module, 'kind': 'Python import (static)'})
            except SyntaxError: pass
        else:
            for number, line in enumerate(text.splitlines(), 1):
                if re.search(r'\b(import|include|require|use|using)\b', line) and (name == path or re.search(r'\b' + re.escape(stem) + r'\b', line)):
                    relations.append({'path': name, 'line': number, 'reference': line.strip()[:300], 'kind': 'Literal reference (unresolved)'})
                if len(relations) >= 80: break
    return {**base, 'relations': relations[:80], 'scanned': scanned, 'truncated': scanned < len(files) or len(relations) >= 80,
            'summary': 'Static reference evidence around this file. Dynamic imports and runtime relationships are not inferred.'}
