"""Katarina's durable questions guide subsequent public-feed reading.

Matching evidence is a research lead, never an answer or trading authorization.
"""
from hashlib import sha256
import re
import json


def prepare(db):
    db.execute('''CREATE TABLE IF NOT EXISTS public_research_agenda(
        id TEXT PRIMARY KEY, question TEXT NOT NULL, origin_review TEXT NOT NULL,
        created_utc TEXT NOT NULL)''')
    db.execute('''CREATE TABLE IF NOT EXISTS public_research_leads(
        question_id TEXT NOT NULL, document_id TEXT NOT NULL, known_utc TEXT NOT NULL,
        PRIMARY KEY(question_id,document_id))''')
    if db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='public_language_reviews'").fetchone():
        with db:
            for review_id, stamp, raw in db.execute(
                    'SELECT review_id,created_utc,candidate_json FROM public_language_reviews ORDER BY created_utc DESC LIMIT 48'):
                try:
                    questions = json.loads(raw)['questions']
                    if not isinstance(questions, list):
                        continue
                    for question in questions[:3]:
                        if not isinstance(question, str) or not 1 <= len(question) <= 300:
                            continue
                        ident = sha256(' '.join(question.lower().split()).encode()).hexdigest()
                        db.execute('INSERT OR IGNORE INTO public_research_agenda VALUES(?,?,?,?)',
                                   (ident, question, review_id, stamp))
                except (ValueError, KeyError, TypeError):
                    continue



def remember_questions(db, review_id, questions, stamp):
    prepare(db)
    with db:
        for question in questions:
            ident = sha256(' '.join(question.lower().split()).encode()).hexdigest()
            db.execute('INSERT OR IGNORE INTO public_research_agenda VALUES(?,?,?,?)',
                       (ident, question, review_id, stamp))


def pending(db):
    prepare(db)
    return list(db.execute('''SELECT a.id,a.question FROM public_research_agenda a
        WHERE NOT EXISTS(SELECT 1 FROM public_research_leads l WHERE l.question_id=a.id)
        ORDER BY a.created_utc,a.id LIMIT 48'''))


def matching(question, text):
    # Literal overlap only: neither a semantic answer nor resolution is claimed.
    stop = {'what','which','when','where','would','could','should','about','with','from',
            'this','that','have','does','will','bagaimana','apakah','mengapa','kapan',
            'yang','untuk','dengan','dalam','pada','dari','terhadap','akan','lebih',
            'dapat','sumber','artikel','pengaruh','dampak'}
    tokens = lambda value: set(re.findall(r'[^\W\d_]{4,}', value.lower())) - stop
    return len(tokens(question) & tokens(text)) >= 2


def prioritize(db, stories):
    questions = pending(db)
    return sorted(stories, key=lambda story: -sum(
        matching(question, story['title']) for _, question in questions))


def record_leads(db, document_id, body, stamp):
    questions = pending(db)
    with db:
        for ident, question in questions:
            if matching(question, body):
                db.execute('INSERT OR IGNORE INTO public_research_leads VALUES(?,?,?)',
                           (ident, document_id, stamp))


def status(db):
    prepare(db)
    return dict(questions_total=db.execute('SELECT COUNT(*) FROM public_research_agenda').fetchone()[0],
                questions_with_leads=db.execute('SELECT COUNT(DISTINCT question_id) FROM public_research_leads').fetchone()[0],
                selection='SELF_GENERATED_QUESTIONS_THEN_FEED_RECENCY',
                answers_verified=False, live_execution_authorized=False)
