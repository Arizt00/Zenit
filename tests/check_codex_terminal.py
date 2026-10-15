"""Local interactive-client smoke check. No login, prompt or model request."""
import json
from pathlib import Path
import sys
import tempfile
import time
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from backend.accounts import interactive_argv
from backend.terminals import TerminalSession

with tempfile.TemporaryDirectory(prefix='zenit-codex-check-',ignore_cleanup_errors=True) as tmp:
    root=Path(tmp);home=root/'profile';home.mkdir()
    args=interactive_argv('codex')
    terminal=TerminalSession({'id':'codex-check','name':'Codex check','argv':args},root,ROOT,environment={'CODEX_HOME':str(home)})
    try:
        deadline=time.monotonic()+15
        while time.monotonic()<deadline:
            text=terminal.read()['data']
            if 'Welcome' in text or 'Sign in' in text or terminal.closed:break
            # Reply only to the terminal's device-status query, not to UI prompts.
            if '\x1b[6n' in text:terminal.write('\x1b[1;1R')
            time.sleep(.1)
        assert '--no-daemon' in args
        assert 'no complete local package' not in text,text
        assert not terminal.closed,text
        assert 'Welcome' in text or 'Sign in' in text,text
        print(json.dumps({'directMode':True,'interactiveWelcome':True,'noLoginOrPromptSent':True}))
    finally:terminal.close();terminal.thread.join(timeout=5)
