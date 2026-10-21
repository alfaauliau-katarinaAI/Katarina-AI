from datetime import datetime,timezone
import numpy as np
import unittest
from katarina.intelligence.perception.calendar_history import load_calendar_history

DT=[('time','i8'),('open','f8'),('high','f8'),('low','f8'),('close','f8'),('spread','i8')]
def at(month,day=1):return datetime(2025,month,day,tzinfo=timezone.utc)
def rows(*times):return np.array([(int(t.timestamp()),100,102,99,101,10) for t in times],dtype=DT)


class CalendarHistoryTests(unittest.TestCase):
    def test_out_of_month_boundary_rows_cannot_duplicate_the_next_chunk(self):
        def fetch(symbol,tf,start,end):
            return rows(at(1),at(2))
        data,coverage=load_calendar_history(fetch,'A',5,300,at(1),at(3),now=at(3))
        self.assertEqual(len(data),2)
        self.assertEqual([m['returned_closed_bars'] for m in coverage['months']],[1,1])

    def test_monthly_requests_and_incomplete_final_bar_hidden(self):
        calls=[]
        def fetch(symbol,tf,start,end):
            calls.append((start,end))
            return rows(start,end.replace(microsecond=0))
        data,coverage=load_calendar_history(fetch,'A',5,300,at(1),at(3),now=at(3))
        self.assertEqual(len(calls),2)
        self.assertEqual(len(data),3)
        self.assertLess(data['time'][-1]+300,at(3).timestamp()+1)
        self.assertFalse(coverage['full_session_completeness_verified'])

    def test_empty_month_is_explicit_and_does_not_erase_other_month(self):
        data,coverage=load_calendar_history(lambda s,t,a,b:None if a.month==1 else rows(a),
            'A',5,300,at(1),at(3),now=at(3))
        self.assertEqual(coverage['missing_months'],['2025-01'])
        self.assertEqual(len(data),1)

    def test_invalid_or_duplicate_data_rejected(self):
        with self.assertRaises(ValueError):
            load_calendar_history(lambda *a:rows(at(1),at(1)),'A',5,300,at(1),at(2),now=at(2))
        with self.assertRaises(ValueError):
            load_calendar_history(lambda *a:None,'A',5,300,at(2),at(1),now=at(3))

    def test_invalid_prices_filtered(self):
        data=rows(at(1));data['close'][0]=float('nan')
        result,coverage=load_calendar_history(lambda *a:data,'A',5,300,at(1),at(2),now=at(2))
        self.assertIsNone(result)
        self.assertEqual(coverage['missing_months'],['2025-01'])
