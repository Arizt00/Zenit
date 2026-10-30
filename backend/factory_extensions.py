"""Bundled extensions: install once or upgrade an explicitly listed old digest."""
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
        previous=store.installed.get(eid)
        upgrade=bool(previous and previous.get('sha256') in entry.get('replaces',[]) and previous.get('sha256')!=entry['sha256'])
        if eid in seen and not upgrade:continue
        if previous and not upgrade:
            seen[eid]='existing';continue
        package=(catalog.parent/entry['file']).resolve()
        if package.parent!=catalog.parent.resolve() or package.is_symlink():raise ValueError('Invalid factory extension path.')
        if hashlib.sha256(package.read_bytes()).hexdigest()!=entry['sha256']:raise ValueError('Factory extension checksum mismatch.')
        review=store.inspect_local(str(package))
        if review['id']!=eid:raise ValueError('Factory extension identity mismatch.')
        installed=store.install(review['ticket'],True)
        if previous:
            if not previous.get('enabled'):store.update_state(eid,enabled=False);installed['enabled']=False
            installed['_factoryPrevious']={key:previous[key] for key in ('id','version','sha256')}
        seen[eid]=installed['version'];result.append(installed)
    atomic_json(marker,seen)
    return result
