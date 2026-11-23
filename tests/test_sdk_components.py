import hashlib,json,shutil,sys,tempfile,unittest
from pathlib import Path
from backend.server import Application
from backend import foundation
from tools.package_sdk import package
ROOT=Path(__file__).resolve().parents[1]
class SDKComponentsTests(unittest.TestCase):
 def test_resource_only_component_verifies_and_resolves_across_install_order(self):
  previous=foundation._additional_roots
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);ws=root/'project';ws.mkdir();source=root/'source';(source/'images').mkdir(parents=True);image=source/'images/base.qcow2';image.write_bytes(b'QFI\xfb'+bytes(4096));digest=hashlib.sha256(image.read_bytes()).hexdigest();index={'schema':1,'platform':sys.platform,'tools':{},'components':[{'id':'arch','file':'images/base.qcow2','sha256':digest}]};(source/'tool-index.json').write_text(json.dumps(index));archive=root/'arch.zip';package(source,'arch',archive);app=Application(ROOT,ws,data_dir=root/'profile')
   try:
    app.features.sdk.install(str(archive));managed=app.features.sdk.config['roots'][0];self.assertEqual(app.features.machines.vm_base()['image'],str(Path(managed)/'images/base.qcow2'))
    other=root/'tools';other.mkdir();(other/'fixture.exe').write_bytes(b'fixture tool path only');(other/'tool-index.json').write_text(json.dumps({'schema':1,'platform':sys.platform,'components':[{'id':'qemu'}],'tools':{'qemu-system-x86_64':'fixture.exe','qemu-img':'fixture.exe'}}));app.features.sdk.activate(str(other));self.assertEqual(app.features.machines.vm_base()['image'],str(Path(managed)/'images/base.qcow2'));self.assertEqual(app.features.machines.vm_base()['qemu'],str(other/'fixture.exe'));self.assertTrue(app.features.machines.snapshot()['templates'][0]['available'])
    (Path(managed)/'images/base.qcow2').write_bytes(b'tampered')
    with self.assertRaisesRegex(ValueError,'imagen|componente'):app.features.sdk.activate(managed)
   finally:app.features.shutdown();app.runner.shutdown();foundation.set_sdk_roots(previous)
if __name__=='__main__':unittest.main()
