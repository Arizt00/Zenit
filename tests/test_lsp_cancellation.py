"""Cancelled LSP responses are empty results; genuine failures remain errors."""
import threading
import unittest
from backend.lsp import LanguageSession,LanguageServers,LanguageRequestCancelled


class LanguageCancellationTests(unittest.TestCase):
    def session(self,error):
        session=LanguageSession.__new__(LanguageSession)
        session.lock=threading.RLock();session.sequence=0;session.pending={}
        session._write=lambda message:session.pending[message['id']].put({'error':error})
        session.validate_params=lambda params:params
        session.capabilities={}
        return session

    def test_cancelled_responses_release_requests_and_return_no_stale_result(self):
        for code in (-32800,-32801,-32802):
            with self.subTest(code=code):
                session=self.session({'code':code,'message':'Document changed'})
                with self.assertRaises(LanguageRequestCancelled):session.request('textDocument/documentHighlight',{})
                self.assertEqual(session.pending,{})
                servers=LanguageServers.__new__(LanguageServers);servers.get=lambda sid:session
                self.assertEqual(servers.request('test','textDocument/documentHighlight',{}),{'result':None,'cancelled':True})
                self.assertEqual(session.pending,{})

    def test_other_errors_are_not_suppressed_even_with_a_cancellation_message(self):
        session=self.session({'code':-32603,'message':'Request cancelled because the document was modified'})
        servers=LanguageServers.__new__(LanguageServers);servers.get=lambda sid:session
        with self.assertRaisesRegex(ValueError,'Request cancelled'):servers.request('test','textDocument/hover',{})
        self.assertEqual(session.pending,{})


if __name__=='__main__':unittest.main()
