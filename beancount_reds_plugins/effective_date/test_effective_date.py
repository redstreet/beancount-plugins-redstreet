__copyright__ = "Copyright (C) 2020  Red S"
__license__ = "GNU GPLv3"

import unittest
import re

from beancount_reds_plugins.effective_date.effective_date import effective_date
from beancount.core import data
from beancount.parser import options
from beancount import loader
import datetime


def get_entries_with_narration(entries, regexp):
    """Return the entries whose narration matches the regexp.

    Args:
      entries: A list of directives.
      regexp: A regular expression string, to be matched against the
        narration field of transactions.
    Returns:
      A list of directives.
    """
    return [entry
            for entry in entries
            if (isinstance(entry, data.Transaction) and
                re.search(regexp, entry.narration))]


class TestEffectiveDate(unittest.TestCase):

    def test_empty_entries(self):
        entries, _ = effective_date([], options.OPTIONS_DEFAULTS.copy(), None)
        self.assertEqual([], entries)

    @loader.load_doc()
    def test_no_effective_dates(self, entries, _, options_map):
        """
        2014-01-01 open Liabilities:Mastercard
        2014-01-01 open Expenses:Taxes:Federal

        2014-02-01 * "Estimated taxes for 2013"
          Liabilities:Mastercard    -2000 USD
          Expenses:Taxes:Federal  2000 USD
         """
        new_entries, _ = effective_date(entries, options_map, None)
        self.assertEqual(new_entries, entries)

    @loader.load_doc()
    def test_expense_earlier(self, entries, _, options_map):
        """
        2014-01-01 open Liabilities:Mastercard
        2014-01-01 open Expenses:Taxes:Federal

        2014-02-01 * "Estimated taxes for 2013"
          Liabilities:Mastercard    -2000 USD
          Expenses:Taxes:Federal  2000 USD
            effective_date: 2013-12-31
        """

        # Above should turn into:
        # 2014-02-01 "Estimated taxes for 2013"
        #   Liabilities:Mastercard     -2000 USD
        #   Liabilities:Hold:Taxes:Federal 2000 USD

        # 2013-12-31 "Estimated taxes for 2013"
        #   Liabilities:Hold:Taxes:Federal    -2000 USD
        #   Expenses:Taxes:Federal    2000 USD

        new_entries, _ = effective_date(entries, options_map, None)
        self.assertEqual(5, len(new_entries))

        results = get_entries_with_narration(new_entries, "Estimated taxes")
        self.assertEqual(datetime.date(2013, 12, 31), results[0].date)
        self.assertEqual(datetime.date(2014, 2, 1), results[1].date)

        # self.assertEqual('Assets:Account1', results.postings[0].account)
        # self.assertEqual('Income:Account1', results.postings[1].account)

        # mansion = get_entries_with_narration(new_entries, "units of MANSION")[0]
        # self.assertEqual(2, len(mansion.postings))
        # self.assertEqual(D('-100'), mansion.postings[0].units.number)

        # entry = get_entries_with_narration(unreal_entries, '3 units')[0]
        # self.assertEqual("Equity:Account1:Gains", entry.postings[0].account)
        # self.assertEqual("Income:Account1:Gains", entry.postings[1].account)
        # self.assertEqual(D("24.00"), entry.postings[0].units.number)
        # self.assertEqual(D("-24.00"), entry.postings[1].units.number)

