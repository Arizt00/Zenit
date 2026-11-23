"""Adapt the user-selected JetBrains distribution without running IntelliJ in Zénit.

Icons are exact JAR bytes. Light/dark attributes are read from the distributed
class's javap output, not guessed from screenshots or the old VS Code palette.
Compiler services use the current nC integration source and selected ncc.
"""
import argparse,hashlib,importlib.util,io,json,re,struct,subprocess,tempfile,zipfile
from pathlib import Path

def sha(data):return hashlib.sha256(data).hexdigest()

def compiler_catalog(files,source):
    compiler=source.parents[2]/'target/release/ncc.exe'
    if not compiler.is_file():return
    def query(args):
        result=subprocess.run([str(compiler),*args,'--json'],capture_output=True,text=True,encoding='utf-8',check=True,timeout=10)
        return json.loads(result.stdout)
    catalog=json.loads(files['extension/data/nc_intellisense_catalog.json']);known={x['label'] for x in catalog['symbols']}
    families=query(['runtime','families'])['rows']
    for family in families:
        exports=query(['runtime','exports',family['family']])
        canonical=exports['import_path'].replace('nc.runtime.','nC.runtime.',1)
        for item in exports['exports']:
            name=item['name']
            if name in known:continue
            known.add(name)
            entry={'label':name,'kind':'function','signature':name+'('+', '.join(item['arg_types'])+') -> '+item['return'],
                   'insertText':name,'legacyImport':canonical,'detail':'NCC · '+canonical,
                   'documentation':'Firma publicada por el compilador NCC seleccionado.'}
            group={'input':'io','output':'io','render':'io','parse':'text','string':'text'}.get(exports['family_key'])
            if group:entry['facadeImport']='use <'+group+':'+exports['family_key']+'>;'
            catalog['symbols'].append(entry)
    catalog['nccProvenance']={'sha256':sha(compiler.read_bytes()),'families':len(families),'authority':'NCC runtime families/exports --json'}
    files['extension/data/nc_intellisense_catalog.json']=json.dumps(catalog,ensure_ascii=False,indent=2).encode()

def class_strings(data):
    count=struct.unpack_from('>H',data,8)[0];offset=10;index=1;values=[]
    while index<count:
        tag=data[offset];offset+=1
        if tag==1:
            size=struct.unpack_from('>H',data,offset)[0];offset+=2;values.append(data[offset:offset+size].decode('utf-8','replace'));offset+=size
        elif tag in (3,4,9,10,11,12,17,18):offset+=4
        elif tag in (5,6):offset+=8;index+=1
        elif tag in (7,8,16,19,20):offset+=2
        elif tag==15:offset+=3
        else:raise ValueError('Unexpected class constant '+str(tag))
        index+=1
    return values

def demo_block(demo,name):
    start=demo.index(name+' ::');opened=demo.index('{',start);depth=1;end=opened+1
    while depth and end<len(demo):
        if demo[end]=='{':depth+=1
        elif demo[end]=='}':depth-=1
        end+=1
    if depth:raise ValueError('Incomplete distributed demo block')
    return (demo[start:end]+'\n').encode()

def palette_from_bytecode(text):
    result={};text=text.split('static {};',1)[1]
    for match in re.finditer(r'// String (NC_[A-Z_0-9]+)\r?\n(.*?)(?=\n\s*\d+: putstatic)',text,re.S):
        key,block=match.groups();values=[]
        for line in block.splitlines():
            value=re.search(r'// int (-?\d+)',line) or re.search(r':\s+(?:bipush|sipush)\s+(-?\d+)',line) or re.search(r':\s+iconst_(\d)',line)
            if value:values.append(int(value[1]))
        if '// Method pair:' in block and len(values)==2:result[key]=dict(zip(('light','dark'),[f'#{n:06x}' for n in values]))
        elif '// Method rgb:' in block and len(values)==3:result[key]={'light':'#'+''.join(f'{n:02x}' for n in values),'dark':'#'+''.join(f'{n:02x}' for n in values)}
    assert result['NC_IMPORT_KEYWORD']=={'light':'#0284c7','dark':'#7dd3fc'}
    assert result['NC_PRINT_FUNCTION']=={'light':'#0284c7','dark':'#22d3ee'}
    assert len(result)>=60,len(result)
    return result

