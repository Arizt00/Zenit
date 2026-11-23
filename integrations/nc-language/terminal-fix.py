"""Build a traceable local nC VSIX; never alter an installed package in place."""
import argparse,hashlib,json,re,zipfile
from pathlib import Path

TERMINAL_FUNCTION=r'''
function createExecutionTerminal(name, resolved, argv, fileName) {
  const cwd = fileName ? path.dirname(fileName) : (vscode.workspace.workspaceFolders?.[0]?.uri?.fsPath || process.cwd());
  const options = { name, cwd };
  if (resolved.transport === 'wsl') {
    const command = ['cd', shellQuoteForBash(toWslPath(cwd)), '&&', shellQuoteForBash(resolved.nccPath || 'ncc'), ...argv.map(arg => shellQuoteForBash(wslArg(resolved, arg)))].join(' ');
    options.shellPath = 'wsl.exe';
    options.shellArgs = [...wslCommandPrefix(resolved.distro).slice(1), 'bash', '-lc', command];
  } else {
    options.shellPath = resolved.nccPath;
    options.shellArgs = argv.map(arg => String(arg));
  }
  return vscode.window.createTerminal(options);
}
'''

def patch(source):
    old='  const terminal = createBestTerminal(title);\n  terminal.show(true);\n  terminal.sendText(commandLine);'
    if source.count(old)!=1:raise ValueError('La versión de nC no coincide con la revisión del parche.')
    source=source.replace(old,'  const terminal = createExecutionTerminal(title, resolved, argv, fileName);\n  terminal.show(true);')
    old="  const terminal = createBestTerminal(title);\n  terminal.show(true);\n  terminal.sendText(createResolvedTerminalCommand(resolved, argv, vscode.window.activeTextEditor?.document?.fileName || null));"
    if source.count(old)!=1:raise ValueError('No se encontró la entrada de subcomandos revisada.')
    source=source.replace(old,"  const terminal = createExecutionTerminal(title, resolved, argv, vscode.window.activeTextEditor?.document?.fileName || null);\n  terminal.show(true);")
    # External PowerShell still needs an explicit call operator for a quoted path.
    old='  return `"${nccPath}" ${escaped.join(\' \')}`.trim();'
    if source.count(old)!=1:raise ValueError('No se encontró la construcción de la orden externa.')
    source=source.replace(old,"  if (process.platform === 'win32' && forcedRunHost() !== 'cmd') return `& ${shellQuoteForPowerShell(nccPath)} ${argv.map(shellQuoteForPowerShell).join(' ')}`;\n"+old)
    return source+TERMINAL_FUNCTION

def build(root,target,revision='2'):
    root=Path(root);manifest=json.loads((root/'package.json').read_text('utf-8'));original=manifest['version']
    if manifest['publisher']!='nc-lang' or manifest['name']!='nc-language' or original!='1.0.0-21v':raise ValueError('Solo se ha revisado nC Language 1.0.0-21v.')
    source=(root/'src/extension.js').read_text('utf-8');fixed=patch(source)
    # Windows command aliases cannot be passed to Node spawnSync as executables.
    # Use the selected compiler's own formatter, preserving the compiler/kit.
    for tail in ["'--compact', '--in-place'","'--compact'"]:
        old=f"  return execCapture(resolveNfmtPath(nccPath), [fileName, {tail}]);"
        if fixed.count(old)!=1:raise ValueError('No se encontró el formateador revisado.')
        new=f"  const formatter = resolveNfmtPath(nccPath);\n  if (/\\.(cmd|bat)$/i.test(formatter)) return execResolvedNccCapture(resolved, ['nfmt', fileName, {tail}], fileName);\n  return execCapture(formatter, [fileName, {tail}]);"
        fixed=fixed.replace(old,new)
    old="""        const exec = new vscode.ShellExecution(commandLine);"""
    if fixed.count(old)!=1:raise ValueError('No se encontró el proveedor de tareas revisado.')
    fixed=fixed.replace(old,"""        const fileName = vscode.window.activeTextEditor?.document?.fileName;
        if (!fileName) continue;
        const resolved = resolveNccForExecution(fileName);
        const argv = row.verb === 'nfmt' ? ['nfmt', fileName, '--compact', '--in-place']
          : row.verb === 'check' ? nccArgsForFileVerb('check', fileName)
          : row.profile ? debugArgsForFile(fileName) : runArgsForFile('run', fileName);
        const cwd = path.dirname(fileName);
        const command = resolved.transport === 'wsl'
          ? ['wsl.exe', ...wslCommandPrefix(resolved.distro).slice(1), 'bash', '-lc',
              ['cd', shellQuoteForBash(toWslPath(cwd)), '&&', shellQuoteForBash(resolved.nccPath || 'ncc'), ...argv.map(arg => shellQuoteForBash(wslArg(resolved, arg)))].join(' ')]
          : [resolved.nccPath, ...argv];
        const exec = new vscode.ProcessExecution(command[0], command.slice(1), {cwd});""")
    old="      const resolved = resolveNccForExecution(fileName);\n      const argv = runArgsForFile('run', fileName);"
    if fixed.count(old)!=1:raise ValueError('No se encontró la ejecución revisada.')
    fixed=fixed.replace(old,"      const editor = vscode.window.activeTextEditor;\n      if (editor?.document?.fileName === fileName && editor.document.isDirty && !await editor.document.save()) throw new Error('Save the active document before running it.');\n"+old)
    manifest['version']=original+'.zenit.'+revision;manifest['displayName']='nC Language · integración Zénit'
    manifest['zenitLocalCompatibilityBuild']={'baseVersion':original,'baseSourceSha256':hashlib.sha256(source.encode()).hexdigest(),'changes':['Compiler terminal uses executable and argv directly','Quoted external PowerShell invocation uses call operator','Formatter aliases use the selected ncc formatter','Tasks use the selected compiler and structured arguments','Run saves the active unsaved document before execution']}
    target=Path(target);target.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED) as archive:
        for file in sorted(root.rglob('*')):
            if not file.is_file():continue
            name=file.relative_to(root).as_posix();data=file.read_bytes()
            if any(part in ('.git','node_modules','dist','build') for part in file.relative_to(root).parts):continue
            if name=='src/extension.js':data=fixed.encode()
            if name=='package.json':data=json.dumps(manifest,ensure_ascii=False,indent=2).encode()
            archive.writestr('extension/'+name,data)
        archive.writestr('extension/ZENIT-LOCAL-FIX.md','Compilación local de compatibilidad. Base: nC Language '+original+'.\nLa terminal integrada ejecuta ncc directamente con argv. No modifica el compilador ni la semántica del lenguaje.\n')
    return {'path':str(target.resolve()),'sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'version':manifest['version']}

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('extension');parser.add_argument('output');args=parser.parse_args();print(json.dumps(build(args.extension,args.output)))