#    def test_expense_later(self, entries, _, options_map):
#        """
#        2014-01-01 open Liabilities:Mastercard
#        2014-01-01 open Expenses:Rent
#
#        2014-02-01 "Rent"
#          Liabilities:Mastercard    -2000 USD
#          Expenses:Rent              2000 USD
#            effective_date: 2014-05-01
#        """
#
#        # Above should turn into:
#        # 2014-02-01 "Rent"
#        #   Liabilities:Mastercard     -2000 USD
#        #   Liabilities:Hold:Rent 2000 USD
#
#        # 2014-05-01 "Rent"
#        #   Liabilities:Hold:Rent -2000 USD
#        #   Expenses:Rent     2000 USD

    @loader.load_doc()
    def test_expense_later_multiple(self, entries, _, options_map):
        """
        2014-01-01 open Liabilities:Mastercard
        2014-01-01 open Expenses:Car:Insurance

        2014-02-01 * "Car insurance: 3 months"
          Liabilities:Mastercard    -600 USD
          Expenses:Car:Insurance     200 USD
            effective_date: 2014-03-01
          Expenses:Car:Insurance     200 USD
            effective_date: 2014-04-01
          Expenses:Car:Insurance     200 USD
            effective_date: 2014-05-01
        """

        # Above should turn into:
        # 2014-02-01 "Car insurance: 3 months"
        #   Liabilities:Mastercard         -600 USD
        #   Liabilities:Hold:Car:Insurance  600 USD
        #
        # 2014-03-01 "Car insurance: 3 months"
        #   Assets:Hold:Car:Insurance -200 USD
        #   Expenses:Car:Insurance     200 USD
        #
        # 2014-04-01 "Car insurance: 3 months"
        #   Assets:Hold:Car:Insurance -200 USD
        #   Expenses:Car:Insurance     200 USD
        #
        # 2014-05-01 "Car insurance: 3 months"
        #   Assets:Hold:Car:Insurance -200 USD
        #   Expenses:Car:Insurance     200 USD

        new_entries, _ = effective_date(entries, options_map, None)
        self.assertEqual(7, len(new_entries))

    @loader.load_doc()
    def test_link_collision(self, entries, _, options_map):
        """
        2014-01-01 open Liabilities:Mastercard
        2014-01-01 open Expenses:Insurance:SportsCards

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A000
          Liabilities:Mastercard    -1.00 USD
          Expenses:Insurance:SportsCards     1.00 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A001
          Liabilities:Mastercard    -1.01 USD
          Expenses:Insurance:SportsCards     1.01 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A002
          Liabilities:Mastercard    -1.02 USD
          Expenses:Insurance:SportsCards     1.02 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A003
          Liabilities:Mastercard    -1.03 USD
          Expenses:Insurance:SportsCards     1.03 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A004
          Liabilities:Mastercard    -1.04 USD
          Expenses:Insurance:SportsCards     1.04 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A005
          Liabilities:Mastercard    -1.05 USD
          Expenses:Insurance:SportsCards     1.05 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A006
          Liabilities:Mastercard    -1.06 USD
          Expenses:Insurance:SportsCards     1.06 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A007
          Liabilities:Mastercard    -1.07 USD
          Expenses:Insurance:SportsCards     1.07 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A008
          Liabilities:Mastercard    -1.08 USD
          Expenses:Insurance:SportsCards     1.08 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A009
          Liabilities:Mastercard    -1.09 USD
          Expenses:Insurance:SportsCards     1.09 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A010
          Liabilities:Mastercard    -1.10 USD
          Expenses:Insurance:SportsCards     1.10 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A011
          Liabilities:Mastercard    -1.11 USD
          Expenses:Insurance:SportsCards     1.11 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A012
          Liabilities:Mastercard    -1.12 USD
          Expenses:Insurance:SportsCards     1.12 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A013
          Liabilities:Mastercard    -1.13 USD
          Expenses:Insurance:SportsCards     1.13 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A014
          Liabilities:Mastercard    -1.14 USD
          Expenses:Insurance:SportsCards     1.14 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A015
          Liabilities:Mastercard    -1.15 USD
          Expenses:Insurance:SportsCards     1.15 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A016
          Liabilities:Mastercard    -1.16 USD
          Expenses:Insurance:SportsCards     1.16 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A017
          Liabilities:Mastercard    -1.17 USD
          Expenses:Insurance:SportsCards     1.17 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A018
          Liabilities:Mastercard    -1.18 USD
          Expenses:Insurance:SportsCards     1.18 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A019
          Liabilities:Mastercard    -1.19 USD
          Expenses:Insurance:SportsCards     1.19 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A020
          Liabilities:Mastercard    -1.20 USD
          Expenses:Insurance:SportsCards     1.20 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A021
          Liabilities:Mastercard    -1.21 USD
          Expenses:Insurance:SportsCards     1.21 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A022
          Liabilities:Mastercard    -1.22 USD
          Expenses:Insurance:SportsCards     1.22 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A023
          Liabilities:Mastercard    -1.23 USD
          Expenses:Insurance:SportsCards     1.23 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A024
          Liabilities:Mastercard    -1.24 USD
          Expenses:Insurance:SportsCards     1.24 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A025
          Liabilities:Mastercard    -1.25 USD
          Expenses:Insurance:SportsCards     1.25 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A026
          Liabilities:Mastercard    -1.26 USD
          Expenses:Insurance:SportsCards     1.26 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A027
          Liabilities:Mastercard    -1.27 USD
          Expenses:Insurance:SportsCards     1.27 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A028
          Liabilities:Mastercard    -1.28 USD
          Expenses:Insurance:SportsCards     1.28 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A029
          Liabilities:Mastercard    -1.29 USD
          Expenses:Insurance:SportsCards     1.29 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A030
          Liabilities:Mastercard    -1.30 USD
          Expenses:Insurance:SportsCards     1.30 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A031
          Liabilities:Mastercard    -1.31 USD
          Expenses:Insurance:SportsCards     1.31 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A032
          Liabilities:Mastercard    -1.32 USD
          Expenses:Insurance:SportsCards     1.32 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A033
          Liabilities:Mastercard    -1.33 USD
          Expenses:Insurance:SportsCards     1.33 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A034
          Liabilities:Mastercard    -1.34 USD
          Expenses:Insurance:SportsCards     1.34 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A035
          Liabilities:Mastercard    -1.35 USD
          Expenses:Insurance:SportsCards     1.35 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A036
          Liabilities:Mastercard    -1.36 USD
          Expenses:Insurance:SportsCards     1.36 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A037
          Liabilities:Mastercard    -1.37 USD
          Expenses:Insurance:SportsCards     1.37 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A038
          Liabilities:Mastercard    -1.38 USD
          Expenses:Insurance:SportsCards     1.38 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A039
          Liabilities:Mastercard    -1.39 USD
          Expenses:Insurance:SportsCards     1.39 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A040
          Liabilities:Mastercard    -1.40 USD
          Expenses:Insurance:SportsCards     1.40 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A041
          Liabilities:Mastercard    -1.41 USD
          Expenses:Insurance:SportsCards     1.41 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A042
          Liabilities:Mastercard    -1.42 USD
          Expenses:Insurance:SportsCards     1.42 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A043
          Liabilities:Mastercard    -1.43 USD
          Expenses:Insurance:SportsCards     1.43 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A044
          Liabilities:Mastercard    -1.44 USD
          Expenses:Insurance:SportsCards     1.44 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A045
          Liabilities:Mastercard    -1.45 USD
          Expenses:Insurance:SportsCards     1.45 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A046
          Liabilities:Mastercard    -1.46 USD
          Expenses:Insurance:SportsCards     1.46 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A047
          Liabilities:Mastercard    -1.47 USD
          Expenses:Insurance:SportsCards     1.47 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A048
          Liabilities:Mastercard    -1.48 USD
          Expenses:Insurance:SportsCards     1.48 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A049
          Liabilities:Mastercard    -1.49 USD
          Expenses:Insurance:SportsCards     1.49 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A050
          Liabilities:Mastercard    -1.50 USD
          Expenses:Insurance:SportsCards     1.50 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A051
          Liabilities:Mastercard    -1.51 USD
          Expenses:Insurance:SportsCards     1.51 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A052
          Liabilities:Mastercard    -1.52 USD
          Expenses:Insurance:SportsCards     1.52 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A053
          Liabilities:Mastercard    -1.53 USD
          Expenses:Insurance:SportsCards     1.53 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A054
          Liabilities:Mastercard    -1.54 USD
          Expenses:Insurance:SportsCards     1.54 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A055
          Liabilities:Mastercard    -1.55 USD
          Expenses:Insurance:SportsCards     1.55 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A056
          Liabilities:Mastercard    -1.56 USD
          Expenses:Insurance:SportsCards     1.56 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A057
          Liabilities:Mastercard    -1.57 USD
          Expenses:Insurance:SportsCards     1.57 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A058
          Liabilities:Mastercard    -1.58 USD
          Expenses:Insurance:SportsCards     1.58 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A059
          Liabilities:Mastercard    -1.59 USD
          Expenses:Insurance:SportsCards     1.59 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A060
          Liabilities:Mastercard    -1.60 USD
          Expenses:Insurance:SportsCards     1.60 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A061
          Liabilities:Mastercard    -1.61 USD
          Expenses:Insurance:SportsCards     1.61 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A062
          Liabilities:Mastercard    -1.62 USD
          Expenses:Insurance:SportsCards     1.62 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A063
          Liabilities:Mastercard    -1.63 USD
          Expenses:Insurance:SportsCards     1.63 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A064
          Liabilities:Mastercard    -1.64 USD
          Expenses:Insurance:SportsCards     1.64 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A065
          Liabilities:Mastercard    -1.65 USD
          Expenses:Insurance:SportsCards     1.65 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A066
          Liabilities:Mastercard    -1.66 USD
          Expenses:Insurance:SportsCards     1.66 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A067
          Liabilities:Mastercard    -1.67 USD
          Expenses:Insurance:SportsCards     1.67 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A068
          Liabilities:Mastercard    -1.68 USD
          Expenses:Insurance:SportsCards     1.68 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A069
          Liabilities:Mastercard    -1.69 USD
          Expenses:Insurance:SportsCards     1.69 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A070
          Liabilities:Mastercard    -1.70 USD
          Expenses:Insurance:SportsCards     1.70 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A071
          Liabilities:Mastercard    -1.71 USD
          Expenses:Insurance:SportsCards     1.71 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A072
          Liabilities:Mastercard    -1.72 USD
          Expenses:Insurance:SportsCards     1.72 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A073
          Liabilities:Mastercard    -1.73 USD
          Expenses:Insurance:SportsCards     1.73 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A074
          Liabilities:Mastercard    -1.74 USD
          Expenses:Insurance:SportsCards     1.74 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A075
          Liabilities:Mastercard    -1.75 USD
          Expenses:Insurance:SportsCards     1.75 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A076
          Liabilities:Mastercard    -1.76 USD
          Expenses:Insurance:SportsCards     1.76 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A077
          Liabilities:Mastercard    -1.77 USD
          Expenses:Insurance:SportsCards     1.77 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A078
          Liabilities:Mastercard    -1.78 USD
          Expenses:Insurance:SportsCards     1.78 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A079
          Liabilities:Mastercard    -1.79 USD
          Expenses:Insurance:SportsCards     1.79 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A080
          Liabilities:Mastercard    -1.80 USD
          Expenses:Insurance:SportsCards     1.80 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A081
          Liabilities:Mastercard    -1.81 USD
          Expenses:Insurance:SportsCards     1.81 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A082
          Liabilities:Mastercard    -1.82 USD
          Expenses:Insurance:SportsCards     1.82 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A083
          Liabilities:Mastercard    -1.83 USD
          Expenses:Insurance:SportsCards     1.83 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A084
          Liabilities:Mastercard    -1.84 USD
          Expenses:Insurance:SportsCards     1.84 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A085
          Liabilities:Mastercard    -1.85 USD
          Expenses:Insurance:SportsCards     1.85 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A086
          Liabilities:Mastercard    -1.86 USD
          Expenses:Insurance:SportsCards     1.86 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A087
          Liabilities:Mastercard    -1.87 USD
          Expenses:Insurance:SportsCards     1.87 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A088
          Liabilities:Mastercard    -1.88 USD
          Expenses:Insurance:SportsCards     1.88 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A089
          Liabilities:Mastercard    -1.89 USD
          Expenses:Insurance:SportsCards     1.89 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A090
          Liabilities:Mastercard    -1.90 USD
          Expenses:Insurance:SportsCards     1.90 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A091
          Liabilities:Mastercard    -1.91 USD
          Expenses:Insurance:SportsCards     1.91 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A092
          Liabilities:Mastercard    -1.92 USD
          Expenses:Insurance:SportsCards     1.92 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A093
          Liabilities:Mastercard    -1.93 USD
          Expenses:Insurance:SportsCards     1.93 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A094
          Liabilities:Mastercard    -1.94 USD
          Expenses:Insurance:SportsCards     1.94 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A095
          Liabilities:Mastercard    -1.95 USD
          Expenses:Insurance:SportsCards     1.95 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A096
          Liabilities:Mastercard    -1.96 USD
          Expenses:Insurance:SportsCards     1.96 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A097
          Liabilities:Mastercard    -1.97 USD
          Expenses:Insurance:SportsCards     1.97 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A098
          Liabilities:Mastercard    -1.98 USD
          Expenses:Insurance:SportsCards     1.98 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A099
          Liabilities:Mastercard    -1.99 USD
          Expenses:Insurance:SportsCards     1.99 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A100
          Liabilities:Mastercard    -2.00 USD
          Expenses:Insurance:SportsCards     2.00 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A101
          Liabilities:Mastercard    -2.01 USD
          Expenses:Insurance:SportsCards     2.01 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A102
          Liabilities:Mastercard    -2.02 USD
          Expenses:Insurance:SportsCards     2.02 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A103
          Liabilities:Mastercard    -2.03 USD
          Expenses:Insurance:SportsCards     2.03 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A104
          Liabilities:Mastercard    -2.04 USD
          Expenses:Insurance:SportsCards     2.04 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A105
          Liabilities:Mastercard    -2.05 USD
          Expenses:Insurance:SportsCards     2.05 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A106
          Liabilities:Mastercard    -2.06 USD
          Expenses:Insurance:SportsCards     2.06 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A107
          Liabilities:Mastercard    -2.07 USD
          Expenses:Insurance:SportsCards     2.07 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A108
          Liabilities:Mastercard    -2.08 USD
          Expenses:Insurance:SportsCards     2.08 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A109
          Liabilities:Mastercard    -2.09 USD
          Expenses:Insurance:SportsCards     2.09 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A110
          Liabilities:Mastercard    -2.10 USD
          Expenses:Insurance:SportsCards     2.10 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A111
          Liabilities:Mastercard    -2.11 USD
          Expenses:Insurance:SportsCards     2.11 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A112
          Liabilities:Mastercard    -2.12 USD
          Expenses:Insurance:SportsCards     2.12 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A113
          Liabilities:Mastercard    -2.13 USD
          Expenses:Insurance:SportsCards     2.13 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A114
          Liabilities:Mastercard    -2.14 USD
          Expenses:Insurance:SportsCards     2.14 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A115
          Liabilities:Mastercard    -2.15 USD
          Expenses:Insurance:SportsCards     2.15 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A116
          Liabilities:Mastercard    -2.16 USD
          Expenses:Insurance:SportsCards     2.16 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A117
          Liabilities:Mastercard    -2.17 USD
          Expenses:Insurance:SportsCards     2.17 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A118
          Liabilities:Mastercard    -2.18 USD
          Expenses:Insurance:SportsCards     2.18 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A119
          Liabilities:Mastercard    -2.19 USD
          Expenses:Insurance:SportsCards     2.19 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A120
          Liabilities:Mastercard    -2.20 USD
          Expenses:Insurance:SportsCards     2.20 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A121
          Liabilities:Mastercard    -2.21 USD
          Expenses:Insurance:SportsCards     2.21 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A122
          Liabilities:Mastercard    -2.22 USD
          Expenses:Insurance:SportsCards     2.22 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A123
          Liabilities:Mastercard    -2.23 USD
          Expenses:Insurance:SportsCards     2.23 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A124
          Liabilities:Mastercard    -2.24 USD
          Expenses:Insurance:SportsCards     2.24 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A125
          Liabilities:Mastercard    -2.25 USD
          Expenses:Insurance:SportsCards     2.25 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A126
          Liabilities:Mastercard    -2.26 USD
          Expenses:Insurance:SportsCards     2.26 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A127
          Liabilities:Mastercard    -2.27 USD
          Expenses:Insurance:SportsCards     2.27 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A128
          Liabilities:Mastercard    -2.28 USD
          Expenses:Insurance:SportsCards     2.28 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A129
          Liabilities:Mastercard    -2.29 USD
          Expenses:Insurance:SportsCards     2.29 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A130
          Liabilities:Mastercard    -2.30 USD
          Expenses:Insurance:SportsCards     2.30 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A131
          Liabilities:Mastercard    -2.31 USD
          Expenses:Insurance:SportsCards     2.31 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A132
          Liabilities:Mastercard    -2.32 USD
          Expenses:Insurance:SportsCards     2.32 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A133
          Liabilities:Mastercard    -2.33 USD
          Expenses:Insurance:SportsCards     2.33 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A134
          Liabilities:Mastercard    -2.34 USD
          Expenses:Insurance:SportsCards     2.34 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A135
          Liabilities:Mastercard    -2.35 USD
          Expenses:Insurance:SportsCards     2.35 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A136
          Liabilities:Mastercard    -2.36 USD
          Expenses:Insurance:SportsCards     2.36 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A137
          Liabilities:Mastercard    -2.37 USD
          Expenses:Insurance:SportsCards     2.37 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A138
          Liabilities:Mastercard    -2.38 USD
          Expenses:Insurance:SportsCards     2.38 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A139
          Liabilities:Mastercard    -2.39 USD
          Expenses:Insurance:SportsCards     2.39 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A140
          Liabilities:Mastercard    -2.40 USD
          Expenses:Insurance:SportsCards     2.40 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A141
          Liabilities:Mastercard    -2.41 USD
          Expenses:Insurance:SportsCards     2.41 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A142
          Liabilities:Mastercard    -2.42 USD
          Expenses:Insurance:SportsCards     2.42 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A143
          Liabilities:Mastercard    -2.43 USD
          Expenses:Insurance:SportsCards     2.43 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A144
          Liabilities:Mastercard    -2.44 USD
          Expenses:Insurance:SportsCards     2.44 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A145
          Liabilities:Mastercard    -2.45 USD
          Expenses:Insurance:SportsCards     2.45 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A146
          Liabilities:Mastercard    -2.46 USD
          Expenses:Insurance:SportsCards     2.46 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A147
          Liabilities:Mastercard    -2.47 USD
          Expenses:Insurance:SportsCards     2.47 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A148
          Liabilities:Mastercard    -2.48 USD
          Expenses:Insurance:SportsCards     2.48 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A149
          Liabilities:Mastercard    -2.49 USD
          Expenses:Insurance:SportsCards     2.49 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A150
          Liabilities:Mastercard    -2.50 USD
          Expenses:Insurance:SportsCards     2.50 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A151
          Liabilities:Mastercard    -2.51 USD
          Expenses:Insurance:SportsCards     2.51 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A152
          Liabilities:Mastercard    -2.52 USD
          Expenses:Insurance:SportsCards     2.52 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A153
          Liabilities:Mastercard    -2.53 USD
          Expenses:Insurance:SportsCards     2.53 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A154
          Liabilities:Mastercard    -2.54 USD
          Expenses:Insurance:SportsCards     2.54 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A155
          Liabilities:Mastercard    -2.55 USD
          Expenses:Insurance:SportsCards     2.55 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A156
          Liabilities:Mastercard    -2.56 USD
          Expenses:Insurance:SportsCards     2.56 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A157
          Liabilities:Mastercard    -2.57 USD
          Expenses:Insurance:SportsCards     2.57 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A158
          Liabilities:Mastercard    -2.58 USD
          Expenses:Insurance:SportsCards     2.58 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A159
          Liabilities:Mastercard    -2.59 USD
          Expenses:Insurance:SportsCards     2.59 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A160
          Liabilities:Mastercard    -2.60 USD
          Expenses:Insurance:SportsCards     2.60 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A161
          Liabilities:Mastercard    -2.61 USD
          Expenses:Insurance:SportsCards     2.61 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A162
          Liabilities:Mastercard    -2.62 USD
          Expenses:Insurance:SportsCards     2.62 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A163
          Liabilities:Mastercard    -2.63 USD
          Expenses:Insurance:SportsCards     2.63 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A164
          Liabilities:Mastercard    -2.64 USD
          Expenses:Insurance:SportsCards     2.64 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A165
          Liabilities:Mastercard    -2.65 USD
          Expenses:Insurance:SportsCards     2.65 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A166
          Liabilities:Mastercard    -2.66 USD
          Expenses:Insurance:SportsCards     2.66 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A167
          Liabilities:Mastercard    -2.67 USD
          Expenses:Insurance:SportsCards     2.67 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A168
          Liabilities:Mastercard    -2.68 USD
          Expenses:Insurance:SportsCards     2.68 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A169
          Liabilities:Mastercard    -2.69 USD
          Expenses:Insurance:SportsCards     2.69 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A170
          Liabilities:Mastercard    -2.70 USD
          Expenses:Insurance:SportsCards     2.70 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A171
          Liabilities:Mastercard    -2.71 USD
          Expenses:Insurance:SportsCards     2.71 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A172
          Liabilities:Mastercard    -2.72 USD
          Expenses:Insurance:SportsCards     2.72 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A173
          Liabilities:Mastercard    -2.73 USD
          Expenses:Insurance:SportsCards     2.73 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A174
          Liabilities:Mastercard    -2.74 USD
          Expenses:Insurance:SportsCards     2.74 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A175
          Liabilities:Mastercard    -2.75 USD
          Expenses:Insurance:SportsCards     2.75 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A176
          Liabilities:Mastercard    -2.76 USD
          Expenses:Insurance:SportsCards     2.76 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A177
          Liabilities:Mastercard    -2.77 USD
          Expenses:Insurance:SportsCards     2.77 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A178
          Liabilities:Mastercard    -2.78 USD
          Expenses:Insurance:SportsCards     2.78 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A179
          Liabilities:Mastercard    -2.79 USD
          Expenses:Insurance:SportsCards     2.79 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A180
          Liabilities:Mastercard    -2.80 USD
          Expenses:Insurance:SportsCards     2.80 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A181
          Liabilities:Mastercard    -2.81 USD
          Expenses:Insurance:SportsCards     2.81 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A182
          Liabilities:Mastercard    -2.82 USD
          Expenses:Insurance:SportsCards     2.82 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A183
          Liabilities:Mastercard    -2.83 USD
          Expenses:Insurance:SportsCards     2.83 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A184
          Liabilities:Mastercard    -2.84 USD
          Expenses:Insurance:SportsCards     2.84 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A185
          Liabilities:Mastercard    -2.85 USD
          Expenses:Insurance:SportsCards     2.85 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A186
          Liabilities:Mastercard    -2.86 USD
          Expenses:Insurance:SportsCards     2.86 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A187
          Liabilities:Mastercard    -2.87 USD
          Expenses:Insurance:SportsCards     2.87 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A188
          Liabilities:Mastercard    -2.88 USD
          Expenses:Insurance:SportsCards     2.88 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A189
          Liabilities:Mastercard    -2.89 USD
          Expenses:Insurance:SportsCards     2.89 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A190
          Liabilities:Mastercard    -2.90 USD
          Expenses:Insurance:SportsCards     2.90 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A191
          Liabilities:Mastercard    -2.91 USD
          Expenses:Insurance:SportsCards     2.91 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A192
          Liabilities:Mastercard    -2.92 USD
          Expenses:Insurance:SportsCards     2.92 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A193
          Liabilities:Mastercard    -2.93 USD
          Expenses:Insurance:SportsCards     2.93 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A194
          Liabilities:Mastercard    -2.94 USD
          Expenses:Insurance:SportsCards     2.94 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A195
          Liabilities:Mastercard    -2.95 USD
          Expenses:Insurance:SportsCards     2.95 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A196
          Liabilities:Mastercard    -2.96 USD
          Expenses:Insurance:SportsCards     2.96 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A197
          Liabilities:Mastercard    -2.97 USD
          Expenses:Insurance:SportsCards     2.97 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A198
          Liabilities:Mastercard    -2.98 USD
          Expenses:Insurance:SportsCards     2.98 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A199
          Liabilities:Mastercard    -2.99 USD
          Expenses:Insurance:SportsCards     2.99 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A200
          Liabilities:Mastercard    -3.00 USD
          Expenses:Insurance:SportsCards     3.00 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A201
          Liabilities:Mastercard    -3.01 USD
          Expenses:Insurance:SportsCards     3.01 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A202
          Liabilities:Mastercard    -3.02 USD
          Expenses:Insurance:SportsCards     3.02 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A203
          Liabilities:Mastercard    -3.03 USD
          Expenses:Insurance:SportsCards     3.03 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A204
          Liabilities:Mastercard    -3.04 USD
          Expenses:Insurance:SportsCards     3.04 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A205
          Liabilities:Mastercard    -3.05 USD
          Expenses:Insurance:SportsCards     3.05 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A206
          Liabilities:Mastercard    -3.06 USD
          Expenses:Insurance:SportsCards     3.06 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A207
          Liabilities:Mastercard    -3.07 USD
          Expenses:Insurance:SportsCards     3.07 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A208
          Liabilities:Mastercard    -3.08 USD
          Expenses:Insurance:SportsCards     3.08 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A209
          Liabilities:Mastercard    -3.09 USD
          Expenses:Insurance:SportsCards     3.09 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A210
          Liabilities:Mastercard    -3.10 USD
          Expenses:Insurance:SportsCards     3.10 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A211
          Liabilities:Mastercard    -3.11 USD
          Expenses:Insurance:SportsCards     3.11 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A212
          Liabilities:Mastercard    -3.12 USD
          Expenses:Insurance:SportsCards     3.12 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A213
          Liabilities:Mastercard    -3.13 USD
          Expenses:Insurance:SportsCards     3.13 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A214
          Liabilities:Mastercard    -3.14 USD
          Expenses:Insurance:SportsCards     3.14 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A215
          Liabilities:Mastercard    -3.15 USD
          Expenses:Insurance:SportsCards     3.15 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A216
          Liabilities:Mastercard    -3.16 USD
          Expenses:Insurance:SportsCards     3.16 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A217
          Liabilities:Mastercard    -3.17 USD
          Expenses:Insurance:SportsCards     3.17 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A218
          Liabilities:Mastercard    -3.18 USD
          Expenses:Insurance:SportsCards     3.18 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A219
          Liabilities:Mastercard    -3.19 USD
          Expenses:Insurance:SportsCards     3.19 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A220
          Liabilities:Mastercard    -3.20 USD
          Expenses:Insurance:SportsCards     3.20 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A221
          Liabilities:Mastercard    -3.21 USD
          Expenses:Insurance:SportsCards     3.21 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A222
          Liabilities:Mastercard    -3.22 USD
          Expenses:Insurance:SportsCards     3.22 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A223
          Liabilities:Mastercard    -3.23 USD
          Expenses:Insurance:SportsCards     3.23 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A224
          Liabilities:Mastercard    -3.24 USD
          Expenses:Insurance:SportsCards     3.24 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A225
          Liabilities:Mastercard    -3.25 USD
          Expenses:Insurance:SportsCards     3.25 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A226
          Liabilities:Mastercard    -3.26 USD
          Expenses:Insurance:SportsCards     3.26 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A227
          Liabilities:Mastercard    -3.27 USD
          Expenses:Insurance:SportsCards     3.27 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A228
          Liabilities:Mastercard    -3.28 USD
          Expenses:Insurance:SportsCards     3.28 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A229
          Liabilities:Mastercard    -3.29 USD
          Expenses:Insurance:SportsCards     3.29 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A230
          Liabilities:Mastercard    -3.30 USD
          Expenses:Insurance:SportsCards     3.30 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A231
          Liabilities:Mastercard    -3.31 USD
          Expenses:Insurance:SportsCards     3.31 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A232
          Liabilities:Mastercard    -3.32 USD
          Expenses:Insurance:SportsCards     3.32 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A233
          Liabilities:Mastercard    -3.33 USD
          Expenses:Insurance:SportsCards     3.33 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A234
          Liabilities:Mastercard    -3.34 USD
          Expenses:Insurance:SportsCards     3.34 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A235
          Liabilities:Mastercard    -3.35 USD
          Expenses:Insurance:SportsCards     3.35 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A236
          Liabilities:Mastercard    -3.36 USD
          Expenses:Insurance:SportsCards     3.36 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A237
          Liabilities:Mastercard    -3.37 USD
          Expenses:Insurance:SportsCards     3.37 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A238
          Liabilities:Mastercard    -3.38 USD
          Expenses:Insurance:SportsCards     3.38 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A239
          Liabilities:Mastercard    -3.39 USD
          Expenses:Insurance:SportsCards     3.39 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A240
          Liabilities:Mastercard    -3.40 USD
          Expenses:Insurance:SportsCards     3.40 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A241
          Liabilities:Mastercard    -3.41 USD
          Expenses:Insurance:SportsCards     3.41 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A242
          Liabilities:Mastercard    -3.42 USD
          Expenses:Insurance:SportsCards     3.42 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A243
          Liabilities:Mastercard    -3.43 USD
          Expenses:Insurance:SportsCards     3.43 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A244
          Liabilities:Mastercard    -3.44 USD
          Expenses:Insurance:SportsCards     3.44 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A245
          Liabilities:Mastercard    -3.45 USD
          Expenses:Insurance:SportsCards     3.45 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A246
          Liabilities:Mastercard    -3.46 USD
          Expenses:Insurance:SportsCards     3.46 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A247
          Liabilities:Mastercard    -3.47 USD
          Expenses:Insurance:SportsCards     3.47 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A248
          Liabilities:Mastercard    -3.48 USD
          Expenses:Insurance:SportsCards     3.48 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A249
          Liabilities:Mastercard    -3.49 USD
          Expenses:Insurance:SportsCards     3.49 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A250
          Liabilities:Mastercard    -3.50 USD
          Expenses:Insurance:SportsCards     3.50 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A251
          Liabilities:Mastercard    -3.51 USD
          Expenses:Insurance:SportsCards     3.51 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A252
          Liabilities:Mastercard    -3.52 USD
          Expenses:Insurance:SportsCards     3.52 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A253
          Liabilities:Mastercard    -3.53 USD
          Expenses:Insurance:SportsCards     3.53 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A254
          Liabilities:Mastercard    -3.54 USD
          Expenses:Insurance:SportsCards     3.54 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A255
          Liabilities:Mastercard    -3.55 USD
          Expenses:Insurance:SportsCards     3.55 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A256
          Liabilities:Mastercard    -3.56 USD
          Expenses:Insurance:SportsCards     3.56 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A257
          Liabilities:Mastercard    -3.57 USD
          Expenses:Insurance:SportsCards     3.57 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A258
          Liabilities:Mastercard    -3.58 USD
          Expenses:Insurance:SportsCards     3.58 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A259
          Liabilities:Mastercard    -3.59 USD
          Expenses:Insurance:SportsCards     3.59 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A260
          Liabilities:Mastercard    -3.60 USD
          Expenses:Insurance:SportsCards     3.60 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A261
          Liabilities:Mastercard    -3.61 USD
          Expenses:Insurance:SportsCards     3.61 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A262
          Liabilities:Mastercard    -3.62 USD
          Expenses:Insurance:SportsCards     3.62 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A263
          Liabilities:Mastercard    -3.63 USD
          Expenses:Insurance:SportsCards     3.63 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A264
          Liabilities:Mastercard    -3.64 USD
          Expenses:Insurance:SportsCards     3.64 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A265
          Liabilities:Mastercard    -3.65 USD
          Expenses:Insurance:SportsCards     3.65 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A266
          Liabilities:Mastercard    -3.66 USD
          Expenses:Insurance:SportsCards     3.66 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A267
          Liabilities:Mastercard    -3.67 USD
          Expenses:Insurance:SportsCards     3.67 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A268
          Liabilities:Mastercard    -3.68 USD
          Expenses:Insurance:SportsCards     3.68 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A269
          Liabilities:Mastercard    -3.69 USD
          Expenses:Insurance:SportsCards     3.69 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A270
          Liabilities:Mastercard    -3.70 USD
          Expenses:Insurance:SportsCards     3.70 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A271
          Liabilities:Mastercard    -3.71 USD
          Expenses:Insurance:SportsCards     3.71 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A272
          Liabilities:Mastercard    -3.72 USD
          Expenses:Insurance:SportsCards     3.72 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A273
          Liabilities:Mastercard    -3.73 USD
          Expenses:Insurance:SportsCards     3.73 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A274
          Liabilities:Mastercard    -3.74 USD
          Expenses:Insurance:SportsCards     3.74 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A275
          Liabilities:Mastercard    -3.75 USD
          Expenses:Insurance:SportsCards     3.75 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A276
          Liabilities:Mastercard    -3.76 USD
          Expenses:Insurance:SportsCards     3.76 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A277
          Liabilities:Mastercard    -3.77 USD
          Expenses:Insurance:SportsCards     3.77 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A278
          Liabilities:Mastercard    -3.78 USD
          Expenses:Insurance:SportsCards     3.78 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A279
          Liabilities:Mastercard    -3.79 USD
          Expenses:Insurance:SportsCards     3.79 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A280
          Liabilities:Mastercard    -3.80 USD
          Expenses:Insurance:SportsCards     3.80 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A281
          Liabilities:Mastercard    -3.81 USD
          Expenses:Insurance:SportsCards     3.81 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A282
          Liabilities:Mastercard    -3.82 USD
          Expenses:Insurance:SportsCards     3.82 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A283
          Liabilities:Mastercard    -3.83 USD
          Expenses:Insurance:SportsCards     3.83 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A284
          Liabilities:Mastercard    -3.84 USD
          Expenses:Insurance:SportsCards     3.84 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A285
          Liabilities:Mastercard    -3.85 USD
          Expenses:Insurance:SportsCards     3.85 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A286
          Liabilities:Mastercard    -3.86 USD
          Expenses:Insurance:SportsCards     3.86 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A287
          Liabilities:Mastercard    -3.87 USD
          Expenses:Insurance:SportsCards     3.87 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A288
          Liabilities:Mastercard    -3.88 USD
          Expenses:Insurance:SportsCards     3.88 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A289
          Liabilities:Mastercard    -3.89 USD
          Expenses:Insurance:SportsCards     3.89 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A290
          Liabilities:Mastercard    -3.90 USD
          Expenses:Insurance:SportsCards     3.90 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A291
          Liabilities:Mastercard    -3.91 USD
          Expenses:Insurance:SportsCards     3.91 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A292
          Liabilities:Mastercard    -3.92 USD
          Expenses:Insurance:SportsCards     3.92 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A293
          Liabilities:Mastercard    -3.93 USD
          Expenses:Insurance:SportsCards     3.93 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A294
          Liabilities:Mastercard    -3.94 USD
          Expenses:Insurance:SportsCards     3.94 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A295
          Liabilities:Mastercard    -3.95 USD
          Expenses:Insurance:SportsCards     3.95 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A296
          Liabilities:Mastercard    -3.96 USD
          Expenses:Insurance:SportsCards     3.96 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A297
          Liabilities:Mastercard    -3.97 USD
          Expenses:Insurance:SportsCards     3.97 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A298
          Liabilities:Mastercard    -3.98 USD
          Expenses:Insurance:SportsCards     3.98 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A299
          Liabilities:Mastercard    -3.99 USD
          Expenses:Insurance:SportsCards     3.99 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A300
          Liabilities:Mastercard    -4.00 USD
          Expenses:Insurance:SportsCards     4.00 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A301
          Liabilities:Mastercard    -4.01 USD
          Expenses:Insurance:SportsCards     4.01 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A302
          Liabilities:Mastercard    -4.02 USD
          Expenses:Insurance:SportsCards     4.02 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A303
          Liabilities:Mastercard    -4.03 USD
          Expenses:Insurance:SportsCards     4.03 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A304
          Liabilities:Mastercard    -4.04 USD
          Expenses:Insurance:SportsCards     4.04 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A305
          Liabilities:Mastercard    -4.05 USD
          Expenses:Insurance:SportsCards     4.05 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A306
          Liabilities:Mastercard    -4.06 USD
          Expenses:Insurance:SportsCards     4.06 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A307
          Liabilities:Mastercard    -4.07 USD
          Expenses:Insurance:SportsCards     4.07 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A308
          Liabilities:Mastercard    -4.08 USD
          Expenses:Insurance:SportsCards     4.08 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A309
          Liabilities:Mastercard    -4.09 USD
          Expenses:Insurance:SportsCards     4.09 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A310
          Liabilities:Mastercard    -4.10 USD
          Expenses:Insurance:SportsCards     4.10 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A311
          Liabilities:Mastercard    -4.11 USD
          Expenses:Insurance:SportsCards     4.11 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A312
          Liabilities:Mastercard    -4.12 USD
          Expenses:Insurance:SportsCards     4.12 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A313
          Liabilities:Mastercard    -4.13 USD
          Expenses:Insurance:SportsCards     4.13 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A314
          Liabilities:Mastercard    -4.14 USD
          Expenses:Insurance:SportsCards     4.14 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A315
          Liabilities:Mastercard    -4.15 USD
          Expenses:Insurance:SportsCards     4.15 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A316
          Liabilities:Mastercard    -4.16 USD
          Expenses:Insurance:SportsCards     4.16 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A317
          Liabilities:Mastercard    -4.17 USD
          Expenses:Insurance:SportsCards     4.17 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A318
          Liabilities:Mastercard    -4.18 USD
          Expenses:Insurance:SportsCards     4.18 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A319
          Liabilities:Mastercard    -4.19 USD
          Expenses:Insurance:SportsCards     4.19 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A320
          Liabilities:Mastercard    -4.20 USD
          Expenses:Insurance:SportsCards     4.20 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A321
          Liabilities:Mastercard    -4.21 USD
          Expenses:Insurance:SportsCards     4.21 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A322
          Liabilities:Mastercard    -4.22 USD
          Expenses:Insurance:SportsCards     4.22 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A323
          Liabilities:Mastercard    -4.23 USD
          Expenses:Insurance:SportsCards     4.23 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A324
          Liabilities:Mastercard    -4.24 USD
          Expenses:Insurance:SportsCards     4.24 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A325
          Liabilities:Mastercard    -4.25 USD
          Expenses:Insurance:SportsCards     4.25 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A326
          Liabilities:Mastercard    -4.26 USD
          Expenses:Insurance:SportsCards     4.26 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A327
          Liabilities:Mastercard    -4.27 USD
          Expenses:Insurance:SportsCards     4.27 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A328
          Liabilities:Mastercard    -4.28 USD
          Expenses:Insurance:SportsCards     4.28 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A329
          Liabilities:Mastercard    -4.29 USD
          Expenses:Insurance:SportsCards     4.29 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A330
          Liabilities:Mastercard    -4.30 USD
          Expenses:Insurance:SportsCards     4.30 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A331
          Liabilities:Mastercard    -4.31 USD
          Expenses:Insurance:SportsCards     4.31 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A332
          Liabilities:Mastercard    -4.32 USD
          Expenses:Insurance:SportsCards     4.32 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A333
          Liabilities:Mastercard    -4.33 USD
          Expenses:Insurance:SportsCards     4.33 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A334
          Liabilities:Mastercard    -4.34 USD
          Expenses:Insurance:SportsCards     4.34 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A335
          Liabilities:Mastercard    -4.35 USD
          Expenses:Insurance:SportsCards     4.35 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A336
          Liabilities:Mastercard    -4.36 USD
          Expenses:Insurance:SportsCards     4.36 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A337
          Liabilities:Mastercard    -4.37 USD
          Expenses:Insurance:SportsCards     4.37 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A338
          Liabilities:Mastercard    -4.38 USD
          Expenses:Insurance:SportsCards     4.38 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A339
          Liabilities:Mastercard    -4.39 USD
          Expenses:Insurance:SportsCards     4.39 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A340
          Liabilities:Mastercard    -4.40 USD
          Expenses:Insurance:SportsCards     4.40 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A341
          Liabilities:Mastercard    -4.41 USD
          Expenses:Insurance:SportsCards     4.41 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A342
          Liabilities:Mastercard    -4.42 USD
          Expenses:Insurance:SportsCards     4.42 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A343
          Liabilities:Mastercard    -4.43 USD
          Expenses:Insurance:SportsCards     4.43 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A344
          Liabilities:Mastercard    -4.44 USD
          Expenses:Insurance:SportsCards     4.44 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A345
          Liabilities:Mastercard    -4.45 USD
          Expenses:Insurance:SportsCards     4.45 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A346
          Liabilities:Mastercard    -4.46 USD
          Expenses:Insurance:SportsCards     4.46 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A347
          Liabilities:Mastercard    -4.47 USD
          Expenses:Insurance:SportsCards     4.47 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A348
          Liabilities:Mastercard    -4.48 USD
          Expenses:Insurance:SportsCards     4.48 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A349
          Liabilities:Mastercard    -4.49 USD
          Expenses:Insurance:SportsCards     4.49 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A350
          Liabilities:Mastercard    -4.50 USD
          Expenses:Insurance:SportsCards     4.50 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A351
          Liabilities:Mastercard    -4.51 USD
          Expenses:Insurance:SportsCards     4.51 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A352
          Liabilities:Mastercard    -4.52 USD
          Expenses:Insurance:SportsCards     4.52 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A353
          Liabilities:Mastercard    -4.53 USD
          Expenses:Insurance:SportsCards     4.53 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A354
          Liabilities:Mastercard    -4.54 USD
          Expenses:Insurance:SportsCards     4.54 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A355
          Liabilities:Mastercard    -4.55 USD
          Expenses:Insurance:SportsCards     4.55 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A356
          Liabilities:Mastercard    -4.56 USD
          Expenses:Insurance:SportsCards     4.56 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A357
          Liabilities:Mastercard    -4.57 USD
          Expenses:Insurance:SportsCards     4.57 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A358
          Liabilities:Mastercard    -4.58 USD
          Expenses:Insurance:SportsCards     4.58 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A359
          Liabilities:Mastercard    -4.59 USD
          Expenses:Insurance:SportsCards     4.59 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A360
          Liabilities:Mastercard    -4.60 USD
          Expenses:Insurance:SportsCards     4.60 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A361
          Liabilities:Mastercard    -4.61 USD
          Expenses:Insurance:SportsCards     4.61 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A362
          Liabilities:Mastercard    -4.62 USD
          Expenses:Insurance:SportsCards     4.62 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A363
          Liabilities:Mastercard    -4.63 USD
          Expenses:Insurance:SportsCards     4.63 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A364
          Liabilities:Mastercard    -4.64 USD
          Expenses:Insurance:SportsCards     4.64 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A365
          Liabilities:Mastercard    -4.65 USD
          Expenses:Insurance:SportsCards     4.65 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A366
          Liabilities:Mastercard    -4.66 USD
          Expenses:Insurance:SportsCards     4.66 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A367
          Liabilities:Mastercard    -4.67 USD
          Expenses:Insurance:SportsCards     4.67 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A368
          Liabilities:Mastercard    -4.68 USD
          Expenses:Insurance:SportsCards     4.68 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A369
          Liabilities:Mastercard    -4.69 USD
          Expenses:Insurance:SportsCards     4.69 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A370
          Liabilities:Mastercard    -4.70 USD
          Expenses:Insurance:SportsCards     4.70 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A371
          Liabilities:Mastercard    -4.71 USD
          Expenses:Insurance:SportsCards     4.71 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A372
          Liabilities:Mastercard    -4.72 USD
          Expenses:Insurance:SportsCards     4.72 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A373
          Liabilities:Mastercard    -4.73 USD
          Expenses:Insurance:SportsCards     4.73 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A374
          Liabilities:Mastercard    -4.74 USD
          Expenses:Insurance:SportsCards     4.74 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A375
          Liabilities:Mastercard    -4.75 USD
          Expenses:Insurance:SportsCards     4.75 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A376
          Liabilities:Mastercard    -4.76 USD
          Expenses:Insurance:SportsCards     4.76 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A377
          Liabilities:Mastercard    -4.77 USD
          Expenses:Insurance:SportsCards     4.77 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A378
          Liabilities:Mastercard    -4.78 USD
          Expenses:Insurance:SportsCards     4.78 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A379
          Liabilities:Mastercard    -4.79 USD
          Expenses:Insurance:SportsCards     4.79 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A380
          Liabilities:Mastercard    -4.80 USD
          Expenses:Insurance:SportsCards     4.80 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A381
          Liabilities:Mastercard    -4.81 USD
          Expenses:Insurance:SportsCards     4.81 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A382
          Liabilities:Mastercard    -4.82 USD
          Expenses:Insurance:SportsCards     4.82 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A383
          Liabilities:Mastercard    -4.83 USD
          Expenses:Insurance:SportsCards     4.83 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A384
          Liabilities:Mastercard    -4.84 USD
          Expenses:Insurance:SportsCards     4.84 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A385
          Liabilities:Mastercard    -4.85 USD
          Expenses:Insurance:SportsCards     4.85 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A386
          Liabilities:Mastercard    -4.86 USD
          Expenses:Insurance:SportsCards     4.86 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A387
          Liabilities:Mastercard    -4.87 USD
          Expenses:Insurance:SportsCards     4.87 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A388
          Liabilities:Mastercard    -4.88 USD
          Expenses:Insurance:SportsCards     4.88 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A389
          Liabilities:Mastercard    -4.89 USD
          Expenses:Insurance:SportsCards     4.89 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A390
          Liabilities:Mastercard    -4.90 USD
          Expenses:Insurance:SportsCards     4.90 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A391
          Liabilities:Mastercard    -4.91 USD
          Expenses:Insurance:SportsCards     4.91 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A392
          Liabilities:Mastercard    -4.92 USD
          Expenses:Insurance:SportsCards     4.92 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A393
          Liabilities:Mastercard    -4.93 USD
          Expenses:Insurance:SportsCards     4.93 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A394
          Liabilities:Mastercard    -4.94 USD
          Expenses:Insurance:SportsCards     4.94 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A395
          Liabilities:Mastercard    -4.95 USD
          Expenses:Insurance:SportsCards     4.95 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A396
          Liabilities:Mastercard    -4.96 USD
          Expenses:Insurance:SportsCards     4.96 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A397
          Liabilities:Mastercard    -4.97 USD
          Expenses:Insurance:SportsCards     4.97 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A398
          Liabilities:Mastercard    -4.98 USD
          Expenses:Insurance:SportsCards     4.98 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A399
          Liabilities:Mastercard    -4.99 USD
          Expenses:Insurance:SportsCards     4.99 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A400
          Liabilities:Mastercard    -5.00 USD
          Expenses:Insurance:SportsCards     5.00 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A401
          Liabilities:Mastercard    -5.01 USD
          Expenses:Insurance:SportsCards     5.01 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A402
          Liabilities:Mastercard    -5.02 USD
          Expenses:Insurance:SportsCards     5.02 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A403
          Liabilities:Mastercard    -5.03 USD
          Expenses:Insurance:SportsCards     5.03 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A404
          Liabilities:Mastercard    -5.04 USD
          Expenses:Insurance:SportsCards     5.04 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A405
          Liabilities:Mastercard    -5.05 USD
          Expenses:Insurance:SportsCards     5.05 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A406
          Liabilities:Mastercard    -5.06 USD
          Expenses:Insurance:SportsCards     5.06 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A407
          Liabilities:Mastercard    -5.07 USD
          Expenses:Insurance:SportsCards     5.07 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A408
          Liabilities:Mastercard    -5.08 USD
          Expenses:Insurance:SportsCards     5.08 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A409
          Liabilities:Mastercard    -5.09 USD
          Expenses:Insurance:SportsCards     5.09 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A410
          Liabilities:Mastercard    -5.10 USD
          Expenses:Insurance:SportsCards     5.10 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A411
          Liabilities:Mastercard    -5.11 USD
          Expenses:Insurance:SportsCards     5.11 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A412
          Liabilities:Mastercard    -5.12 USD
          Expenses:Insurance:SportsCards     5.12 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A413
          Liabilities:Mastercard    -5.13 USD
          Expenses:Insurance:SportsCards     5.13 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A414
          Liabilities:Mastercard    -5.14 USD
          Expenses:Insurance:SportsCards     5.14 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A415
          Liabilities:Mastercard    -5.15 USD
          Expenses:Insurance:SportsCards     5.15 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A416
          Liabilities:Mastercard    -5.16 USD
          Expenses:Insurance:SportsCards     5.16 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A417
          Liabilities:Mastercard    -5.17 USD
          Expenses:Insurance:SportsCards     5.17 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A418
          Liabilities:Mastercard    -5.18 USD
          Expenses:Insurance:SportsCards     5.18 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A419
          Liabilities:Mastercard    -5.19 USD
          Expenses:Insurance:SportsCards     5.19 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A420
          Liabilities:Mastercard    -5.20 USD
          Expenses:Insurance:SportsCards     5.20 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A421
          Liabilities:Mastercard    -5.21 USD
          Expenses:Insurance:SportsCards     5.21 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A422
          Liabilities:Mastercard    -5.22 USD
          Expenses:Insurance:SportsCards     5.22 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A423
          Liabilities:Mastercard    -5.23 USD
          Expenses:Insurance:SportsCards     5.23 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A424
          Liabilities:Mastercard    -5.24 USD
          Expenses:Insurance:SportsCards     5.24 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A425
          Liabilities:Mastercard    -5.25 USD
          Expenses:Insurance:SportsCards     5.25 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A426
          Liabilities:Mastercard    -5.26 USD
          Expenses:Insurance:SportsCards     5.26 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A427
          Liabilities:Mastercard    -5.27 USD
          Expenses:Insurance:SportsCards     5.27 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A428
          Liabilities:Mastercard    -5.28 USD
          Expenses:Insurance:SportsCards     5.28 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A429
          Liabilities:Mastercard    -5.29 USD
          Expenses:Insurance:SportsCards     5.29 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A430
          Liabilities:Mastercard    -5.30 USD
          Expenses:Insurance:SportsCards     5.30 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A431
          Liabilities:Mastercard    -5.31 USD
          Expenses:Insurance:SportsCards     5.31 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A432
          Liabilities:Mastercard    -5.32 USD
          Expenses:Insurance:SportsCards     5.32 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A433
          Liabilities:Mastercard    -5.33 USD
          Expenses:Insurance:SportsCards     5.33 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A434
          Liabilities:Mastercard    -5.34 USD
          Expenses:Insurance:SportsCards     5.34 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A435
          Liabilities:Mastercard    -5.35 USD
          Expenses:Insurance:SportsCards     5.35 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A436
          Liabilities:Mastercard    -5.36 USD
          Expenses:Insurance:SportsCards     5.36 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A437
          Liabilities:Mastercard    -5.37 USD
          Expenses:Insurance:SportsCards     5.37 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A438
          Liabilities:Mastercard    -5.38 USD
          Expenses:Insurance:SportsCards     5.38 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A439
          Liabilities:Mastercard    -5.39 USD
          Expenses:Insurance:SportsCards     5.39 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A440
          Liabilities:Mastercard    -5.40 USD
          Expenses:Insurance:SportsCards     5.40 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A441
          Liabilities:Mastercard    -5.41 USD
          Expenses:Insurance:SportsCards     5.41 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A442
          Liabilities:Mastercard    -5.42 USD
          Expenses:Insurance:SportsCards     5.42 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A443
          Liabilities:Mastercard    -5.43 USD
          Expenses:Insurance:SportsCards     5.43 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A444
          Liabilities:Mastercard    -5.44 USD
          Expenses:Insurance:SportsCards     5.44 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A445
          Liabilities:Mastercard    -5.45 USD
          Expenses:Insurance:SportsCards     5.45 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A446
          Liabilities:Mastercard    -5.46 USD
          Expenses:Insurance:SportsCards     5.46 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A447
          Liabilities:Mastercard    -5.47 USD
          Expenses:Insurance:SportsCards     5.47 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A448
          Liabilities:Mastercard    -5.48 USD
          Expenses:Insurance:SportsCards     5.48 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A449
          Liabilities:Mastercard    -5.49 USD
          Expenses:Insurance:SportsCards     5.49 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A450
          Liabilities:Mastercard    -5.50 USD
          Expenses:Insurance:SportsCards     5.50 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A451
          Liabilities:Mastercard    -5.51 USD
          Expenses:Insurance:SportsCards     5.51 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A452
          Liabilities:Mastercard    -5.52 USD
          Expenses:Insurance:SportsCards     5.52 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A453
          Liabilities:Mastercard    -5.53 USD
          Expenses:Insurance:SportsCards     5.53 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A454
          Liabilities:Mastercard    -5.54 USD
          Expenses:Insurance:SportsCards     5.54 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A455
          Liabilities:Mastercard    -5.55 USD
          Expenses:Insurance:SportsCards     5.55 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A456
          Liabilities:Mastercard    -5.56 USD
          Expenses:Insurance:SportsCards     5.56 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A457
          Liabilities:Mastercard    -5.57 USD
          Expenses:Insurance:SportsCards     5.57 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A458
          Liabilities:Mastercard    -5.58 USD
          Expenses:Insurance:SportsCards     5.58 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A459
          Liabilities:Mastercard    -5.59 USD
          Expenses:Insurance:SportsCards     5.59 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A460
          Liabilities:Mastercard    -5.60 USD
          Expenses:Insurance:SportsCards     5.60 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A461
          Liabilities:Mastercard    -5.61 USD
          Expenses:Insurance:SportsCards     5.61 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A462
          Liabilities:Mastercard    -5.62 USD
          Expenses:Insurance:SportsCards     5.62 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A463
          Liabilities:Mastercard    -5.63 USD
          Expenses:Insurance:SportsCards     5.63 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A464
          Liabilities:Mastercard    -5.64 USD
          Expenses:Insurance:SportsCards     5.64 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A465
          Liabilities:Mastercard    -5.65 USD
          Expenses:Insurance:SportsCards     5.65 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A466
          Liabilities:Mastercard    -5.66 USD
          Expenses:Insurance:SportsCards     5.66 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A467
          Liabilities:Mastercard    -5.67 USD
          Expenses:Insurance:SportsCards     5.67 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A468
          Liabilities:Mastercard    -5.68 USD
          Expenses:Insurance:SportsCards     5.68 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A469
          Liabilities:Mastercard    -5.69 USD
          Expenses:Insurance:SportsCards     5.69 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A470
          Liabilities:Mastercard    -5.70 USD
          Expenses:Insurance:SportsCards     5.70 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A471
          Liabilities:Mastercard    -5.71 USD
          Expenses:Insurance:SportsCards     5.71 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A472
          Liabilities:Mastercard    -5.72 USD
          Expenses:Insurance:SportsCards     5.72 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A473
          Liabilities:Mastercard    -5.73 USD
          Expenses:Insurance:SportsCards     5.73 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A474
          Liabilities:Mastercard    -5.74 USD
          Expenses:Insurance:SportsCards     5.74 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A475
          Liabilities:Mastercard    -5.75 USD
          Expenses:Insurance:SportsCards     5.75 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A476
          Liabilities:Mastercard    -5.76 USD
          Expenses:Insurance:SportsCards     5.76 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A477
          Liabilities:Mastercard    -5.77 USD
          Expenses:Insurance:SportsCards     5.77 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A478
          Liabilities:Mastercard    -5.78 USD
          Expenses:Insurance:SportsCards     5.78 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A479
          Liabilities:Mastercard    -5.79 USD
          Expenses:Insurance:SportsCards     5.79 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A480
          Liabilities:Mastercard    -5.80 USD
          Expenses:Insurance:SportsCards     5.80 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A481
          Liabilities:Mastercard    -5.81 USD
          Expenses:Insurance:SportsCards     5.81 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A482
          Liabilities:Mastercard    -5.82 USD
          Expenses:Insurance:SportsCards     5.82 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A483
          Liabilities:Mastercard    -5.83 USD
          Expenses:Insurance:SportsCards     5.83 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A484
          Liabilities:Mastercard    -5.84 USD
          Expenses:Insurance:SportsCards     5.84 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A485
          Liabilities:Mastercard    -5.85 USD
          Expenses:Insurance:SportsCards     5.85 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A486
          Liabilities:Mastercard    -5.86 USD
          Expenses:Insurance:SportsCards     5.86 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A487
          Liabilities:Mastercard    -5.87 USD
          Expenses:Insurance:SportsCards     5.87 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A488
          Liabilities:Mastercard    -5.88 USD
          Expenses:Insurance:SportsCards     5.88 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A489
          Liabilities:Mastercard    -5.89 USD
          Expenses:Insurance:SportsCards     5.89 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A490
          Liabilities:Mastercard    -5.90 USD
          Expenses:Insurance:SportsCards     5.90 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A491
          Liabilities:Mastercard    -5.91 USD
          Expenses:Insurance:SportsCards     5.91 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A492
          Liabilities:Mastercard    -5.92 USD
          Expenses:Insurance:SportsCards     5.92 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A493
          Liabilities:Mastercard    -5.93 USD
          Expenses:Insurance:SportsCards     5.93 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A494
          Liabilities:Mastercard    -5.94 USD
          Expenses:Insurance:SportsCards     5.94 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A495
          Liabilities:Mastercard    -5.95 USD
          Expenses:Insurance:SportsCards     5.95 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A496
          Liabilities:Mastercard    -5.96 USD
          Expenses:Insurance:SportsCards     5.96 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A497
          Liabilities:Mastercard    -5.97 USD
          Expenses:Insurance:SportsCards     5.97 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A498
          Liabilities:Mastercard    -5.98 USD
          Expenses:Insurance:SportsCards     5.98 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A499
          Liabilities:Mastercard    -5.99 USD
          Expenses:Insurance:SportsCards     5.99 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A500
          Liabilities:Mastercard    -6.00 USD
          Expenses:Insurance:SportsCards     6.00 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A501
          Liabilities:Mastercard    -6.01 USD
          Expenses:Insurance:SportsCards     6.01 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A502
          Liabilities:Mastercard    -6.02 USD
          Expenses:Insurance:SportsCards     6.02 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A503
          Liabilities:Mastercard    -6.03 USD
          Expenses:Insurance:SportsCards     6.03 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A504
          Liabilities:Mastercard    -6.04 USD
          Expenses:Insurance:SportsCards     6.04 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A505
          Liabilities:Mastercard    -6.05 USD
          Expenses:Insurance:SportsCards     6.05 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A506
          Liabilities:Mastercard    -6.06 USD
          Expenses:Insurance:SportsCards     6.06 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A507
          Liabilities:Mastercard    -6.07 USD
          Expenses:Insurance:SportsCards     6.07 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A508
          Liabilities:Mastercard    -6.08 USD
          Expenses:Insurance:SportsCards     6.08 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A509
          Liabilities:Mastercard    -6.09 USD
          Expenses:Insurance:SportsCards     6.09 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A510
          Liabilities:Mastercard    -6.10 USD
          Expenses:Insurance:SportsCards     6.10 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A511
          Liabilities:Mastercard    -6.11 USD
          Expenses:Insurance:SportsCards     6.11 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A512
          Liabilities:Mastercard    -6.12 USD
          Expenses:Insurance:SportsCards     6.12 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A513
          Liabilities:Mastercard    -6.13 USD
          Expenses:Insurance:SportsCards     6.13 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A514
          Liabilities:Mastercard    -6.14 USD
          Expenses:Insurance:SportsCards     6.14 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A515
          Liabilities:Mastercard    -6.15 USD
          Expenses:Insurance:SportsCards     6.15 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A516
          Liabilities:Mastercard    -6.16 USD
          Expenses:Insurance:SportsCards     6.16 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A517
          Liabilities:Mastercard    -6.17 USD
          Expenses:Insurance:SportsCards     6.17 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A518
          Liabilities:Mastercard    -6.18 USD
          Expenses:Insurance:SportsCards     6.18 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A519
          Liabilities:Mastercard    -6.19 USD
          Expenses:Insurance:SportsCards     6.19 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A520
          Liabilities:Mastercard    -6.20 USD
          Expenses:Insurance:SportsCards     6.20 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A521
          Liabilities:Mastercard    -6.21 USD
          Expenses:Insurance:SportsCards     6.21 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A522
          Liabilities:Mastercard    -6.22 USD
          Expenses:Insurance:SportsCards     6.22 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A523
          Liabilities:Mastercard    -6.23 USD
          Expenses:Insurance:SportsCards     6.23 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A524
          Liabilities:Mastercard    -6.24 USD
          Expenses:Insurance:SportsCards     6.24 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A525
          Liabilities:Mastercard    -6.25 USD
          Expenses:Insurance:SportsCards     6.25 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A526
          Liabilities:Mastercard    -6.26 USD
          Expenses:Insurance:SportsCards     6.26 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A527
          Liabilities:Mastercard    -6.27 USD
          Expenses:Insurance:SportsCards     6.27 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A528
          Liabilities:Mastercard    -6.28 USD
          Expenses:Insurance:SportsCards     6.28 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A529
          Liabilities:Mastercard    -6.29 USD
          Expenses:Insurance:SportsCards     6.29 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A530
          Liabilities:Mastercard    -6.30 USD
          Expenses:Insurance:SportsCards     6.30 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A531
          Liabilities:Mastercard    -6.31 USD
          Expenses:Insurance:SportsCards     6.31 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A532
          Liabilities:Mastercard    -6.32 USD
          Expenses:Insurance:SportsCards     6.32 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A533
          Liabilities:Mastercard    -6.33 USD
          Expenses:Insurance:SportsCards     6.33 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A534
          Liabilities:Mastercard    -6.34 USD
          Expenses:Insurance:SportsCards     6.34 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A535
          Liabilities:Mastercard    -6.35 USD
          Expenses:Insurance:SportsCards     6.35 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A536
          Liabilities:Mastercard    -6.36 USD
          Expenses:Insurance:SportsCards     6.36 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A537
          Liabilities:Mastercard    -6.37 USD
          Expenses:Insurance:SportsCards     6.37 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A538
          Liabilities:Mastercard    -6.38 USD
          Expenses:Insurance:SportsCards     6.38 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A539
          Liabilities:Mastercard    -6.39 USD
          Expenses:Insurance:SportsCards     6.39 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A540
          Liabilities:Mastercard    -6.40 USD
          Expenses:Insurance:SportsCards     6.40 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A541
          Liabilities:Mastercard    -6.41 USD
          Expenses:Insurance:SportsCards     6.41 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A542
          Liabilities:Mastercard    -6.42 USD
          Expenses:Insurance:SportsCards     6.42 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A543
          Liabilities:Mastercard    -6.43 USD
          Expenses:Insurance:SportsCards     6.43 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A544
          Liabilities:Mastercard    -6.44 USD
          Expenses:Insurance:SportsCards     6.44 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A545
          Liabilities:Mastercard    -6.45 USD
          Expenses:Insurance:SportsCards     6.45 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A546
          Liabilities:Mastercard    -6.46 USD
          Expenses:Insurance:SportsCards     6.46 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A547
          Liabilities:Mastercard    -6.47 USD
          Expenses:Insurance:SportsCards     6.47 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A548
          Liabilities:Mastercard    -6.48 USD
          Expenses:Insurance:SportsCards     6.48 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A549
          Liabilities:Mastercard    -6.49 USD
          Expenses:Insurance:SportsCards     6.49 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A550
          Liabilities:Mastercard    -6.50 USD
          Expenses:Insurance:SportsCards     6.50 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A551
          Liabilities:Mastercard    -6.51 USD
          Expenses:Insurance:SportsCards     6.51 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A552
          Liabilities:Mastercard    -6.52 USD
          Expenses:Insurance:SportsCards     6.52 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A553
          Liabilities:Mastercard    -6.53 USD
          Expenses:Insurance:SportsCards     6.53 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A554
          Liabilities:Mastercard    -6.54 USD
          Expenses:Insurance:SportsCards     6.54 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A555
          Liabilities:Mastercard    -6.55 USD
          Expenses:Insurance:SportsCards     6.55 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A556
          Liabilities:Mastercard    -6.56 USD
          Expenses:Insurance:SportsCards     6.56 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A557
          Liabilities:Mastercard    -6.57 USD
          Expenses:Insurance:SportsCards     6.57 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A558
          Liabilities:Mastercard    -6.58 USD
          Expenses:Insurance:SportsCards     6.58 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A559
          Liabilities:Mastercard    -6.59 USD
          Expenses:Insurance:SportsCards     6.59 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A560
          Liabilities:Mastercard    -6.60 USD
          Expenses:Insurance:SportsCards     6.60 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A561
          Liabilities:Mastercard    -6.61 USD
          Expenses:Insurance:SportsCards     6.61 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A562
          Liabilities:Mastercard    -6.62 USD
          Expenses:Insurance:SportsCards     6.62 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A563
          Liabilities:Mastercard    -6.63 USD
          Expenses:Insurance:SportsCards     6.63 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A564
          Liabilities:Mastercard    -6.64 USD
          Expenses:Insurance:SportsCards     6.64 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A565
          Liabilities:Mastercard    -6.65 USD
          Expenses:Insurance:SportsCards     6.65 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A566
          Liabilities:Mastercard    -6.66 USD
          Expenses:Insurance:SportsCards     6.66 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A567
          Liabilities:Mastercard    -6.67 USD
          Expenses:Insurance:SportsCards     6.67 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A568
          Liabilities:Mastercard    -6.68 USD
          Expenses:Insurance:SportsCards     6.68 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A569
          Liabilities:Mastercard    -6.69 USD
          Expenses:Insurance:SportsCards     6.69 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A570
          Liabilities:Mastercard    -6.70 USD
          Expenses:Insurance:SportsCards     6.70 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A571
          Liabilities:Mastercard    -6.71 USD
          Expenses:Insurance:SportsCards     6.71 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A572
          Liabilities:Mastercard    -6.72 USD
          Expenses:Insurance:SportsCards     6.72 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A573
          Liabilities:Mastercard    -6.73 USD
          Expenses:Insurance:SportsCards     6.73 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A574
          Liabilities:Mastercard    -6.74 USD
          Expenses:Insurance:SportsCards     6.74 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A575
          Liabilities:Mastercard    -6.75 USD
          Expenses:Insurance:SportsCards     6.75 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A576
          Liabilities:Mastercard    -6.76 USD
          Expenses:Insurance:SportsCards     6.76 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A577
          Liabilities:Mastercard    -6.77 USD
          Expenses:Insurance:SportsCards     6.77 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A578
          Liabilities:Mastercard    -6.78 USD
          Expenses:Insurance:SportsCards     6.78 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A579
          Liabilities:Mastercard    -6.79 USD
          Expenses:Insurance:SportsCards     6.79 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A580
          Liabilities:Mastercard    -6.80 USD
          Expenses:Insurance:SportsCards     6.80 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A581
          Liabilities:Mastercard    -6.81 USD
          Expenses:Insurance:SportsCards     6.81 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A582
          Liabilities:Mastercard    -6.82 USD
          Expenses:Insurance:SportsCards     6.82 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A583
          Liabilities:Mastercard    -6.83 USD
          Expenses:Insurance:SportsCards     6.83 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A584
          Liabilities:Mastercard    -6.84 USD
          Expenses:Insurance:SportsCards     6.84 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A585
          Liabilities:Mastercard    -6.85 USD
          Expenses:Insurance:SportsCards     6.85 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A586
          Liabilities:Mastercard    -6.86 USD
          Expenses:Insurance:SportsCards     6.86 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A587
          Liabilities:Mastercard    -6.87 USD
          Expenses:Insurance:SportsCards     6.87 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A588
          Liabilities:Mastercard    -6.88 USD
          Expenses:Insurance:SportsCards     6.88 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A589
          Liabilities:Mastercard    -6.89 USD
          Expenses:Insurance:SportsCards     6.89 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A590
          Liabilities:Mastercard    -6.90 USD
          Expenses:Insurance:SportsCards     6.90 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A591
          Liabilities:Mastercard    -6.91 USD
          Expenses:Insurance:SportsCards     6.91 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A592
          Liabilities:Mastercard    -6.92 USD
          Expenses:Insurance:SportsCards     6.92 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A593
          Liabilities:Mastercard    -6.93 USD
          Expenses:Insurance:SportsCards     6.93 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A594
          Liabilities:Mastercard    -6.94 USD
          Expenses:Insurance:SportsCards     6.94 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A595
          Liabilities:Mastercard    -6.95 USD
          Expenses:Insurance:SportsCards     6.95 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A596
          Liabilities:Mastercard    -6.96 USD
          Expenses:Insurance:SportsCards     6.96 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A597
          Liabilities:Mastercard    -6.97 USD
          Expenses:Insurance:SportsCards     6.97 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A598
          Liabilities:Mastercard    -6.98 USD
          Expenses:Insurance:SportsCards     6.98 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A599
          Liabilities:Mastercard    -6.99 USD
          Expenses:Insurance:SportsCards     6.99 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A600
          Liabilities:Mastercard    -7.00 USD
          Expenses:Insurance:SportsCards     7.00 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A601
          Liabilities:Mastercard    -7.01 USD
          Expenses:Insurance:SportsCards     7.01 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A602
          Liabilities:Mastercard    -7.02 USD
          Expenses:Insurance:SportsCards     7.02 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A603
          Liabilities:Mastercard    -7.03 USD
          Expenses:Insurance:SportsCards     7.03 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A604
          Liabilities:Mastercard    -7.04 USD
          Expenses:Insurance:SportsCards     7.04 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A605
          Liabilities:Mastercard    -7.05 USD
          Expenses:Insurance:SportsCards     7.05 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A606
          Liabilities:Mastercard    -7.06 USD
          Expenses:Insurance:SportsCards     7.06 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A607
          Liabilities:Mastercard    -7.07 USD
          Expenses:Insurance:SportsCards     7.07 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A608
          Liabilities:Mastercard    -7.08 USD
          Expenses:Insurance:SportsCards     7.08 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A609
          Liabilities:Mastercard    -7.09 USD
          Expenses:Insurance:SportsCards     7.09 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A610
          Liabilities:Mastercard    -7.10 USD
          Expenses:Insurance:SportsCards     7.10 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A611
          Liabilities:Mastercard    -7.11 USD
          Expenses:Insurance:SportsCards     7.11 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A612
          Liabilities:Mastercard    -7.12 USD
          Expenses:Insurance:SportsCards     7.12 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A613
          Liabilities:Mastercard    -7.13 USD
          Expenses:Insurance:SportsCards     7.13 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A614
          Liabilities:Mastercard    -7.14 USD
          Expenses:Insurance:SportsCards     7.14 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A615
          Liabilities:Mastercard    -7.15 USD
          Expenses:Insurance:SportsCards     7.15 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A616
          Liabilities:Mastercard    -7.16 USD
          Expenses:Insurance:SportsCards     7.16 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A617
          Liabilities:Mastercard    -7.17 USD
          Expenses:Insurance:SportsCards     7.17 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A618
          Liabilities:Mastercard    -7.18 USD
          Expenses:Insurance:SportsCards     7.18 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A619
          Liabilities:Mastercard    -7.19 USD
          Expenses:Insurance:SportsCards     7.19 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A620
          Liabilities:Mastercard    -7.20 USD
          Expenses:Insurance:SportsCards     7.20 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A621
          Liabilities:Mastercard    -7.21 USD
          Expenses:Insurance:SportsCards     7.21 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A622
          Liabilities:Mastercard    -7.22 USD
          Expenses:Insurance:SportsCards     7.22 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A623
          Liabilities:Mastercard    -7.23 USD
          Expenses:Insurance:SportsCards     7.23 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A624
          Liabilities:Mastercard    -7.24 USD
          Expenses:Insurance:SportsCards     7.24 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A625
          Liabilities:Mastercard    -7.25 USD
          Expenses:Insurance:SportsCards     7.25 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A626
          Liabilities:Mastercard    -7.26 USD
          Expenses:Insurance:SportsCards     7.26 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A627
          Liabilities:Mastercard    -7.27 USD
          Expenses:Insurance:SportsCards     7.27 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A628
          Liabilities:Mastercard    -7.28 USD
          Expenses:Insurance:SportsCards     7.28 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A629
          Liabilities:Mastercard    -7.29 USD
          Expenses:Insurance:SportsCards     7.29 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A630
          Liabilities:Mastercard    -7.30 USD
          Expenses:Insurance:SportsCards     7.30 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A631
          Liabilities:Mastercard    -7.31 USD
          Expenses:Insurance:SportsCards     7.31 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A632
          Liabilities:Mastercard    -7.32 USD
          Expenses:Insurance:SportsCards     7.32 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A633
          Liabilities:Mastercard    -7.33 USD
          Expenses:Insurance:SportsCards     7.33 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A634
          Liabilities:Mastercard    -7.34 USD
          Expenses:Insurance:SportsCards     7.34 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A635
          Liabilities:Mastercard    -7.35 USD
          Expenses:Insurance:SportsCards     7.35 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A636
          Liabilities:Mastercard    -7.36 USD
          Expenses:Insurance:SportsCards     7.36 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A637
          Liabilities:Mastercard    -7.37 USD
          Expenses:Insurance:SportsCards     7.37 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A638
          Liabilities:Mastercard    -7.38 USD
          Expenses:Insurance:SportsCards     7.38 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A639
          Liabilities:Mastercard    -7.39 USD
          Expenses:Insurance:SportsCards     7.39 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A640
          Liabilities:Mastercard    -7.40 USD
          Expenses:Insurance:SportsCards     7.40 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A641
          Liabilities:Mastercard    -7.41 USD
          Expenses:Insurance:SportsCards     7.41 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A642
          Liabilities:Mastercard    -7.42 USD
          Expenses:Insurance:SportsCards     7.42 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A643
          Liabilities:Mastercard    -7.43 USD
          Expenses:Insurance:SportsCards     7.43 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A644
          Liabilities:Mastercard    -7.44 USD
          Expenses:Insurance:SportsCards     7.44 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A645
          Liabilities:Mastercard    -7.45 USD
          Expenses:Insurance:SportsCards     7.45 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A646
          Liabilities:Mastercard    -7.46 USD
          Expenses:Insurance:SportsCards     7.46 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A647
          Liabilities:Mastercard    -7.47 USD
          Expenses:Insurance:SportsCards     7.47 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A648
          Liabilities:Mastercard    -7.48 USD
          Expenses:Insurance:SportsCards     7.48 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A649
          Liabilities:Mastercard    -7.49 USD
          Expenses:Insurance:SportsCards     7.49 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A650
          Liabilities:Mastercard    -7.50 USD
          Expenses:Insurance:SportsCards     7.50 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A651
          Liabilities:Mastercard    -7.51 USD
          Expenses:Insurance:SportsCards     7.51 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A652
          Liabilities:Mastercard    -7.52 USD
          Expenses:Insurance:SportsCards     7.52 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A653
          Liabilities:Mastercard    -7.53 USD
          Expenses:Insurance:SportsCards     7.53 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A654
          Liabilities:Mastercard    -7.54 USD
          Expenses:Insurance:SportsCards     7.54 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A655
          Liabilities:Mastercard    -7.55 USD
          Expenses:Insurance:SportsCards     7.55 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A656
          Liabilities:Mastercard    -7.56 USD
          Expenses:Insurance:SportsCards     7.56 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A657
          Liabilities:Mastercard    -7.57 USD
          Expenses:Insurance:SportsCards     7.57 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A658
          Liabilities:Mastercard    -7.58 USD
          Expenses:Insurance:SportsCards     7.58 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A659
          Liabilities:Mastercard    -7.59 USD
          Expenses:Insurance:SportsCards     7.59 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A660
          Liabilities:Mastercard    -7.60 USD
          Expenses:Insurance:SportsCards     7.60 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A661
          Liabilities:Mastercard    -7.61 USD
          Expenses:Insurance:SportsCards     7.61 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A662
          Liabilities:Mastercard    -7.62 USD
          Expenses:Insurance:SportsCards     7.62 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A663
          Liabilities:Mastercard    -7.63 USD
          Expenses:Insurance:SportsCards     7.63 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A664
          Liabilities:Mastercard    -7.64 USD
          Expenses:Insurance:SportsCards     7.64 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A665
          Liabilities:Mastercard    -7.65 USD
          Expenses:Insurance:SportsCards     7.65 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A666
          Liabilities:Mastercard    -7.66 USD
          Expenses:Insurance:SportsCards     7.66 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A667
          Liabilities:Mastercard    -7.67 USD
          Expenses:Insurance:SportsCards     7.67 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A668
          Liabilities:Mastercard    -7.68 USD
          Expenses:Insurance:SportsCards     7.68 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A669
          Liabilities:Mastercard    -7.69 USD
          Expenses:Insurance:SportsCards     7.69 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A670
          Liabilities:Mastercard    -7.70 USD
          Expenses:Insurance:SportsCards     7.70 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A671
          Liabilities:Mastercard    -7.71 USD
          Expenses:Insurance:SportsCards     7.71 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A672
          Liabilities:Mastercard    -7.72 USD
          Expenses:Insurance:SportsCards     7.72 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A673
          Liabilities:Mastercard    -7.73 USD
          Expenses:Insurance:SportsCards     7.73 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A674
          Liabilities:Mastercard    -7.74 USD
          Expenses:Insurance:SportsCards     7.74 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A675
          Liabilities:Mastercard    -7.75 USD
          Expenses:Insurance:SportsCards     7.75 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A676
          Liabilities:Mastercard    -7.76 USD
          Expenses:Insurance:SportsCards     7.76 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A677
          Liabilities:Mastercard    -7.77 USD
          Expenses:Insurance:SportsCards     7.77 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A678
          Liabilities:Mastercard    -7.78 USD
          Expenses:Insurance:SportsCards     7.78 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A679
          Liabilities:Mastercard    -7.79 USD
          Expenses:Insurance:SportsCards     7.79 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A680
          Liabilities:Mastercard    -7.80 USD
          Expenses:Insurance:SportsCards     7.80 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A681
          Liabilities:Mastercard    -7.81 USD
          Expenses:Insurance:SportsCards     7.81 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A682
          Liabilities:Mastercard    -7.82 USD
          Expenses:Insurance:SportsCards     7.82 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A683
          Liabilities:Mastercard    -7.83 USD
          Expenses:Insurance:SportsCards     7.83 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A684
          Liabilities:Mastercard    -7.84 USD
          Expenses:Insurance:SportsCards     7.84 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A685
          Liabilities:Mastercard    -7.85 USD
          Expenses:Insurance:SportsCards     7.85 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A686
          Liabilities:Mastercard    -7.86 USD
          Expenses:Insurance:SportsCards     7.86 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A687
          Liabilities:Mastercard    -7.87 USD
          Expenses:Insurance:SportsCards     7.87 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A688
          Liabilities:Mastercard    -7.88 USD
          Expenses:Insurance:SportsCards     7.88 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A689
          Liabilities:Mastercard    -7.89 USD
          Expenses:Insurance:SportsCards     7.89 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A690
          Liabilities:Mastercard    -7.90 USD
          Expenses:Insurance:SportsCards     7.90 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A691
          Liabilities:Mastercard    -7.91 USD
          Expenses:Insurance:SportsCards     7.91 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A692
          Liabilities:Mastercard    -7.92 USD
          Expenses:Insurance:SportsCards     7.92 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A693
          Liabilities:Mastercard    -7.93 USD
          Expenses:Insurance:SportsCards     7.93 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A694
          Liabilities:Mastercard    -7.94 USD
          Expenses:Insurance:SportsCards     7.94 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A695
          Liabilities:Mastercard    -7.95 USD
          Expenses:Insurance:SportsCards     7.95 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A696
          Liabilities:Mastercard    -7.96 USD
          Expenses:Insurance:SportsCards     7.96 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A697
          Liabilities:Mastercard    -7.97 USD
          Expenses:Insurance:SportsCards     7.97 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A698
          Liabilities:Mastercard    -7.98 USD
          Expenses:Insurance:SportsCards     7.98 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A699
          Liabilities:Mastercard    -7.99 USD
          Expenses:Insurance:SportsCards     7.99 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A700
          Liabilities:Mastercard    -8.00 USD
          Expenses:Insurance:SportsCards     8.00 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A701
          Liabilities:Mastercard    -8.01 USD
          Expenses:Insurance:SportsCards     8.01 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A702
          Liabilities:Mastercard    -8.02 USD
          Expenses:Insurance:SportsCards     8.02 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A703
          Liabilities:Mastercard    -8.03 USD
          Expenses:Insurance:SportsCards     8.03 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A704
          Liabilities:Mastercard    -8.04 USD
          Expenses:Insurance:SportsCards     8.04 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A705
          Liabilities:Mastercard    -8.05 USD
          Expenses:Insurance:SportsCards     8.05 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A706
          Liabilities:Mastercard    -8.06 USD
          Expenses:Insurance:SportsCards     8.06 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A707
          Liabilities:Mastercard    -8.07 USD
          Expenses:Insurance:SportsCards     8.07 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A708
          Liabilities:Mastercard    -8.08 USD
          Expenses:Insurance:SportsCards     8.08 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A709
          Liabilities:Mastercard    -8.09 USD
          Expenses:Insurance:SportsCards     8.09 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A710
          Liabilities:Mastercard    -8.10 USD
          Expenses:Insurance:SportsCards     8.10 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A711
          Liabilities:Mastercard    -8.11 USD
          Expenses:Insurance:SportsCards     8.11 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A712
          Liabilities:Mastercard    -8.12 USD
          Expenses:Insurance:SportsCards     8.12 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A713
          Liabilities:Mastercard    -8.13 USD
          Expenses:Insurance:SportsCards     8.13 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A714
          Liabilities:Mastercard    -8.14 USD
          Expenses:Insurance:SportsCards     8.14 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A715
          Liabilities:Mastercard    -8.15 USD
          Expenses:Insurance:SportsCards     8.15 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A716
          Liabilities:Mastercard    -8.16 USD
          Expenses:Insurance:SportsCards     8.16 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A717
          Liabilities:Mastercard    -8.17 USD
          Expenses:Insurance:SportsCards     8.17 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A718
          Liabilities:Mastercard    -8.18 USD
          Expenses:Insurance:SportsCards     8.18 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A719
          Liabilities:Mastercard    -8.19 USD
          Expenses:Insurance:SportsCards     8.19 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A720
          Liabilities:Mastercard    -8.20 USD
          Expenses:Insurance:SportsCards     8.20 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A721
          Liabilities:Mastercard    -8.21 USD
          Expenses:Insurance:SportsCards     8.21 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A722
          Liabilities:Mastercard    -8.22 USD
          Expenses:Insurance:SportsCards     8.22 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A723
          Liabilities:Mastercard    -8.23 USD
          Expenses:Insurance:SportsCards     8.23 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A724
          Liabilities:Mastercard    -8.24 USD
          Expenses:Insurance:SportsCards     8.24 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A725
          Liabilities:Mastercard    -8.25 USD
          Expenses:Insurance:SportsCards     8.25 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A726
          Liabilities:Mastercard    -8.26 USD
          Expenses:Insurance:SportsCards     8.26 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A727
          Liabilities:Mastercard    -8.27 USD
          Expenses:Insurance:SportsCards     8.27 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A728
          Liabilities:Mastercard    -8.28 USD
          Expenses:Insurance:SportsCards     8.28 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A729
          Liabilities:Mastercard    -8.29 USD
          Expenses:Insurance:SportsCards     8.29 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A730
          Liabilities:Mastercard    -8.30 USD
          Expenses:Insurance:SportsCards     8.30 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A731
          Liabilities:Mastercard    -8.31 USD
          Expenses:Insurance:SportsCards     8.31 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A732
          Liabilities:Mastercard    -8.32 USD
          Expenses:Insurance:SportsCards     8.32 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A733
          Liabilities:Mastercard    -8.33 USD
          Expenses:Insurance:SportsCards     8.33 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A734
          Liabilities:Mastercard    -8.34 USD
          Expenses:Insurance:SportsCards     8.34 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A735
          Liabilities:Mastercard    -8.35 USD
          Expenses:Insurance:SportsCards     8.35 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A736
          Liabilities:Mastercard    -8.36 USD
          Expenses:Insurance:SportsCards     8.36 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A737
          Liabilities:Mastercard    -8.37 USD
          Expenses:Insurance:SportsCards     8.37 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A738
          Liabilities:Mastercard    -8.38 USD
          Expenses:Insurance:SportsCards     8.38 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A739
          Liabilities:Mastercard    -8.39 USD
          Expenses:Insurance:SportsCards     8.39 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A740
          Liabilities:Mastercard    -8.40 USD
          Expenses:Insurance:SportsCards     8.40 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A741
          Liabilities:Mastercard    -8.41 USD
          Expenses:Insurance:SportsCards     8.41 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A742
          Liabilities:Mastercard    -8.42 USD
          Expenses:Insurance:SportsCards     8.42 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A743
          Liabilities:Mastercard    -8.43 USD
          Expenses:Insurance:SportsCards     8.43 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A744
          Liabilities:Mastercard    -8.44 USD
          Expenses:Insurance:SportsCards     8.44 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A745
          Liabilities:Mastercard    -8.45 USD
          Expenses:Insurance:SportsCards     8.45 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A746
          Liabilities:Mastercard    -8.46 USD
          Expenses:Insurance:SportsCards     8.46 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A747
          Liabilities:Mastercard    -8.47 USD
          Expenses:Insurance:SportsCards     8.47 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A748
          Liabilities:Mastercard    -8.48 USD
          Expenses:Insurance:SportsCards     8.48 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A749
          Liabilities:Mastercard    -8.49 USD
          Expenses:Insurance:SportsCards     8.49 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A750
          Liabilities:Mastercard    -8.50 USD
          Expenses:Insurance:SportsCards     8.50 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A751
          Liabilities:Mastercard    -8.51 USD
          Expenses:Insurance:SportsCards     8.51 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A752
          Liabilities:Mastercard    -8.52 USD
          Expenses:Insurance:SportsCards     8.52 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A753
          Liabilities:Mastercard    -8.53 USD
          Expenses:Insurance:SportsCards     8.53 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A754
          Liabilities:Mastercard    -8.54 USD
          Expenses:Insurance:SportsCards     8.54 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A755
          Liabilities:Mastercard    -8.55 USD
          Expenses:Insurance:SportsCards     8.55 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A756
          Liabilities:Mastercard    -8.56 USD
          Expenses:Insurance:SportsCards     8.56 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A757
          Liabilities:Mastercard    -8.57 USD
          Expenses:Insurance:SportsCards     8.57 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A758
          Liabilities:Mastercard    -8.58 USD
          Expenses:Insurance:SportsCards     8.58 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A759
          Liabilities:Mastercard    -8.59 USD
          Expenses:Insurance:SportsCards     8.59 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A760
          Liabilities:Mastercard    -8.60 USD
          Expenses:Insurance:SportsCards     8.60 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A761
          Liabilities:Mastercard    -8.61 USD
          Expenses:Insurance:SportsCards     8.61 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A762
          Liabilities:Mastercard    -8.62 USD
          Expenses:Insurance:SportsCards     8.62 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A763
          Liabilities:Mastercard    -8.63 USD
          Expenses:Insurance:SportsCards     8.63 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A764
          Liabilities:Mastercard    -8.64 USD
          Expenses:Insurance:SportsCards     8.64 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A765
          Liabilities:Mastercard    -8.65 USD
          Expenses:Insurance:SportsCards     8.65 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A766
          Liabilities:Mastercard    -8.66 USD
          Expenses:Insurance:SportsCards     8.66 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A767
          Liabilities:Mastercard    -8.67 USD
          Expenses:Insurance:SportsCards     8.67 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A768
          Liabilities:Mastercard    -8.68 USD
          Expenses:Insurance:SportsCards     8.68 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A769
          Liabilities:Mastercard    -8.69 USD
          Expenses:Insurance:SportsCards     8.69 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A770
          Liabilities:Mastercard    -8.70 USD
          Expenses:Insurance:SportsCards     8.70 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A771
          Liabilities:Mastercard    -8.71 USD
          Expenses:Insurance:SportsCards     8.71 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A772
          Liabilities:Mastercard    -8.72 USD
          Expenses:Insurance:SportsCards     8.72 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A773
          Liabilities:Mastercard    -8.73 USD
          Expenses:Insurance:SportsCards     8.73 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A774
          Liabilities:Mastercard    -8.74 USD
          Expenses:Insurance:SportsCards     8.74 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A775
          Liabilities:Mastercard    -8.75 USD
          Expenses:Insurance:SportsCards     8.75 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A776
          Liabilities:Mastercard    -8.76 USD
          Expenses:Insurance:SportsCards     8.76 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A777
          Liabilities:Mastercard    -8.77 USD
          Expenses:Insurance:SportsCards     8.77 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A778
          Liabilities:Mastercard    -8.78 USD
          Expenses:Insurance:SportsCards     8.78 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A779
          Liabilities:Mastercard    -8.79 USD
          Expenses:Insurance:SportsCards     8.79 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A780
          Liabilities:Mastercard    -8.80 USD
          Expenses:Insurance:SportsCards     8.80 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A781
          Liabilities:Mastercard    -8.81 USD
          Expenses:Insurance:SportsCards     8.81 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A782
          Liabilities:Mastercard    -8.82 USD
          Expenses:Insurance:SportsCards     8.82 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A783
          Liabilities:Mastercard    -8.83 USD
          Expenses:Insurance:SportsCards     8.83 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A784
          Liabilities:Mastercard    -8.84 USD
          Expenses:Insurance:SportsCards     8.84 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A785
          Liabilities:Mastercard    -8.85 USD
          Expenses:Insurance:SportsCards     8.85 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A786
          Liabilities:Mastercard    -8.86 USD
          Expenses:Insurance:SportsCards     8.86 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A787
          Liabilities:Mastercard    -8.87 USD
          Expenses:Insurance:SportsCards     8.87 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A788
          Liabilities:Mastercard    -8.88 USD
          Expenses:Insurance:SportsCards     8.88 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A789
          Liabilities:Mastercard    -8.89 USD
          Expenses:Insurance:SportsCards     8.89 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A790
          Liabilities:Mastercard    -8.90 USD
          Expenses:Insurance:SportsCards     8.90 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A791
          Liabilities:Mastercard    -8.91 USD
          Expenses:Insurance:SportsCards     8.91 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A792
          Liabilities:Mastercard    -8.92 USD
          Expenses:Insurance:SportsCards     8.92 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A793
          Liabilities:Mastercard    -8.93 USD
          Expenses:Insurance:SportsCards     8.93 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A794
          Liabilities:Mastercard    -8.94 USD
          Expenses:Insurance:SportsCards     8.94 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A795
          Liabilities:Mastercard    -8.95 USD
          Expenses:Insurance:SportsCards     8.95 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A796
          Liabilities:Mastercard    -8.96 USD
          Expenses:Insurance:SportsCards     8.96 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A797
          Liabilities:Mastercard    -8.97 USD
          Expenses:Insurance:SportsCards     8.97 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A798
          Liabilities:Mastercard    -8.98 USD
          Expenses:Insurance:SportsCards     8.98 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A799
          Liabilities:Mastercard    -8.99 USD
          Expenses:Insurance:SportsCards     8.99 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A800
          Liabilities:Mastercard    -9.00 USD
          Expenses:Insurance:SportsCards     9.00 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A801
          Liabilities:Mastercard    -9.01 USD
          Expenses:Insurance:SportsCards     9.01 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A802
          Liabilities:Mastercard    -9.02 USD
          Expenses:Insurance:SportsCards     9.02 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A803
          Liabilities:Mastercard    -9.03 USD
          Expenses:Insurance:SportsCards     9.03 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A804
          Liabilities:Mastercard    -9.04 USD
          Expenses:Insurance:SportsCards     9.04 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A805
          Liabilities:Mastercard    -9.05 USD
          Expenses:Insurance:SportsCards     9.05 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A806
          Liabilities:Mastercard    -9.06 USD
          Expenses:Insurance:SportsCards     9.06 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A807
          Liabilities:Mastercard    -9.07 USD
          Expenses:Insurance:SportsCards     9.07 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A808
          Liabilities:Mastercard    -9.08 USD
          Expenses:Insurance:SportsCards     9.08 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A809
          Liabilities:Mastercard    -9.09 USD
          Expenses:Insurance:SportsCards     9.09 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A810
          Liabilities:Mastercard    -9.10 USD
          Expenses:Insurance:SportsCards     9.10 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A811
          Liabilities:Mastercard    -9.11 USD
          Expenses:Insurance:SportsCards     9.11 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A812
          Liabilities:Mastercard    -9.12 USD
          Expenses:Insurance:SportsCards     9.12 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A813
          Liabilities:Mastercard    -9.13 USD
          Expenses:Insurance:SportsCards     9.13 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A814
          Liabilities:Mastercard    -9.14 USD
          Expenses:Insurance:SportsCards     9.14 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A815
          Liabilities:Mastercard    -9.15 USD
          Expenses:Insurance:SportsCards     9.15 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A816
          Liabilities:Mastercard    -9.16 USD
          Expenses:Insurance:SportsCards     9.16 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A817
          Liabilities:Mastercard    -9.17 USD
          Expenses:Insurance:SportsCards     9.17 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A818
          Liabilities:Mastercard    -9.18 USD
          Expenses:Insurance:SportsCards     9.18 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A819
          Liabilities:Mastercard    -9.19 USD
          Expenses:Insurance:SportsCards     9.19 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A820
          Liabilities:Mastercard    -9.20 USD
          Expenses:Insurance:SportsCards     9.20 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A821
          Liabilities:Mastercard    -9.21 USD
          Expenses:Insurance:SportsCards     9.21 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A822
          Liabilities:Mastercard    -9.22 USD
          Expenses:Insurance:SportsCards     9.22 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A823
          Liabilities:Mastercard    -9.23 USD
          Expenses:Insurance:SportsCards     9.23 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A824
          Liabilities:Mastercard    -9.24 USD
          Expenses:Insurance:SportsCards     9.24 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A825
          Liabilities:Mastercard    -9.25 USD
          Expenses:Insurance:SportsCards     9.25 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A826
          Liabilities:Mastercard    -9.26 USD
          Expenses:Insurance:SportsCards     9.26 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A827
          Liabilities:Mastercard    -9.27 USD
          Expenses:Insurance:SportsCards     9.27 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A828
          Liabilities:Mastercard    -9.28 USD
          Expenses:Insurance:SportsCards     9.28 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A829
          Liabilities:Mastercard    -9.29 USD
          Expenses:Insurance:SportsCards     9.29 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A830
          Liabilities:Mastercard    -9.30 USD
          Expenses:Insurance:SportsCards     9.30 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A831
          Liabilities:Mastercard    -9.31 USD
          Expenses:Insurance:SportsCards     9.31 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A832
          Liabilities:Mastercard    -9.32 USD
          Expenses:Insurance:SportsCards     9.32 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A833
          Liabilities:Mastercard    -9.33 USD
          Expenses:Insurance:SportsCards     9.33 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A834
          Liabilities:Mastercard    -9.34 USD
          Expenses:Insurance:SportsCards     9.34 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A835
          Liabilities:Mastercard    -9.35 USD
          Expenses:Insurance:SportsCards     9.35 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A836
          Liabilities:Mastercard    -9.36 USD
          Expenses:Insurance:SportsCards     9.36 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A837
          Liabilities:Mastercard    -9.37 USD
          Expenses:Insurance:SportsCards     9.37 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A838
          Liabilities:Mastercard    -9.38 USD
          Expenses:Insurance:SportsCards     9.38 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A839
          Liabilities:Mastercard    -9.39 USD
          Expenses:Insurance:SportsCards     9.39 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A840
          Liabilities:Mastercard    -9.40 USD
          Expenses:Insurance:SportsCards     9.40 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A841
          Liabilities:Mastercard    -9.41 USD
          Expenses:Insurance:SportsCards     9.41 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A842
          Liabilities:Mastercard    -9.42 USD
          Expenses:Insurance:SportsCards     9.42 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A843
          Liabilities:Mastercard    -9.43 USD
          Expenses:Insurance:SportsCards     9.43 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A844
          Liabilities:Mastercard    -9.44 USD
          Expenses:Insurance:SportsCards     9.44 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A845
          Liabilities:Mastercard    -9.45 USD
          Expenses:Insurance:SportsCards     9.45 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A846
          Liabilities:Mastercard    -9.46 USD
          Expenses:Insurance:SportsCards     9.46 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A847
          Liabilities:Mastercard    -9.47 USD
          Expenses:Insurance:SportsCards     9.47 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A848
          Liabilities:Mastercard    -9.48 USD
          Expenses:Insurance:SportsCards     9.48 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A849
          Liabilities:Mastercard    -9.49 USD
          Expenses:Insurance:SportsCards     9.49 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A850
          Liabilities:Mastercard    -9.50 USD
          Expenses:Insurance:SportsCards     9.50 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A851
          Liabilities:Mastercard    -9.51 USD
          Expenses:Insurance:SportsCards     9.51 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A852
          Liabilities:Mastercard    -9.52 USD
          Expenses:Insurance:SportsCards     9.52 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A853
          Liabilities:Mastercard    -9.53 USD
          Expenses:Insurance:SportsCards     9.53 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A854
          Liabilities:Mastercard    -9.54 USD
          Expenses:Insurance:SportsCards     9.54 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A855
          Liabilities:Mastercard    -9.55 USD
          Expenses:Insurance:SportsCards     9.55 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A856
          Liabilities:Mastercard    -9.56 USD
          Expenses:Insurance:SportsCards     9.56 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A857
          Liabilities:Mastercard    -9.57 USD
          Expenses:Insurance:SportsCards     9.57 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A858
          Liabilities:Mastercard    -9.58 USD
          Expenses:Insurance:SportsCards     9.58 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A859
          Liabilities:Mastercard    -9.59 USD
          Expenses:Insurance:SportsCards     9.59 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A860
          Liabilities:Mastercard    -9.60 USD
          Expenses:Insurance:SportsCards     9.60 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A861
          Liabilities:Mastercard    -9.61 USD
          Expenses:Insurance:SportsCards     9.61 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A862
          Liabilities:Mastercard    -9.62 USD
          Expenses:Insurance:SportsCards     9.62 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A863
          Liabilities:Mastercard    -9.63 USD
          Expenses:Insurance:SportsCards     9.63 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A864
          Liabilities:Mastercard    -9.64 USD
          Expenses:Insurance:SportsCards     9.64 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A865
          Liabilities:Mastercard    -9.65 USD
          Expenses:Insurance:SportsCards     9.65 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A866
          Liabilities:Mastercard    -9.66 USD
          Expenses:Insurance:SportsCards     9.66 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A867
          Liabilities:Mastercard    -9.67 USD
          Expenses:Insurance:SportsCards     9.67 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A868
          Liabilities:Mastercard    -9.68 USD
          Expenses:Insurance:SportsCards     9.68 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A869
          Liabilities:Mastercard    -9.69 USD
          Expenses:Insurance:SportsCards     9.69 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A870
          Liabilities:Mastercard    -9.70 USD
          Expenses:Insurance:SportsCards     9.70 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A871
          Liabilities:Mastercard    -9.71 USD
          Expenses:Insurance:SportsCards     9.71 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A872
          Liabilities:Mastercard    -9.72 USD
          Expenses:Insurance:SportsCards     9.72 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A873
          Liabilities:Mastercard    -9.73 USD
          Expenses:Insurance:SportsCards     9.73 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A874
          Liabilities:Mastercard    -9.74 USD
          Expenses:Insurance:SportsCards     9.74 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A875
          Liabilities:Mastercard    -9.75 USD
          Expenses:Insurance:SportsCards     9.75 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A876
          Liabilities:Mastercard    -9.76 USD
          Expenses:Insurance:SportsCards     9.76 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A877
          Liabilities:Mastercard    -9.77 USD
          Expenses:Insurance:SportsCards     9.77 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A878
          Liabilities:Mastercard    -9.78 USD
          Expenses:Insurance:SportsCards     9.78 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A879
          Liabilities:Mastercard    -9.79 USD
          Expenses:Insurance:SportsCards     9.79 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A880
          Liabilities:Mastercard    -9.80 USD
          Expenses:Insurance:SportsCards     9.80 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A881
          Liabilities:Mastercard    -9.81 USD
          Expenses:Insurance:SportsCards     9.81 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A882
          Liabilities:Mastercard    -9.82 USD
          Expenses:Insurance:SportsCards     9.82 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A883
          Liabilities:Mastercard    -9.83 USD
          Expenses:Insurance:SportsCards     9.83 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A884
          Liabilities:Mastercard    -9.84 USD
          Expenses:Insurance:SportsCards     9.84 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A885
          Liabilities:Mastercard    -9.85 USD
          Expenses:Insurance:SportsCards     9.85 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A886
          Liabilities:Mastercard    -9.86 USD
          Expenses:Insurance:SportsCards     9.86 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A887
          Liabilities:Mastercard    -9.87 USD
          Expenses:Insurance:SportsCards     9.87 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A888
          Liabilities:Mastercard    -9.88 USD
          Expenses:Insurance:SportsCards     9.88 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A889
          Liabilities:Mastercard    -9.89 USD
          Expenses:Insurance:SportsCards     9.89 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A890
          Liabilities:Mastercard    -9.90 USD
          Expenses:Insurance:SportsCards     9.90 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A891
          Liabilities:Mastercard    -9.91 USD
          Expenses:Insurance:SportsCards     9.91 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A892
          Liabilities:Mastercard    -9.92 USD
          Expenses:Insurance:SportsCards     9.92 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A893
          Liabilities:Mastercard    -9.93 USD
          Expenses:Insurance:SportsCards     9.93 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A894
          Liabilities:Mastercard    -9.94 USD
          Expenses:Insurance:SportsCards     9.94 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A895
          Liabilities:Mastercard    -9.95 USD
          Expenses:Insurance:SportsCards     9.95 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A896
          Liabilities:Mastercard    -9.96 USD
          Expenses:Insurance:SportsCards     9.96 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A897
          Liabilities:Mastercard    -9.97 USD
          Expenses:Insurance:SportsCards     9.97 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A898
          Liabilities:Mastercard    -9.98 USD
          Expenses:Insurance:SportsCards     9.98 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A899
          Liabilities:Mastercard    -9.99 USD
          Expenses:Insurance:SportsCards     9.99 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A900
          Liabilities:Mastercard    -10.00 USD
          Expenses:Insurance:SportsCards     10.00 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A901
          Liabilities:Mastercard    -10.01 USD
          Expenses:Insurance:SportsCards     10.01 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A902
          Liabilities:Mastercard    -10.02 USD
          Expenses:Insurance:SportsCards     10.02 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A903
          Liabilities:Mastercard    -10.03 USD
          Expenses:Insurance:SportsCards     10.03 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A904
          Liabilities:Mastercard    -10.04 USD
          Expenses:Insurance:SportsCards     10.04 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A905
          Liabilities:Mastercard    -10.05 USD
          Expenses:Insurance:SportsCards     10.05 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A906
          Liabilities:Mastercard    -10.06 USD
          Expenses:Insurance:SportsCards     10.06 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A907
          Liabilities:Mastercard    -10.07 USD
          Expenses:Insurance:SportsCards     10.07 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A908
          Liabilities:Mastercard    -10.08 USD
          Expenses:Insurance:SportsCards     10.08 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A909
          Liabilities:Mastercard    -10.09 USD
          Expenses:Insurance:SportsCards     10.09 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A910
          Liabilities:Mastercard    -10.10 USD
          Expenses:Insurance:SportsCards     10.10 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A911
          Liabilities:Mastercard    -10.11 USD
          Expenses:Insurance:SportsCards     10.11 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A912
          Liabilities:Mastercard    -10.12 USD
          Expenses:Insurance:SportsCards     10.12 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A913
          Liabilities:Mastercard    -10.13 USD
          Expenses:Insurance:SportsCards     10.13 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A914
          Liabilities:Mastercard    -10.14 USD
          Expenses:Insurance:SportsCards     10.14 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A915
          Liabilities:Mastercard    -10.15 USD
          Expenses:Insurance:SportsCards     10.15 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A916
          Liabilities:Mastercard    -10.16 USD
          Expenses:Insurance:SportsCards     10.16 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A917
          Liabilities:Mastercard    -10.17 USD
          Expenses:Insurance:SportsCards     10.17 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A918
          Liabilities:Mastercard    -10.18 USD
          Expenses:Insurance:SportsCards     10.18 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A919
          Liabilities:Mastercard    -10.19 USD
          Expenses:Insurance:SportsCards     10.19 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A920
          Liabilities:Mastercard    -10.20 USD
          Expenses:Insurance:SportsCards     10.20 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A921
          Liabilities:Mastercard    -10.21 USD
          Expenses:Insurance:SportsCards     10.21 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A922
          Liabilities:Mastercard    -10.22 USD
          Expenses:Insurance:SportsCards     10.22 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A923
          Liabilities:Mastercard    -10.23 USD
          Expenses:Insurance:SportsCards     10.23 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A924
          Liabilities:Mastercard    -10.24 USD
          Expenses:Insurance:SportsCards     10.24 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A925
          Liabilities:Mastercard    -10.25 USD
          Expenses:Insurance:SportsCards     10.25 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A926
          Liabilities:Mastercard    -10.26 USD
          Expenses:Insurance:SportsCards     10.26 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A927
          Liabilities:Mastercard    -10.27 USD
          Expenses:Insurance:SportsCards     10.27 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A928
          Liabilities:Mastercard    -10.28 USD
          Expenses:Insurance:SportsCards     10.28 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A929
          Liabilities:Mastercard    -10.29 USD
          Expenses:Insurance:SportsCards     10.29 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A930
          Liabilities:Mastercard    -10.30 USD
          Expenses:Insurance:SportsCards     10.30 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A931
          Liabilities:Mastercard    -10.31 USD
          Expenses:Insurance:SportsCards     10.31 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A932
          Liabilities:Mastercard    -10.32 USD
          Expenses:Insurance:SportsCards     10.32 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A933
          Liabilities:Mastercard    -10.33 USD
          Expenses:Insurance:SportsCards     10.33 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A934
          Liabilities:Mastercard    -10.34 USD
          Expenses:Insurance:SportsCards     10.34 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A935
          Liabilities:Mastercard    -10.35 USD
          Expenses:Insurance:SportsCards     10.35 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A936
          Liabilities:Mastercard    -10.36 USD
          Expenses:Insurance:SportsCards     10.36 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A937
          Liabilities:Mastercard    -10.37 USD
          Expenses:Insurance:SportsCards     10.37 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A938
          Liabilities:Mastercard    -10.38 USD
          Expenses:Insurance:SportsCards     10.38 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A939
          Liabilities:Mastercard    -10.39 USD
          Expenses:Insurance:SportsCards     10.39 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A940
          Liabilities:Mastercard    -10.40 USD
          Expenses:Insurance:SportsCards     10.40 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A941
          Liabilities:Mastercard    -10.41 USD
          Expenses:Insurance:SportsCards     10.41 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A942
          Liabilities:Mastercard    -10.42 USD
          Expenses:Insurance:SportsCards     10.42 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A943
          Liabilities:Mastercard    -10.43 USD
          Expenses:Insurance:SportsCards     10.43 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A944
          Liabilities:Mastercard    -10.44 USD
          Expenses:Insurance:SportsCards     10.44 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A945
          Liabilities:Mastercard    -10.45 USD
          Expenses:Insurance:SportsCards     10.45 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A946
          Liabilities:Mastercard    -10.46 USD
          Expenses:Insurance:SportsCards     10.46 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A947
          Liabilities:Mastercard    -10.47 USD
          Expenses:Insurance:SportsCards     10.47 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A948
          Liabilities:Mastercard    -10.48 USD
          Expenses:Insurance:SportsCards     10.48 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A949
          Liabilities:Mastercard    -10.49 USD
          Expenses:Insurance:SportsCards     10.49 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A950
          Liabilities:Mastercard    -10.50 USD
          Expenses:Insurance:SportsCards     10.50 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A951
          Liabilities:Mastercard    -10.51 USD
          Expenses:Insurance:SportsCards     10.51 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A952
          Liabilities:Mastercard    -10.52 USD
          Expenses:Insurance:SportsCards     10.52 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A953
          Liabilities:Mastercard    -10.53 USD
          Expenses:Insurance:SportsCards     10.53 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A954
          Liabilities:Mastercard    -10.54 USD
          Expenses:Insurance:SportsCards     10.54 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A955
          Liabilities:Mastercard    -10.55 USD
          Expenses:Insurance:SportsCards     10.55 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A956
          Liabilities:Mastercard    -10.56 USD
          Expenses:Insurance:SportsCards     10.56 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A957
          Liabilities:Mastercard    -10.57 USD
          Expenses:Insurance:SportsCards     10.57 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A958
          Liabilities:Mastercard    -10.58 USD
          Expenses:Insurance:SportsCards     10.58 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A959
          Liabilities:Mastercard    -10.59 USD
          Expenses:Insurance:SportsCards     10.59 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A960
          Liabilities:Mastercard    -10.60 USD
          Expenses:Insurance:SportsCards     10.60 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A961
          Liabilities:Mastercard    -10.61 USD
          Expenses:Insurance:SportsCards     10.61 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A962
          Liabilities:Mastercard    -10.62 USD
          Expenses:Insurance:SportsCards     10.62 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A963
          Liabilities:Mastercard    -10.63 USD
          Expenses:Insurance:SportsCards     10.63 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A964
          Liabilities:Mastercard    -10.64 USD
          Expenses:Insurance:SportsCards     10.64 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A965
          Liabilities:Mastercard    -10.65 USD
          Expenses:Insurance:SportsCards     10.65 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A966
          Liabilities:Mastercard    -10.66 USD
          Expenses:Insurance:SportsCards     10.66 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A967
          Liabilities:Mastercard    -10.67 USD
          Expenses:Insurance:SportsCards     10.67 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A968
          Liabilities:Mastercard    -10.68 USD
          Expenses:Insurance:SportsCards     10.68 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A969
          Liabilities:Mastercard    -10.69 USD
          Expenses:Insurance:SportsCards     10.69 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A970
          Liabilities:Mastercard    -10.70 USD
          Expenses:Insurance:SportsCards     10.70 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A971
          Liabilities:Mastercard    -10.71 USD
          Expenses:Insurance:SportsCards     10.71 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A972
          Liabilities:Mastercard    -10.72 USD
          Expenses:Insurance:SportsCards     10.72 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A973
          Liabilities:Mastercard    -10.73 USD
          Expenses:Insurance:SportsCards     10.73 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A974
          Liabilities:Mastercard    -10.74 USD
          Expenses:Insurance:SportsCards     10.74 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A975
          Liabilities:Mastercard    -10.75 USD
          Expenses:Insurance:SportsCards     10.75 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A976
          Liabilities:Mastercard    -10.76 USD
          Expenses:Insurance:SportsCards     10.76 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A977
          Liabilities:Mastercard    -10.77 USD
          Expenses:Insurance:SportsCards     10.77 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A978
          Liabilities:Mastercard    -10.78 USD
          Expenses:Insurance:SportsCards     10.78 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A979
          Liabilities:Mastercard    -10.79 USD
          Expenses:Insurance:SportsCards     10.79 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A980
          Liabilities:Mastercard    -10.80 USD
          Expenses:Insurance:SportsCards     10.80 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A981
          Liabilities:Mastercard    -10.81 USD
          Expenses:Insurance:SportsCards     10.81 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A982
          Liabilities:Mastercard    -10.82 USD
          Expenses:Insurance:SportsCards     10.82 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A983
          Liabilities:Mastercard    -10.83 USD
          Expenses:Insurance:SportsCards     10.83 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A984
          Liabilities:Mastercard    -10.84 USD
          Expenses:Insurance:SportsCards     10.84 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A985
          Liabilities:Mastercard    -10.85 USD
          Expenses:Insurance:SportsCards     10.85 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A986
          Liabilities:Mastercard    -10.86 USD
          Expenses:Insurance:SportsCards     10.86 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A987
          Liabilities:Mastercard    -10.87 USD
          Expenses:Insurance:SportsCards     10.87 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A988
          Liabilities:Mastercard    -10.88 USD
          Expenses:Insurance:SportsCards     10.88 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A989
          Liabilities:Mastercard    -10.89 USD
          Expenses:Insurance:SportsCards     10.89 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A990
          Liabilities:Mastercard    -10.90 USD
          Expenses:Insurance:SportsCards     10.90 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A991
          Liabilities:Mastercard    -10.91 USD
          Expenses:Insurance:SportsCards     10.91 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A992
          Liabilities:Mastercard    -10.92 USD
          Expenses:Insurance:SportsCards     10.92 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A993
          Liabilities:Mastercard    -10.93 USD
          Expenses:Insurance:SportsCards     10.93 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A994
          Liabilities:Mastercard    -10.94 USD
          Expenses:Insurance:SportsCards     10.94 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A995
          Liabilities:Mastercard    -10.95 USD
          Expenses:Insurance:SportsCards     10.95 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A996
          Liabilities:Mastercard    -10.96 USD
          Expenses:Insurance:SportsCards     10.96 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A997
          Liabilities:Mastercard    -10.97 USD
          Expenses:Insurance:SportsCards     10.97 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A998
          Liabilities:Mastercard    -10.98 USD
          Expenses:Insurance:SportsCards     10.98 USD
            effective_date: 2014-03-01

        2014-02-01 * "Insure sports card: 1 month"
          card_id: A999
          Liabilities:Mastercard    -10.99 USD
          Expenses:Insurance:SportsCards     10.99 USD
            effective_date: 2014-03-01
        """

        # Should turn into 1000*2 transactions plus 2 opens, plus 1
        NUM_ITEMS = 1000
        ENTRIES_PER_ITEM = 2
        LEN_ENTRIES = 1 + 2 + (NUM_ITEMS * ENTRIES_PER_ITEM)

        new_entries, _ = effective_date(entries, options_map, None)

        print()
        link_counts = {}
        for e in new_entries:
            if isinstance(e, data.Transaction):
                entry_link = next(iter(e.links)) if e.links else ''
                if entry_link:
                    if entry_link not in link_counts:
                        link_counts[entry_link] = 0
                    link_counts[entry_link] += 1
                # print(e.date,
                #       e.postings[0].units,
                #       e.meta['card_id'],
                #       entry_link)

        self.assertEqual(len(new_entries), LEN_ENTRIES)
        self.assertEqual(len(link_counts), NUM_ITEMS)
        self.assertEqual(max(link_counts.values()), ENTRIES_PER_ITEM)
        self.assertEqual(min(link_counts.values()), ENTRIES_PER_ITEM)
