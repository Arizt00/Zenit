#!/usr/bin/env python3
"""Persistent LSP 3.x stdio bridge for the nclsp validate CLI.

A text-only diagnostic bridge: never claims completion/hover/rename support.
Does not write into the nC project; unsaved buffers are validated in a temp dir.
"""
import argparse
import concurrent.futures
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import urllib.parse

MAX_MESSAGE = 16 * 1024 * 1024
SEND_LOCK = threading.Lock()


def send(message):
    data = json.dumps(message, separators=(',', ':'), ensure_ascii=False).encode('utf-8')
    with SEND_LOCK:
        sys.stdout.buffer.write(f'Content-Length: {len(data)}\r\n\r\n'.encode('ascii'))
        sys.stdout.buffer.write(data)
        sys.stdout.buffer.flush()


def read_message(stream):
    length = None
    while True:
        header = stream.readline()
        if not header:
            return None
        if header in (b'\r\n', b'\n'):
            break
        name, sep, value = header.partition(b':')
        if sep and name.lower().strip() == b'content-length':
            length = int(value.strip())
    if length is None or length < 0 or length > MAX_MESSAGE:
        raise ValueError('Missing or invalid LSP Content-Length')
    data = stream.read(length)
    if len(data) != length:
        raise EOFError('Truncated LSP message')
    return json.loads(data.decode('utf-8'))


def diagnostic(message, severity=1, line=0, character=0):
    return {
        'range': {
            'start': {'line': max(0, line), 'character': max(0, character)},
            'end': {'line': max(0, line), 'character': max(0, character) + 1}
        },
        'severity': severity,
        'source': 'nclsp',
        'message': str(message)
    }


def parse_report(stdout, stderr, code):
    try:
        payload = json.loads(stdout)
    except (json.JSONDecodeError, TypeError):
        return [diagnostic((stderr or stdout or 'nclsp exited with code ' + str(code)).strip())]
    if not isinstance(payload, dict):
        return [diagnostic('Unexpected nclsp validate response')]
    diagnostics = []
    for key, severity in [('errors', 1), ('warnings', 2)]:
        for row in payload.get(key, []) or []:
            if isinstance(row, dict):
                message = row.get('message') or row.get('detail') or str(row)
                line = int(row.get('line') or 1) - 1
                column = int(row.get('column') or 1) - 1
                diagnostics.append(diagnostic(message, severity, line, column))
            else:
                diagnostics.append(diagnostic(row, severity))
    if code and not diagnostics:
        diagnostics.append(diagnostic(stderr.strip() or 'nclsp validate failed (' + str(code) + ')'))
    return diagnostics


def validate_document(nclsp, uri, text, timeout):
    # Do not trust document names to construct paths or execute commands.
    basename = Path(urllib.parse.unquote(urllib.parse.urlparse(uri).path)).name
    suffix = Path(basename).suffix.lower()
    if suffix not in {'.n', '.nc', '.nb', '.nbb', '.nm', '.ncp'}:
        suffix = '.n'
    with tempfile.TemporaryDirectory(prefix='nc-lsp-') as directory:
        filename = Path(directory) / ('buffer' + suffix)
        filename.write_text(text, encoding='utf-8')
        command = [nclsp, 'validate', str(filename), '--profile', 'standard',
                   '--migration-stage', 'error-by-profile', '--json']
        try:
            result = subprocess.run(command, capture_output=True, text=True,
                                    encoding='utf-8', errors='replace',
                                    timeout=timeout, check=False)
        except (OSError, subprocess.TimeoutExpired) as exc:
            return [diagnostic('Cannot validate with nclsp: ' + str(exc))]
    return parse_report(result.stdout, result.stderr, result.returncode)


