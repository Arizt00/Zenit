"""Keep compiler diagnostic routing on the selected native/WSL toolchain."""
from pathlib import Path

def patch(source):
    old="const res = cp.spawnSync('wsl.exe', ['wslpath', '-a', winPath], {"
    if source.count(old)!=1:raise ValueError('The reviewed wslpath call changed.')
    source=source.replace('function toWslPath(winPath) {', 'function toWslPath(winPath, distro = preferredWslDistro()) {')
    source=source.replace(old,"const res = cp.spawnSync('wsl.exe', [...wslCommandPrefix(distro).slice(1), '--exec', 'wslpath', '-a', winPath], {")
    start=source.index('async function routeDocument(context, document, signal) {')
    end=source.index('\nfunction routeDocumentViaWslNclsp(',start)
    source=source[:start]+Path(__file__).with_suffix('.js').read_text('utf-8')+'\n'+source[end:]
    return source