# Map the same nC concepts to their Monaco/TextMate names; their RGB values come
# from the actual JetBrains class. Context scopes keep other languages unchanged.
SCOPE_KEYS={
 'keyword':'NC_KEYWORD','storage':'NC_KEYWORD','keyword.control.import':'NC_IMPORT_KEYWORD',
 'entity.name.container':'NC_CONTAINER','entity.name.section.stc':'NC_STC_SECTION','entity.name.section.function':'NC_FN_SECTION','entity.name.section.fn':'NC_FN_SECTION','entity.name.section.fa':'NC_FA_SECTION',
 'keyword.control.main':'NC_MAIN_FAMILY','storage.modifier.visibility':'NC_VISIBILITY','variable.other.referential':'NC_AT_REFERENCE','variable.other.referential.group':'NC_AT_GROUP_REFERENCE',
 'keyword.operator.projection':'NC_PROJECTION','keyword.operator.verification':'NC_VERIFICATION','keyword.operator.assignment.material':'NC_MATERIAL_WRITE','keyword.control.return':'NC_RETURN',
 'support.function.dev':'NC_DEV','keyword.other.nc.role.runtime':'NC_MODE_RUNTIME','keyword.other.nc.role.system':'NC_MODE_KERNEL','keyword.other.nc.role.tooling':'NC_MODE_COMPILER',
 'support.type':'NC_TYPE','support.type.basic':'NC_BASIC_TYPE','support.type.advanced':'NC_ADVANCED_TYPE','support.type.generic':'NC_GENERIC_TYPE','support.type.array':'NC_ARRAY_TYPE','support.type.nc.pointer':'NC_POINTER_TYPE','support.type.memregion':'NC_MEM_REGION_TYPE',
 'constant.language.boolean':'NC_BOOL','support.type.nc.runtime':'NC_RUNTIME_FUNCTION','support.other.import':'NC_RUNTIME_FUNCTION','support.function.nc.print':'NC_PRINT_FUNCTION',
 'support.function.nc.pointer':'NC_POINTER_FUNCTION','support.function.nc.color':'NC_COLOR_FUNCTION','keyword.control.flow':'NC_CONTROL_FLOW','keyword.control.loop':'NC_LOOP_CONTROL',
 'keyword.other.nc.kernel.address':'NC_KERNEL_ADDRESS_KEYWORD','support.function.primitive':'NC_PRIMITIVE_ENTITY','support.function.hardware':'NC_HARDWARE_ENTITY','support.function.machine':'NC_MACHINE_INSTRUCTION','support.constant.machine.register':'NC_MACHINE_REGISTER',
 'constant.numeric':'NC_NUMBER','string':'NC_STRING','keyword.operator':'NC_OPERATOR','keyword.other.nc.rawhazard':'NC_RAW_HAZARD','support.function.ffi':'NC_FFI',
 'support.function.copy':'NC_COPY','support.function.clone':'NC_CLONE','entity.name.function':'NC_FUNCTION',
}
SEMANTIC_KEYS={
 'keyword':'NC_KEYWORD','importKeyword':'NC_IMPORT_KEYWORD','importDomain':'NC_RUNTIME_FUNCTION','importFamily':'NC_RUNTIME_FUNCTION','importItem':'NC_RUNTIME_FUNCTION',
 'container':'NC_CONTAINER','stcSection':'NC_STC_SECTION','fnSection':'NC_FN_SECTION','faSection':'NC_FA_SECTION','mainFamily':'NC_MAIN_FAMILY','visibilityKeyword':'NC_VISIBILITY',
 'atReference':'NC_AT_REFERENCE','atGroup':'NC_AT_GROUP_REFERENCE','projectionOperator':'NC_PROJECTION','verificationOperator':'NC_VERIFICATION','materialWrite':'NC_MATERIAL_WRITE','operator':'NC_OPERATOR',
 'devCall':'NC_DEV','returnKeyword':'NC_RETURN','modeRuntime':'NC_MODE_RUNTIME','modeCompiler':'NC_MODE_COMPILER','modeSystem':'NC_MODE_KERNEL','modeKernel':'NC_MODE_KERNEL','modeMachine':'NC_MODE_MACHINE','modePrimitive':'NC_MODE_PRIMITIVE','modeBasal':'NC_MODE_BASAL',
 'type':'NC_TYPE','basicType':'NC_BASIC_TYPE','advancedType':'NC_ADVANCED_TYPE','genericType':'NC_GENERIC_TYPE','arrayType':'NC_ARRAY_TYPE','pointerType':'NC_POINTER_TYPE','memRegionType':'NC_MEM_REGION_TYPE','boolLiteral':'NC_BOOL',
 'runtimeFamily':'NC_RUNTIME_FUNCTION','printFunction':'NC_PRINT_FUNCTION','pointerFunction':'NC_POINTER_FUNCTION','colorFunction':'NC_COLOR_FUNCTION','controlFlow':'NC_CONTROL_FLOW','loopControl':'NC_LOOP_CONTROL',
 'kernelAddressKeyword':'NC_KERNEL_ADDRESS_KEYWORD','primitiveEntity':'NC_PRIMITIVE_ENTITY','hardwareEntity':'NC_HARDWARE_ENTITY','machineInstruction':'NC_MACHINE_INSTRUCTION','machineRegister':'NC_MACHINE_REGISTER',
 'number':'NC_NUMBER','string':'NC_STRING','rawHazard':'NC_RAW_HAZARD','capability':'NC_CAPABILITY','policy':'NC_POLICY','ffiEntity':'NC_FFI','function':'NC_FUNCTION',
}

