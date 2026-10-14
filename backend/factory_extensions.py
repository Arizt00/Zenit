"""Bundled extensions are installed once; user versions/removals are respected."""
import hashlib
import json
from .preferences import atomic_json


def install_factory(store, project):
    catalog=project/'web/assets/extensions/factory.json'
    if not catalog.is_file():return []
    marker=store.prefs.directory/'factory-extensions.json'
    try:seen=json.loads(marker.read_text('utf-8'))
    except (OSError,ValueError):seen={}
    if not isinstance(seen,dict):seen={}
    result=[]
    for entry in json.loads(catalog.read_text('utf-8')):
        eid=entry['id']
        if eid in seen:continue
        if eid in store.installed:
            seen[eid]='existing';continue
        package=(catalog.parent/entry['file']).resolve()
        if package.parent!=catalog.parent.resolve() or package.is_symlink():raise ValueError('Invalid factory extension path.')
        if hashlib.sha256(package.read_bytes()).hexdigest()!=entry['sha256']:raise ValueError('Factory extension checksum mismatch.')
        review=store.inspect_local(str(package))
        if review['id']!=eid:raise ValueError('Factory extension identity mismatch.')
        installed=store.install(review['ticket'],True);seen[eid]=installed['version'];result.append(installed)
    atomic_json(marker,seen)
    return result
