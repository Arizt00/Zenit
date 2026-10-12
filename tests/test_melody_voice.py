import base64,json,tempfile,time,unittest,wave,io
from pathlib import Path
from backend.melody_voice import MelodyVoice,spoken_text
from backend.preferences import Preferences
from backend.runtime_paths import find_tool

class VoiceTests(unittest.TestCase):
 def test_text_skips_code_and_keeps_actual_prose(self):
  self.assertEqual(spoken_text('**Razón**\nEste `valor` sirve.\n```python\nsecret=42\n```\n[Prueba](https://example.com)'), 'Razón\nEste valor sirve.\n\nPrueba')
  for value in ('```python\nprint(42)\n```','x'*2501,None):
   with self.assertRaises(ValueError):spoken_text(value)
 def test_unconfigured_voice_is_explicitly_unavailable(self):
  with tempfile.TemporaryDirectory() as tmp:
   voice=MelodyVoice(Preferences(tmp));self.assertFalse(voice.status()['available'])
   with self.assertRaises(ValueError):voice.start('Hola')
   self.assertFalse(voice.jobs);voice.shutdown()
 def test_audio_format_busy_cancellation_and_session_only_cleanup(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);script=root/'voice.cjs';script.write_text('process.stdout.write(JSON.stringify({type:"ready"})+"\\n");process.stdin.once("data",()=>setTimeout(()=>{process.stdout.write(JSON.stringify({type:"audio",sampleRate:24000,pcm:Buffer.alloc(48000).toString("base64")})+"\\n"+JSON.stringify({type:"done"})+"\\n");process.exit(0)},250));')
   voice=MelodyVoice(Preferences(tmp));voice.command=lambda:[find_tool('node'),str(script)]
   job=voice.start('Hola')
   with self.assertRaises(ValueError):voice.start('Segunda voz simultánea')
   end=time.monotonic()+5
   while not voice.snapshot(job['id'])['done'] and time.monotonic()<end:time.sleep(.02)
   with wave.open(io.BytesIO(voice.audio(job['id']))) as wav:self.assertEqual((wav.getframerate(),wav.getnchannels(),wav.getsampwidth(),wav.getnframes()),(24000,1,2,24000))
   voice.cancel(job['id'])
   with self.assertRaises(FileNotFoundError):voice.audio(job['id'])
   job=voice.start('Cancelar');voice.cancel(job['id']);end=time.monotonic()+5
   while not voice.snapshot(job['id'])['done'] and time.monotonic()<end:time.sleep(.02)
   self.assertTrue(voice.snapshot(job['id'])['cancelled']);voice.shutdown()
   with self.assertRaises(ValueError):voice.start('Sesión cerrada')
   self.assertFalse(list(root.glob('*.wav')))
