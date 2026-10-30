// The same lane selection as nC's official ideRouter.lowLevel. The compiler
// remains the authority; this bridge only preserves the kit selected by the user.
function ncDiagnosticRoute(document, resolved) {
  let mode = core.sanitizeLspMode(config().get('lspMode'));
  const low = /\.(nb|nm|nbb|ncp)$/i.test(document.fileName)
    || /primitive\[@\]|\[@machine\]|\[@\]/.test(document.getText().slice(0, 8192));
  if (mode === 'auto') mode = low ? 'nc-sys-lsp' : 'nide-broker';
  const file = resolved.transport === 'wsl' ? toWslPath(document.fileName, resolved.distro) : document.fileName;
  const profileArgs = ['--profile', core.sanitizeProfile(config().get('profile')), '--migration-stage', 'error-by-profile', '--json'];
  let command, backend, transport;
  if (mode === 'nide-broker') {
    backend = 'nide'; transport = 'broker-nide';
    command = [resolved.nccPath, 'nide', 'diagnostics', file];
  } else if (mode === 'nclsp') {
    backend = 'nclsp'; transport = 'lsp-direct';
    command = [resolved.nccPath, 'nclsp', 'validate', file, ...profileArgs];
  } else {
    backend = 'nc-sys-lsp'; transport = 'lsp-direct';
    const sibling = resolved.transport === 'wsl'
      ? path.posix.join(path.posix.dirname(resolved.nccPath), 'nc-sys-lsp')
      : path.join(path.dirname(resolved.nccPath), process.platform === 'win32' ? 'nc-sys-lsp.exe' : 'nc-sys-lsp');
    const analyzer = resolved.transport === 'wsl' ? sibling
      : fs.existsSync(sibling) ? sibling : commandOnPath('nc-sys-lsp');
    if (!analyzer) throw new Error('The selected native nC kit requires nc-sys-lsp for machine/basal/primitive diagnostics. Install that companion tool in the selected kit.');
    command = [analyzer, 'analyze', file, ...profileArgs];
  }
  if (resolved.transport === 'wsl') {
    const cwd = toWslPath(path.dirname(document.fileName), resolved.distro);
    const script = ['cd', shellQuoteForBash(cwd), '&&', ...command.map(shellQuoteForBash)].join(' ');
    command = ['wsl.exe', ...wslCommandPrefix(resolved.distro).slice(1), '--exec', 'bash', '-lc', script];
  }
  return {backend, transport, command, semantic_authority:'ncc', kit:resolved.source};
}

async function routeDocument(context, document, signal) {
  if (signal?.aborted) { const error = new Error('Aborted'); error.code = 'NC_DIAGNOSTIC_ABORTED'; throw error; }
  return ncDiagnosticRoute(document, resolveNccForExecution(document.fileName));
}
