"""Extract ancillary styles, removing the old shell and welcome presentation.

Run with tinycss2==1.4.0. The output has no imports or old main component rules.
Each replaced component is owned by a dedicated stylesheet in web/design/.
"""
import hashlib,json,re
from pathlib import Path
import tinycss2
ROOT=Path(__file__).resolve().parents[1]
SOURCES=('style.css','refinement.css','atelier.css','platform.css','lenon.css','controls.css',
         'continuity.css','preview.css','finish.css','desktop-workflows.css','workspace-profiles.css',
         'workbench-polish.css','zenit.css','laboratory.css')
OWNED=re.compile(r'(?<![\w-])(?:#lumen-home\b|\.(?:app|topbar|brand[\w-]*|lumen-logo|global-search|top-actions|search-placeholder|pane-switcher|tool-button|run-button|debug-button|avatar|activity-rail|rail-[\w-]*|inspiration-[\w-]*|workspace|dock-slot|dock-content|dock-scrim|project-panel|panel-heading|heading-actions|heading-mark|editor-panel|editor-tabbar|file-tabs|file-tab|file-label|tab-close|breadcrumbs|editor-mount|assistant[\w-]*|melody[\w-]*|ai-actions|ai-action-card|action-card-icon|ai-composer|composer-context|ai-current-document|ai-live-control|send-button|terminal-panel|terminal-toolbar|terminal-tabs|terminal-tab|terminal-tools|terminal-scroll|terminal-output|terminal-prompt|statusbar|status-item|home-[\w-]*|profile-photo|profile-initial|photo-badge|recent-[\w-]*|hero-copy|handwritten|glass-art|glass-aura|glass-fallback|icon-button|primary-button|secondary-button|text-button|file-type[\w-]*|tree-[\w-]*|sidebar-content|extension-(?:hero[\w-]*|card[\w-]*|catalog[\w-]*|logo|package-icon|icon-fallback|grid|toolbar|footer|results)|foundation[\w-]*|lab-[\w-]*|debug[\w-]*|lantern-workbench|lantern-toolbar|lantern-session|lantern-autosave|lantern-output|lantern-inline|forge[\w-]*|hacker-bar|hacker-mode|command-palette|palette[\w-]*|popover|menu[\w-]*|asm-[\w-]*|profile-tool-heading|modal[\w-]*|extension-(?:download[\w-]*|review[\w-]*|install[\w-]*|plan[\w-]*|checksum|compatibility|dependency[\w-]*)|review-metadata|review-disclaimer|settings[\w-]*|preference[\w-]*|platform-switch|platform-theme[\w-]*|preview-window|search-page|search-intro|studio-search[\w-]*|search-filters|search-empty|search-hit|search-code|search-result-heading|search-visual|platform-header|platform-title|platform-mark|platform-eyebrow|lantern-mini|lantern-monitor|lantern-open|lantern-monitor-actions|icon)(?![\w-]))')
GLOBAL={'*','html','body','html,body','button','input','textarea','select','kbd',':root','[hidden]','.hidden','::selection'}
def split_selectors(tokens):
    result=[];part=[]
    for token in tokens:
        if token.type=='literal' and token.value==',':result.append(tinycss2.serialize(part).strip());part=[]
        else:part.append(token)
    result.append(tinycss2.serialize(part).strip());return result
def migrate(rules):
    result=[]
    for rule in rules:
        if rule.type=='at-rule':
            if rule.content is None or rule.lower_at_keyword=='keyframes':
                result.append(tinycss2.serialize([rule]));continue
            children=migrate(tinycss2.parse_rule_list(rule.content,skip_comments=True,skip_whitespace=True))
            if children:result.append('@'+rule.at_keyword+' '+tinycss2.serialize(rule.prelude)+'{\n'+children+'\n}')
        elif rule.type=='qualified-rule':
            selectors=[s for s in split_selectors(rule.prelude) if s not in GLOBAL and not s.startswith(':root') and not OWNED.search(s)]
            if not selectors:continue
            declarations=tinycss2.parse_declaration_list(rule.content,skip_comments=True,skip_whitespace=True)
            valid=[d for d in declarations if d.type=='declaration']
            # Ancillary component declarations retain their established order.
            for d in valid:d.important=False
            result.append(','.join(selectors)+'{'+tinycss2.serialize(valid)+'}')
    return '\n'.join(result)
def main():
    target=ROOT/'web/design';target.mkdir(exist_ok=True);blocks=[];inputs=[]
    for name in SOURCES:
        raw=(ROOT/'web'/name).read_text(encoding='utf-8');inputs.append({'file':name,'sha256':hashlib.sha256(raw.encode()).hexdigest()})
        blocks.append('/* Ancillary contracts from '+name+' */\n'+migrate(tinycss2.parse_stylesheet(raw,skip_comments=True,skip_whitespace=True)))
    (target/'support.css').write_text('/* Generated ancillary components. Main shell/welcome rules were removed. */\n'+'\n'.join(blocks),encoding='utf-8')
    (target/'migration.json').write_text(json.dumps({'inputs':inputs,'replacedComponents':'shell, welcome, explorer, editor chrome, Melody, terminal chrome, Lantern, search, settings, extensions, Laboratory, Debug, Forge, ASM, modals','retained':'Ancillary controls and advanced feature presentation; progressively replaced per view.'},indent=2)+'\n',encoding='utf-8')
    print('Removed conflicting presentation from fourteen historical inputs.')
if __name__=='__main__':main()
