from datetime import date, datetime, timedelta
from unittest import TestCase

from vocal.util import dates


class UtilTestCase(TestCase):
    def test_add_one_month(self):
        d1 = date(2020, 2, 1)
        d2 = dates.add_months(d1, 1)
        assert d2.month == 3
        assert d2.day == 1

        d1 = date(2020, 12, 1)
        d2 = dates.add_months(d1, 1)
        assert d2.year == 2021
        assert d2.month == 1
        assert d2.day == 1

        d1 = date(2020, 1, 31)
        d2 = dates.add_months(d1, 1)
        assert d2.month == 2
        assert d2.day == 29

        d1 = date(2020, 4, 30)
        d2 = dates.add_months(d1, 1)
        assert d2.month == 5
        assert d2.day == 31

        d1 = date(2020, 5, 31)
        d2 = dates.add_months(d1, 1)
        assert d2.month == 6
        assert d2.day == 30

    def test_add_multiple_months(self):
        d1 = date(2020, 2, 1)
        d2 = dates.add_months(d1, 3)
        assert d2.month == 5
        assert d2.day == 1

        d1 = date(2020, 2, 14)
        d2 = dates.add_months(d1, 3)
        assert d2.month == 5
        assert d2.day == 14

        d1 = date(2020, 12, 14)
        d2 = dates.add_months(d1, 3)
        assert d2.month == 3
        assert d2.day == 14

        d1 = date(2020, 1, 31)
        d2 = dates.add_months(d1, 3)
        assert d2.month == 4
        assert d2.day == 30

        d1 = date(2020, 2, 29)
        d2 = dates.add_months(d1, 12)
        assert d2.year == 2021
        assert d2.month == 2
        assert d2.day == 28

        d1 = date(2019, 2, 28)
        d2 = dates.add_months(d1, 12)
        assert d2.year == 2020
        assert d2.month == 2
        assert d2.day == 29

    def test_tricky(self):
        d1 = date(2020, 8, 30)
        d2 = dates.add_months(d1, 3)
        assert d2.month == 11
        assert d2.day == 30

        d1 = date(2020, 11, 29)
        d2 = dates.add_months(d1, 3)
        assert d2.month == 2
        assert d2.day == 28

        d1 = date(2019, 1, 29)
        d2 = dates.add_months(d1, 13)
        assert d2.month == 2
        assert d2.day == 29

        d1 = date(2020, 2, 29)
        d2 = dates.add_months(d1, 13)
        assert d2.month == 3
        assert d2.day == 31

        d1 = date(2020, 2, 28)
        d2 = dates.add_months(d1, 13)
        assert d2.month == 3
        assert d2.day == 28

    def test_no_drift(self):
        d = date(2020, 1, 2)

        assert dates.add_months(d, 1).day == 2
        assert dates.add_months(d, 2).day == 2
        assert dates.add_months(d, 3).day == 2
        assert dates.add_months(d, 4).day == 2
        assert dates.add_months(d, 5).day == 2
        assert dates.add_months(d, 6).day == 2
        assert dates.add_months(d, 7).day == 2
        assert dates.add_months(d, 8).day == 2
        assert dates.add_months(d, 9).day == 2
        assert dates.add_months(d, 10).day == 2
        assert dates.add_months(d, 11).day == 2
        assert dates.add_months(d, 12).day == 2
        assert dates.add_months(d, 13).day == 2
        assert dates.add_months(d, 14).day == 2
        assert dates.add_months(d, 15).day == 2
        assert dates.add_months(d, 16).day == 2
        assert dates.add_months(d, 17).day == 2
        assert dates.add_months(d, 18).day == 2

        for i in range(18):
            assert d.day == 2
            d = dates.add_months(d, 1)

    def test_no_drift_2(self):
        d = date(2020, 1, 29)

        assert dates.add_months(d, 1).day == 29
        assert dates.add_months(d, 2).day == 29
        assert dates.add_months(d, 3).day == 29
        assert dates.add_months(d, 4).day == 29
        assert dates.add_months(d, 5).day == 29
        assert dates.add_months(d, 6).day == 29
        assert dates.add_months(d, 7).day == 29
        assert dates.add_months(d, 8).day == 29
        assert dates.add_months(d, 9).day == 29
        assert dates.add_months(d, 10).day == 29
        assert dates.add_months(d, 11).day == 29
        assert dates.add_months(d, 12).day == 29
        assert dates.add_months(d, 13).day == 28
        assert dates.add_months(d, 14).day == 29
        assert dates.add_months(d, 15).day == 29
        assert dates.add_months(d, 16).day == 29
        assert dates.add_months(d, 17).day == 29
        assert dates.add_months(d, 18).day == 29
