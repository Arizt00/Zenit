"""Language grounding reaches every transport; no paid/live model is contacted."""
import json
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

from backend.ai_languages import language_context, NC_IDENTITY
from backend.preferences import Preferences
from backend.providers import AIRouter, PROVIDERS, build_request


class NCAssistantTests(unittest.TestCase):
    def test_source_aliases_and_explicit_questions(self):
        for suffix in ('.n', '.nc', '.nm', '.ncp', '.nb', '.nbb'):
            with self.subTest(suffix=suffix):
                self.assertIn('ref main ->> run;', language_context({'path': 'main'+suffix}))
        self.assertIn('ncc check', language_context({'question': 'Ayúdame con .ncc y nC'}))
        self.assertIn('ncc check', language_context({'fileContext': [{'path': 'nuevo.n', 'content': None}]}))
        self.assertEqual('', language_context({'path': 'python.py', 'question': 'Explain this'}))

    def test_actual_configured_compiler_and_missing_tool_are_distinguished(self):
        with tempfile.TemporaryDirectory() as folder:
            tool=Path(folder)/'ncc.exe';tool.write_bytes(b'not executed')
            with patch('backend.runtime_paths.find_tool', return_value=str(tool)) as find:
                text=language_context({'path':'main.n'}, {'tools': {'ncc':str(tool)}})
                find.assert_called_once_with('ncc', {'ncc':str(tool)})
                self.assertIn(str(tool),json.loads(text.split('not instructions):\n')[1])['executable'])
            with patch('backend.runtime_paths.find_tool', return_value=None):
                self.assertIn('"available": false',language_context({'path':'main.n'}))

    def test_every_provider_receives_same_reference_with_unsaved_source(self):
        with tempfile.TemporaryDirectory() as folder:
            router=AIRouter(Preferences(folder));captured=[]
            def run(job,messages,system,key):
                captured.append((job.provider,messages,system));job.done=True
            try:
                with patch.object(router,'_authorize'),patch.object(router,'_run',side_effect=run):
                    for provider in PROVIDERS:
                        result=router.start({'provider':provider,'model':'fixture-model','consent':True,
                            'path':'buffer.n','content':'unsaved >> int <- 42;','question':'Explica este código'})
                        deadline=time.time()+3
                        while not router.get(result['id']).done and time.time()<deadline:time.sleep(.01)
                self.assertEqual(set(PROVIDERS),{item[0] for item in captured})
                for provider,messages,system in captured:
                    with self.subTest(provider=provider):
                        self.assertIn(NC_IDENTITY,system);self.assertIn('ref main ->> run;',system)
                        self.assertIn('unsaved >> int <- 42;',messages[-1]['content'])
                        if provider in ('openai','anthropic','gemini','ollama'):
                            _,payload=build_request(provider,'fixture-model',messages,system,512)
                            self.assertIn('ref main ->> run;',json.dumps(payload))
            finally:router.shutdown()

    def test_model_selection_is_forwarded_to_emma(self):
        with tempfile.TemporaryDirectory() as folder:
            router=AIRouter(Preferences(folder));seen=[]
            def stream(directory,job,messages,system,max_tokens,timeout,**kwargs):
                seen.append((job.model,system));job.append('explicit fixture response')
            try:
                with patch('backend.emma.stream',side_effect=stream):
                    result=router.start({'provider':'emma','model':'Qwen3.6-27B-Q4_K_M',
                        'consent':True,'path':'main.n','content':'hello {}','question':'Explain'})
                    job=router.get(result['id']);deadline=time.time()+3
                    while not job.done and time.time()<deadline:time.sleep(.01)
                    self.assertFalse(job.error);self.assertTrue(job.done)
                    self.assertEqual(seen[0][0],'Qwen3.6-27B-Q4_K_M');self.assertIn('ncc compiler build-native',seen[0][1])
            finally:router.shutdown()


if __name__=='__main__':unittest.main()