class Session:
    def __init__(self, nclsp, timeout):
        self.nclsp = nclsp
        self.timeout = timeout
        self.documents = {}
        self.lock = threading.Lock()
        self.pool = concurrent.futures.ThreadPoolExecutor(max_workers=2,
                                                          thread_name_prefix='nclsp')
        self.timers = {}
        self.stopping = False

    def updated(self, uri, text, version):
        with self.lock:
            if self.stopping:
                return
            previous = self.timers.pop(uri, None)
            if previous is not None:
                previous.cancel()
            generation = self.documents.get(uri, {}).get('generation', 0) + 1
            self.documents[uri] = {'text': text, 'version': version,
                                   'generation': generation}
            # Avoid launching a validator process for each keystroke.
            timer = threading.Timer(0.35, self.submit_if_current,
                                    args=(uri, text, version, generation))
            timer.daemon = True
            self.timers[uri] = timer
            timer.start()

    def submit_if_current(self, uri, text, version, generation):
        with self.lock:
            current = self.documents.get(uri)
            if self.stopping or not current or current['generation'] != generation:
                return
            self.timers.pop(uri, None)
            try:
                self.pool.submit(self.publish_if_current, uri, text, version, generation)
            except RuntimeError:
                # Executor was already shut down during project close.
                return

    def publish_if_current(self, uri, text, version, generation):
        results = validate_document(self.nclsp, uri, text, self.timeout)
        with self.lock:
            current = self.documents.get(uri)
            if self.stopping or current is None or current['generation'] != generation:
                return
            params = {'uri': uri, 'diagnostics': results}
            if version is not None:
                params['version'] = version
            send({'jsonrpc': '2.0', 'method': 'textDocument/publishDiagnostics',
                  'params': params})

    def close(self, uri):
        with self.lock:
            timer = self.timers.pop(uri, None)
            if timer is not None:
                timer.cancel()
            self.documents.pop(uri, None)
        send({'jsonrpc': '2.0', 'method': 'textDocument/publishDiagnostics',
              'params': {'uri': uri, 'diagnostics': []}})

    def shutdown(self):
        with self.lock:
            self.stopping = True
            self.documents.clear()
            for timer in self.timers.values():
                timer.cancel()
            self.timers.clear()
        self.pool.shutdown(wait=False, cancel_futures=True)

    def handle(self, request):
        method = request.get('method')
        req_id = request.get('id')
        params = request.get('params') or {}
        if method == 'initialize':
            reply = {
                'capabilities': {'textDocumentSync': {'openClose': True, 'change': 1,
                                                     'save': {'includeText': True}}},
                'serverInfo': {'name': 'nC nclsp validate bridge', 'version': '2.1.0'}
            }
            send({'jsonrpc': '2.0', 'id': req_id, 'result': reply})
        elif method in ('initialized', 'workspace/didChangeConfiguration'):
            return
        elif method == 'textDocument/didOpen':
            doc = params['textDocument']
            self.updated(doc['uri'], doc['text'], doc.get('version'))
        elif method == 'textDocument/didChange':
            doc = params['textDocument']
            changes = params.get('contentChanges') or []
            if changes and 'text' in changes[-1]:
                self.updated(doc['uri'], changes[-1]['text'], doc.get('version'))
        elif method == 'textDocument/didSave':
            doc = params['textDocument']
            with self.lock:
                old = self.documents.get(doc['uri'])
            if old:
                self.updated(doc['uri'], params.get('text', old['text']), old['version'])
        elif method == 'textDocument/didClose':
            self.close(params['textDocument']['uri'])
        elif method == 'shutdown':
            self.shutdown()
            send({'jsonrpc': '2.0', 'id': req_id, 'result': None})
        elif method == 'exit':
            self.shutdown()
            return False
        elif req_id is not None:
            send({'jsonrpc': '2.0', 'id': req_id,
                  'error': {'code': -32601, 'message': 'Method not supported: ' + str(method)}})
        return True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--nclsp', default=os.getenv('NC_NCLSP_BIN', 'nclsp'))
    parser.add_argument('--timeout', type=float, default=12.0)
    arguments = parser.parse_args()
    session = Session(arguments.nclsp, arguments.timeout)
    try:
        while True:
            message = read_message(sys.stdin.buffer)
            if message is None or session.handle(message) is False:
                break
    except (ValueError, EOFError) as exc:
        sys.stderr.write('nclsp bridge: ' + str(exc) + '\n')
    finally:
        session.shutdown()


if __name__ == '__main__':
    main()
