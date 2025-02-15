__copyright__ = "Copyright (C) 2020  Red S"
__license__ = "GNU GPLv3"

import tempfile
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

    def test_link_collision(self):
        VERBOSE = False
        START_MONTH = 2
        NUM_DAYS = 5
        NUM_ITEMS_PER_DAY = 1000
        ENTRIES_PER_ITEM = 2
        LEN_ENTRIES = 1 + 2 + (NUM_ITEMS_PER_DAY * NUM_DAYS * ENTRIES_PER_ITEM)

        with tempfile.NamedTemporaryFile('w', delete_on_close=False) as tf:
            directives = ('2014-01-01 open Liabilities:Mastercard\n'
                          '2014-01-01 open Expenses:Insurance:SportsCards\n'
                          '\n')
            tf.write(directives)
            for day in range(1, NUM_DAYS + 1):
                start_date = datetime.date(2014, START_MONTH, day)
                eff_date = datetime.date(2014, START_MONTH + 1, day)
                for i in range(NUM_ITEMS_PER_DAY):
                    card_id = f'A{str(i).zfill(3)}'
                    txn = (
                        f'{start_date.isoformat()} * "Insure card: 1 month"\n'
                        f'  card_id: {card_id}\n'
                        '  Liabilities:Mastercard    -1 USD\n'
                        '  Expenses:Insurance:SportsCards     1 USD\n'
                        f'    effective_date: {eff_date.isoformat()}\n'
                        '\n'
                    )
                    tf.write(txn)
            tf.close()

            entries, _, options_map = loader.load_file(tf.name)
            new_entries, _ = effective_date(entries, options_map, None)

            link_counts = {}
            transaction_counts = 0
            for e in new_entries:
                if isinstance(e, data.Transaction):
                    transaction_counts += 1
                    entry_link = next(iter(e.links)) if e.links else ''
                    if entry_link:
                        if entry_link not in link_counts:
                            link_counts[entry_link] = 0
                        link_counts[entry_link] += 1

                    if VERBOSE:
                        print(e.date,
                              e.postings[0].units,
                              e.meta['card_id'],
                              entry_link)

        self.assertEqual(len(new_entries), LEN_ENTRIES)
        self.assertEqual(
            transaction_counts, (NUM_ITEMS_PER_DAY * NUM_DAYS) * 2)
        self.assertEqual(len(link_counts), NUM_ITEMS_PER_DAY * NUM_DAYS)
        self.assertEqual(max(link_counts.values()), ENTRIES_PER_ITEM)
        self.assertEqual(min(link_counts.values()), ENTRIES_PER_ITEM)
