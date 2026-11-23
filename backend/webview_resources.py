"""Scoped resources for opaque-origin extension frames, without editor cookies."""
import json
import re
from pathlib import Path
from urllib.parse import quote, unquote

RESOURCE_SOURCE = 'zenit-webview-source:'


def prepare_html(ident, token, html, roots):
    prefix = '/extension-webview-resource/' + token + '/'

    def resource(match):
        if match[1] != ident:
            raise PermissionError('Recurso de otro panel de extensión.')
        path = Path(unquote(match[2])).resolve()
        for index, root in enumerate(roots):
            if path.is_relative_to(root):
                return prefix + str(index) + '/' + quote(path.relative_to(root).as_posix(), safe='/')
        raise PermissionError('Recurso fuera de localResourceRoots.')

    html = re.sub(r'zenit-resource://([^/]+)/([^\s\"\'<>)]*)', resource, html)

    def meta(match):
        tag = match[0]
        if not re.search(r'http-equiv\s*=\s*[\"\']Content-Security-Policy[\"\']', tag, re.I):
            return tag
        return re.sub(r'(?<![\w.-])(?:vscode-resource:|vscode-webview-resource:|zenit-resource:)', RESOURCE_SOURCE, tag)

    html = re.sub(r'<meta\b[^>]*>', meta, html, flags=re.I)

    def data_script(match):
        attributes, content = match[1], match[2]
        if not re.search(r'\bdata-initial-state(?:\s|=|$)', attributes) or re.search(r'\b(?:src|type)\s*=', attributes, re.I):
            return match[0]
        try:
            json.loads(content)
        except ValueError:
            return match[0]
        return '<script type="application/json"' + attributes + '>' + content + '</script>'

    return re.sub(r'<script\b([^>]*)>([\s\S]*?)</script\s*>', data_script, html, flags=re.I)


def resource_path(roots, root_index, relative):
    from .extensions import safe_member
    if not root_index.isdecimal() or int(root_index) >= len(roots):
        raise FileNotFoundError('Raíz de recurso no disponible.')
    root = Path(roots[int(root_index)]).resolve()
    path = (root / str(safe_member(unquote(relative)))).resolve()
    if not path.is_relative_to(root):
        raise PermissionError('Recurso fuera de localResourceRoots.')
    return path
