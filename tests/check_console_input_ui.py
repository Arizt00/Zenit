"""Type into real running programs through xterm, using disposable projects."""
import json,sys,tempfile,threading,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from backend.server import Application,LumenServer
from playwright.sync_api import sync_playwright,expect

def main():
 out=ROOT/'qa-output/r6-console-input';out.mkdir(exist_ok=True);checks=[];errors=[]
 with tempfile.TemporaryDirectory(prefix='zenit-console-ui-',ignore_cleanup_errors=True) as temporary:
  base=Path(temporary);root=base/'Project with spaces';root.mkdir()
  sources={
   'input.py':'print("PY_READY>",flush=True)\na=input()\nprint("PY_NEXT>",flush=True)\nb=input()\nprint("PY_GOT="+a+"|"+b,flush=True)\n',
   'input.c':'#include <stdio.h>\nint main(void){char s[100];printf("C_READY>\\n");fflush(stdout);if(!fgets(s,sizeof s,stdin))return 1;printf("C_GOT=%s",s);return 0;}\n',
   'input.cpp':'#include <iostream>\n#include <string>\nint main(){std::cout << "CPP_READY>" << std::endl;std::string s;std::getline(std::cin,s);std::cout << "CPP_GOT=" << s << std::endl;}\n',
   'Input.java':'import java.util.Scanner; public class Input { public static void main(String[] args) { System.out.println("JAVA_READY>"); Scanner in=new Scanner(System.in); System.out.println("JAVA_GOT="+in.nextLine()); }}\n',
   'main.n':'use <project:helper>; use <io:input, output>; app :: runtime { fn: run() -> bool { println("NC_READY>"); value >> str <- readLine(); println(value); println(helper.worker.answer()); return true; } ref main ->> run; fa: return true; }',
   'Helper.n':'worker :: runtime { fn: public: answer() -> int { return 92841; } fa: return true; }'
  }
  for name,content in sources.items():(root/name).write_text(content,encoding='utf-8')
  app=Application(ROOT,root,data_dir=base/'profile');app.workspace.trusted=True;f=app.features
  f.studio.update({'onboarded':True});f.prefs.update({'general.showWelcome':False,'general.locale':'es','updates.automatic':False})
  server=LumenServer(0,app);threading.Thread(target=server.serve_forever,daemon=True).start()
  try:
   with sync_playwright() as pw:
    browser=pw.chromium.launch(channel='msedge',headless=True);page=browser.new_page(viewport={'width':1600,'height':1000});page.on('pageerror',lambda e:errors.append(str(e)))
    def inject(route):
     response=route.fetch();route.fulfill(response=response,body=response.text()+'\nwindow.__qa={get platform(){return platformUI},get desktop(){return desktopUI},get dock(){return dock},openFile};')
    page.route('**/src/app.js',inject);page.goto(f'http://127.0.0.1:{server.server_port}');page.wait_for_function('window.lumen?.platformReady')
    def wait_output(session,expected):
     end=time.monotonic()+40
     while expected not in session.output and not session.closed and time.monotonic()<end:time.sleep(.04)
     assert expected in session.output,session.output[-1600:]
    for name,ready,wanted in [('input.py','PY_READY>','PY_GOT=18|área'),('input.c','C_READY>','C_GOT=18'),('input.cpp','CPP_READY>','CPP_GOT=18'),('Input.java','JAVA_READY>','JAVA_GOT=18'),('main.n','NC_READY>','92841')]:
     page.evaluate('(name)=>__qa.openFile(name)',name)
     if name=='main.n':page.evaluate('__qa.dock.floatPanel("console",{x:370,y:460,width:850,height:300})')
     expect(page.locator('.run-button')).to_have_attribute('data-action','run',timeout=10000)
     page.locator('.run-button').click()
     try:page.wait_for_function('(name)=>__qa.platform.showingPTY&&__qa.desktop.forgeRun?.path===name&&!!__qa.desktop.forgeRun?.terminal',arg=name,timeout=40000)
     except Exception:
      page.screenshot(path=str(out/'failure.png'));print(page.locator('#toasts').inner_text(),flush=True)
      print(page.evaluate('({path:window.lumen.activeFile,run:__qa.desktop.forgeRun,pending:__qa.desktop.runPending,busy:__qa.desktop.forgeBusy,error:__qa.desktop.forgeError,action:document.querySelector(".run-button").dataset.action})'),flush=True)
      print({'jobs':[(j.done,j.code,j.output[-900:]) for j in app.runner.jobs.values()]},flush=True);raise
     identity=page.evaluate('__qa.platform.activeTerminal');session=f.terminals.get(identity);wait_output(session,ready)
     screen=page.locator(f'.pty-session[data-session-id="{identity}"] .xterm-screen');screen.click()
     page.keyboard.type('17');page.keyboard.press('Backspace');page.keyboard.type('8');page.keyboard.press('Enter')
     if name=='input.py':
      wait_output(session,'PY_NEXT>');page.keyboard.insert_text('área');page.keyboard.press('Enter')
     wait_output(session,wanted)
     end=time.monotonic()+10
     while not session.closed and time.monotonic()<end:time.sleep(.03)
     assert session.closed and session.code==0,(name,session.output[-1600:])
     checks.append({'language':name,'typed':True,'backspace':True,'received':True,'exitCode':0,'floating':name=='main.n'})
     page.screenshot(path=str(out/(name.replace('.','-')+'.png')))
     print('PASS visible keyboard input',name,flush=True)
    assert all((root/name).read_text('utf-8')==content for name,content in sources.items())
    assert not errors,errors;browser.close()
  finally:server.shutdown();server.server_close();f.shutdown();app.runner.shutdown()
 (out/'verification.json').write_text(json.dumps({'passed':True,'checks':checks,'errors':errors},ensure_ascii=False,indent=2),encoding='utf-8')
 print(json.dumps({'passed':len(checks),'errors':errors}),flush=True)

if __name__=='__main__':main()
