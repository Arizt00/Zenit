"""Apply the reviewed local-binding patch to the pinned nC integration source."""
def patch(source):
    anchor="const core = require('./nc_semantic');"
    if source.count(anchor)!=1:raise ValueError('La integración nC no coincide con el origen revisado.')
    source=source.replace(anchor,anchor+"\nconst ncNavigation = require('./zenit-scoped-navigation.cjs').create(core, vscode);")
    # Module names are canonical identifiers; an adjacent Calculadora.n also
    # represents project:calculadora, as in NCC's staged project resolver.
    old='path.basename(file, ext) === moduleName'
    if source.count(old)!=1:raise ValueError('Resolución de módulo nC inesperada.')
    source=source.replace(old,'path.basename(file, ext).toLowerCase() === moduleName.toLowerCase()')
    old="'.git', '.hg', '.svn', '.ncc', 'target', 'node_modules', 'dist', 'build',"
    if source.count(old)!=1:raise ValueError('Índice de proyecto nC inesperado.')
    source=source.replace(old,"'.git', '.hg', '.svn', '.ncc', '.lumen', '.venv', 'venv', 'target', 'node_modules', 'dist', 'build',")
    old='return base.replace(/[^A-Za-z0-9_]/g, \'_\');'
    if source.count(old)!=1:raise ValueError('Identificador de módulo nC inesperado.')
    source=source.replace(old,"return base.replace(/[^A-Za-z0-9_]/g, '_').toLowerCase();")
    anchor='''    try {
      const route = await routeDocument(context, document, signal);'''
    if source.count(anchor)!=1:raise ValueError('Diagnósticos de proyecto nC inesperados.')
    source=source.replace(anchor,'''    try {
      const nativeHighLevel = process.env.ZENIT_NC_PROJECT_DIAGNOSTICS === '1' && document.languageId === 'nc'
        && !/primitive\\[@\\]|\\[@machine\\]|\\[@\\]/.test(document.getText().slice(0,8192));
      const selectedKit = nativeHighLevel ? resolveNccForExecution(document.fileName) : null;
      if (nativeHighLevel && selectedKit.transport !== 'wsl') {
        const report = await vscode.commands.executeCommand('zenit.nc.projectDiagnostics', {path:document.fileName,text:document.getText(),compiler:selectedKit.nccPath});
        if (!isCurrent() || report.cancelled) return;
        const items = report.code === 0 ? [] : parseCompilerTextDiagnostics(document, report.output, 'NCC · proyecto');
        if (report.code !== 0 && !items.length) items.push(new vscode.Diagnostic(new vscode.Range(0,0,0,1), report.output || 'NCC no pudo comprobar el proyecto.', vscode.DiagnosticSeverity.Error));
        diagnostics.set(document.uri, items);
        return;
      }
      const route = await routeDocument(context, document, signal);''')
    start=source.index('function renameCurrentFileExtension(targetExt) {');end=source.index('\nfunction provideCodeActions(',start)
    source=source[:start]+'''function renameCurrentFileExtension(targetExt, fileName) {
  const editor = vscode.window.activeTextEditor;
  if (!targetExt || (!fileName && !editor)) return;
  const uri = fileName ? vscode.Uri.file(fileName) : editor.document.uri;
  const nextPath = uri.fsPath.replace(/\\.[^.]+$/, targetExt);
  const edit = new vscode.WorkspaceEdit();
  edit.renameFile(uri, vscode.Uri.file(nextPath), { overwrite: false, ignoreIfExists: true });
  return vscode.workspace.applyEdit(edit);
}
''' + source[end:]
    for old,new in [
        ('arguments: [targetExt]','arguments: [targetExt, document.fileName]'),
        ('(targetExt) => renameCurrentFileExtension(targetExt)','(targetExt, fileName) => renameCurrentFileExtension(targetExt, fileName)'),
    ]:
        if source.count(old)!=1:raise ValueError('Acción de migración nC inesperada.')
        source=source.replace(old,new)
    replacements=[
        ('provideDefinition(document, position, catalog)', 'provideReferences', '''  const imported = ncNavigation.importAt(document, position) ? importDefinitionAtPosition(document, position, catalog) : null;
  const local = imported || ncNavigation.definition(document, position);
  if (local) return local;
  return ncNavigation.memberDefinition(document, position, moduleName => {
    const target = resolveProjectModuleFile(document, moduleName);
    return target ? vscode.workspace.openTextDocument(vscode.Uri.file(target)) : null;
  });'''),
        ('provideReferences(document, position)', 'provideDocumentSymbols', '  return ncNavigation.references(document, position);'),
        ('provideDocumentSymbols(document)', 'provideSemanticTokens', '  return ncNavigation.symbols(document);'),
        ('provideRenameEdits(document, position, newName)', 'registerTaskProvider', '''  if (ncNavigation.importAt(document, position)) throw new Error('imports are not renamed; edit the import item explicitly');
  return ncNavigation.rename(document, position, newName);'''),
    ]
    for signature,next_function,body in replacements:
        marker='function '+signature+' {'
        if source.count(marker)!=1:raise ValueError('Proveedor nC inesperado: '+signature)
        start=source.index(marker);end=source.index('\nfunction '+next_function+'(',start)
        source=source[:start]+marker+'\n'+body+'\n}\n'+source[end:]
    return source