def build(distribution,source,target,javap):
    distribution,source,target=map(Path,(distribution,source,target));source=source.resolve()
    with zipfile.ZipFile(distribution) as archive:
        names=[n for n in archive.namelist() if re.search(r'/lib/nc-language-plugin-[^/]+\.jar$',n)];assert len(names)==1
        jar_bytes=archive.read(names[0])
    with zipfile.ZipFile(io.BytesIO(jar_bytes)) as jar,tempfile.TemporaryDirectory(prefix='nc-jb-') as temp:
        temp=Path(temp);jar_path=temp/'plugin.jar';jar_path.write_bytes(jar_bytes)
        descriptor=jar.read('META-INF/plugin.xml').decode('utf-8');assert '<id>dev.nc.language</id>' in descriptor and '<version>1.0.0.21v</version>' in descriptor
        bytecode=subprocess.check_output([str(javap),'-classpath',str(jar_path),'-c','-p','dev.nc.jetbrains.NcTextAttributes'],text=True,encoding='utf-8')
        palette=palette_from_bytecode(bytecode)
        provenance={'source':'JetBrains distribution selected by the user','filename':distribution.name,'sha256':sha(distribution.read_bytes()),'jarSha256':sha(jar_bytes),
                    'attributeClassSha256':sha(jar.read('dev/nc/jetbrains/NcTextAttributes.class')),'lexerClassSha256':sha(jar.read('dev/nc/jetbrains/NcSimpleLexer.class')),'highlighterClassSha256':sha(jar.read('dev/nc/jetbrains/NcSyntaxHighlighter.class')),
                    'serviceSource':str(source),'serviceSourceSha256':sha((source/'src/extension.js').read_bytes()),'iconSha256':{}}
        styles={'provenance':provenance}
        languages={'nc':('source.nc','SOURCE'),'nc-root':('source.nc.basal','BASAL'),'nc-machine':('source.nc.machine','MACHINE'),'nc-backend-object':('source.nc.backend-object','MACHINE'),'nc-primitive':('source.nc.primitive','PRIMITIVE'),'nc-hardware':('source.nc.hardware','HARDWARE')}
        for mode in ('light','dark'):
            entries=[];semantic={}
            for language,(context,family) in languages.items():
                for scope,key in SCOPE_KEYS.items():
                    if key in palette:entries.append({'scope':context+' '+scope,'settings':{'foreground':palette[key][mode],'fontStyle':''}})
                for role,key in [('entity.name.section','NC_'+family+'_SECTION'),('support.type.nc','NC_'+('TYPE' if family=='SOURCE' else family+'_TYPE')),('constant.numeric','NC_'+('NUMBER' if family=='SOURCE' else family+'_NUMBER'))]:
                    if key in palette:entries.append({'scope':context+' '+role,'settings':{'foreground':palette[key][mode],'fontStyle':''}})
                for token,key in SEMANTIC_KEYS.items():
                    if token=='number' and family!='SOURCE':key='NC_'+family+'_NUMBER'
                    if token=='type' and family!='SOURCE':key='NC_'+family+'_TYPE'
                    if key in palette:semantic[token+':'+language]=palette[key][mode]
                for width in (8,16,32,64,128,256,512):
                    key='NC_KERNEL_MMIO_'+str(width);entries.append({'scope':context+' support.function.nc.mmio.width'+str(width),'settings':{'foreground':palette[key][mode]}});semantic['kernelMmio'+str(width)+':'+language]=palette[key][mode]
            styles[mode]={'tokenColors':entries,'semanticTokenColors':semantic}
        spec=importlib.util.spec_from_file_location('nc_terminal_fix',Path(__file__).with_name('terminal-fix.py'));module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        intermediate=temp/'base.vsix';module.build(source,intermediate,'7')
        with zipfile.ZipFile(intermediate) as base:
            files={n:base.read(n) for n in base.namelist()}
        routing_spec=importlib.util.spec_from_file_location('nc_diagnostic_routing',Path(__file__).with_name('diagnostic-routing.py'));routing=importlib.util.module_from_spec(routing_spec);routing_spec.loader.exec_module(routing)
        files['extension/src/extension.js']=routing.patch(files['extension/src/extension.js'].decode()).encode()
        scoped_spec=importlib.util.spec_from_file_location('nc_scoped_navigation',Path(__file__).with_name('scoped-navigation.py'));scoped=importlib.util.module_from_spec(scoped_spec);scoped_spec.loader.exec_module(scoped)
        files['extension/src/extension.js']=scoped.patch(files['extension/src/extension.js'].decode()).encode()
        files['extension/src/zenit-scoped-navigation.cjs']=Path(__file__).with_name('scoped-navigation.cjs').read_bytes()
        compiler_catalog(files,source)
        manifest=json.loads(files['extension/package.json']);manifest['displayName']='nC Language · JetBrains en Zénit';manifest['icon']='./icons/nc-logo.svg';manifest.setdefault('lumen',{})['languageStyles']='./nc-jetbrains-visual.json';manifest['zenitJetBrainsVisual']=provenance
        manifest['zenitLocalCompatibilityBuild']['changes']+=['Diagnostics preserve the selected native/WSL compiler and official lane selection','WSL path conversion uses --exec and the selected distribution without losing Windows separators']
        manifest['zenitLocalCompatibilityBuild']['changes']+=['Local definitions, references and rename respect container/function/block scope and unsaved text; conflicting names are rejected','Outline ranges and children belong to their own container/function; project-wide semantic binding is not claimed']
        manifest['zenitLocalCompatibilityBuild']['changes']+=['Lane migration quick fixes capture the source file and return the WorkspaceEdit promise instead of using another provider request document']
        manifest['zenitLocalCompatibilityBuild']['changes']+=['Known qualified local members preserve binding during navigation/references/rename; imported module member definitions resolve their declared project file']
        manifest['zenitLocalCompatibilityBuild']['changes']+=['Compact and Allman declarations retain original UTF-16 coordinates; imports do not hide declarations on the same line']
        icons={};associations={}
        for suffix in ('n','nm','nb','nbb','ncp','nbo'):
            name='icons/nc-file-'+suffix+'.svg';data=jar.read(name);provenance['iconSha256'][suffix]=sha(data);files['extension/'+name]=data;icons[suffix]={'iconPath':'nc-file-'+suffix+'.svg'};associations[suffix]=suffix
        files['extension/icons/nc-jetbrains-icons.json']=json.dumps({'iconDefinitions':icons,'fileExtensions':associations}).encode()
        manifest['contributes']['iconThemes']=[{'id':'nc-icons','label':'nC · JetBrains','path':'./icons/nc-jetbrains-icons.json'}]
        files['extension/assets/nc-logo.svg']=jar.read('icons/nc-logo.svg')
        files['extension/icons/nc-logo.svg']=jar.read('icons/nc-logo.svg')
        files['extension/nc-jetbrains-visual.json']=json.dumps(styles,ensure_ascii=False,indent=2).encode()
        files['extension/package.json']=json.dumps(manifest,ensure_ascii=False,indent=2).encode()
        files['extension/JETBRAINS-PROVENANCE.json']=json.dumps(provenance,ensure_ascii=False,indent=2).encode()
        demo=next(s for s in class_strings(jar.read('dev/nc/jetbrains/NcColorSettingsPage.class')) if 'runtimeDemo {' in s and 'machineDemo :: machine' in s)
        files['extension/JETBRAINS-DISTRIBUTED-DEMO.n']=demo.encode()
        for fixture,container in [('machine_mode.nm','machineDemo'),('root_mode.nb','rootDemo'),('primitive_mode.nbb','primitiveDemo'),('primitive_mode.ncp','primitiveDemo')]:files['extension/test-fixtures/'+fixture]=demo_block(demo,container)
        files['extension/test-fixtures/high_level.n']=b'''use <io:output>;

vistaActual {
    stc:
        valor >> int <- 42;

    fn:
        run() -> bool {
            println(valor);
            return true;
        }

    ref main ->> run;

    fa:
        return true;
}
'''
        target.parent.mkdir(parents=True,exist_ok=True)
        with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED) as output:
            for name,data in files.items():output.writestr(name,data)
    return {'path':str(target.resolve()),'version':manifest['version'],'sha256':sha(target.read_bytes()),'jetbrains':provenance,'attributePairs':len(palette)}

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('distribution');parser.add_argument('service_source');parser.add_argument('output');parser.add_argument('--javap',required=True);args=parser.parse_args()
    print(json.dumps(build(args.distribution,args.service_source,args.output,args.javap),ensure_ascii=False))
