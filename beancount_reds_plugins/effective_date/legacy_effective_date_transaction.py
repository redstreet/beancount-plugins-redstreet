"""Beancount plugin to implement per-posting effective dates. See README.md for more."""

import datetime
import random
import string
import time
from beancount.core import data
from beancount_reds_plugins.common import common

DEBUG = 0

# to enable this older transaction-level hacky plugin, edit __plugins__ in effective_date.py

LINK_FORMAT = 'edate-{date}-{random}'


def effective_date_transaction(entries, options_map, config):
    """Effective dates

    Changes this:

    ------(
    2014-02-01 "Estimated taxes for 2013"
      effective_date: 2013-12-31
      Liabilities:Mastercard    -2000 USD
      Expenses:Taxes:Federal  2000 USD
    )------

    into this:
    ------(
    2014-02-01 "Estimated taxes for 2013"
      Liabilities:Mastercard     -2000 USD
      Liabilities:Hold:Taxes:Federal 2000 USD

    2013-12-31 "Estimated taxes for 2013"
      Liabilities:Hold:Taxes:Federal    -2000 USD
      Expenses:Taxes:Federal    2000 USD
    )------


    # Example 2: realizing income earlier (eg: for taxes, accounting, etc.):
    ------(
    2017-01-03 "Paycheck"
      effective_date: 2016-12-31
      Income:Employment    -2000 USD
      Assets:Bank  2000 USD
    )------

    into this:
    ------(
    2016-12-31 "Paycheck"
      Income:Employment    -2000 USD
      Assets:Hold:Income:Employment    2000 USD

    2014-02-01 "Paycheck"
      Assets:Hold:Income:Employment    -2000 USD
      Assets:Bank  2000 USD
    )------


    Args:
      entries: a list of entry instances
      options_map: a dict of options parsed from the file
      config: A configuration string, which is intended to be a Python dict
        mapping match-accounts to a pair of (negative-account, position-account)
        account names.
    Returns:
      A tuple of entries and errors.

    """

    start_time = time.time()
    errors = []

    interesting_entries = []
    filtered_entries = []
    new_accounts = []
    for entry in entries:
        outlist = (interesting_entries
                   if (isinstance(entry, data.Transaction) and
                       'effective_date' in entry.meta and
                       type(entry.meta['effective_date']) is datetime.date)
                   else filtered_entries)
        outlist.append(entry)

    # print("------")
    # for e in interesting_entries:
    #     # print(e)
    #     printer.print_entry(e)
    #     print(type(e.meta.effective_date) is datetime.date)
    #     print("")
    # print("------")

    modcount = 0
    new_entries = []
    for entry in interesting_entries:
        modified_entry_postings = []
        effective_date_entry_postings = []
        found = False
        accts_to_split = {
                'Expenses': {'earlier': 'Liabilities:Hold', 'later': 'Assets:Hold'},
                'Income':   {'earlier': 'Assets:Hold', 'later': 'Liabilities:Hold'},
                }
        for posting in entry.postings:
            if any(acct in posting.account for acct in accts_to_split):
                found_acct = ''
                for acct in accts_to_split:
                    if posting.account.startswith(acct):
                        found_acct = acct
                found = True
                modcount += 1

                holding_account = accts_to_split[found_acct]['earlier']
                if entry.meta['effective_date'] > entry.date:
                    holding_account = accts_to_split[found_acct]['later']
                new_posting = posting._replace(account=posting.account.replace(found_acct, holding_account))
                if new_posting.account not in new_accounts:
                    new_accounts.append(new_posting.account)
                modified_entry_postings += [new_posting]
                effective_date_entry_postings += [posting]

                effective_date_entry_postings += [posting._replace(
                    account=posting.account.replace(found_acct, holding_account),
                    units=-posting.units)]

                if posting.account not in new_accounts:
                    new_accounts.append(posting.account)

            else:
                modified_entry_postings += [posting]

        if found:
            rand_string = ''.join(random.choice(string.ascii_uppercase) for i in range(5))
            link = LINK_FORMAT.format(rand_string)
            # modified_entry = data.entry_replace(entry, postings=modified_entry_postings,
            #                                     links=(entry.links or set()) | set([link]))
            modified_entry = entry._replace(postings=modified_entry_postings,
                                            links=(entry.links or set()) | set([link]))

            effective_date_entry_narration = entry.narration + " (originally: {})".format(str(entry.date))
            # effective_date_entry = data.entry_replace(entry, date=entry.meta['effective_date'],
            #         postings=effective_date_entry_postings,
            #         narration = effective_date_entry_narration,
            #         links=(entry.links or set()) | set([link]))
            new_meta = {'original_date': entry.date}
            effective_date_entry = entry._replace(date=entry.meta['effective_date'],
                                                  meta={**entry.meta, **new_meta},
                                                  postings=effective_date_entry_postings,
                                                  narration=effective_date_entry_narration,
                                                  links=(entry.links or set()) | set([link]))
            new_entries += [modified_entry, effective_date_entry]
        else:
            new_entries += [entry]

    # print("Output results:")
    # for e in new_entries:
    #     printer.print_entry(e)

    if DEBUG:
        elapsed_time = time.time() - start_time
        print("effective_date_transaction [{:.1f}s]: {} entries inserted.".format(elapsed_time, modcount))

    new_open_entries = common.create_open_directives(new_accounts, entries, meta_desc='<effective_date>')
    retval = new_open_entries + new_entries + filtered_entries
    return retval, errors
