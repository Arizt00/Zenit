"""First-paint appearance comes from the profile, independent of the HTTP port."""
from .extensions import localized_manifest


def appearance(preferences, extensions):
    base=preferences.get('appearance.theme')
    if base not in ('day','dark','forest'):
        base='day'
    selected=preferences.get('appearance.extensionTheme') or ''
    if selected and ':' in selected:
        owner,identity=selected.split(':',1)
        item=extensions.installed.get(owner)
        if item and item.get('enabled',True):
            try:
                package=extensions.root/item['directory']
                if package.is_symlink() or package.resolve().parent!=extensions.root.resolve():
                    return {'base':base,'extension':''}
                manifest=localized_manifest(package/'extension')
                for declaration in manifest.get('contributes',{}).get('themes',[]):
                    if str(declaration.get('id',declaration.get('label','theme')))==identity:
                        return {'base':'day' if declaration.get('uiTheme') in ('vs','hc-light') else 'dark','extension':selected}
            except (OSError,ValueError,KeyError,TypeError):
                pass
    return {'base':base,'extension':''}
