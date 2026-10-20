import sqlite3
import unittest
from katarina.intelligence.research_agenda import remember_questions, prioritize, record_leads, status

class ResearchAgendaTests(unittest.TestCase):
    def test_own_questions_change_selection_and_persist_provenance(self):
        db=sqlite3.connect(':memory:')
        remember_questions(db,'review-1',['How do inflation rates affect gold bullion?'],'2026-10-20T00:00:00+00:00')
        remember_questions(db,'review-1',['How do inflation rates affect gold bullion?'],'2026-10-20T00:00:00+00:00')
        stories=[{'title':'General banking update'},{'title':'Gold bullion amid inflation rates'}]
        self.assertEqual(prioritize(db,stories)[0],stories[1])
        record_leads(db,'unrelated','General banking update','2026-10-20T01:00:00+00:00')
        self.assertEqual(status(db)['questions_with_leads'],0)
        record_leads(db,'doc-2','Gold bullion prices and inflation rates','2026-10-20T01:00:00+00:00')
        self.assertEqual(status(db)['questions_total'],1)
        self.assertEqual(status(db)['questions_with_leads'],1)
        self.assertEqual(db.execute('SELECT document_id FROM public_research_leads').fetchone()[0],'doc-2')
        self.assertFalse(status(db)['answers_verified'])
        self.assertFalse(status(db)['live_execution_authorized'])
        self.assertEqual(prioritize(db,stories),stories)
