"""Beancount plugin to implement per-posting effective dates. See README.md for more."""

from ast import literal_eval
import copy
import datetime
import random
import string
import sys
import time
from beancount.core import data
from beancount_reds_plugins.common import common

DEBUG = 0

__plugins__ = ['effective_date']
# to enable the older transaction-level hacky plugin, now renamed to effective_date_transaction
# __plugins__ = ['effective_date', 'effective_date_transaction']

DEFAULT_FORMATS = {
    'LINK_FORMAT': 'edate-{date}-{rand}',
    'DATE_FORMAT': '%Y%m%d',    # %y to omit century
    'RANDOM_LEN': 3,
}
HEX_BASE = 16


def has_valid_effective_date(posting):
    return posting.meta is not None and \
             'effective_date' in posting.meta and \
             type(posting.meta['effective_date']) is datetime.date


def has_posting_with_valid_effective_date(entry):
    for posting in entry.postings:
        if has_valid_effective_date(posting):
            return True
    return False


def create_new_effective_date_entry(entry, date, hold_posting, original_posting):
    def cleaned(p):
        clean_meta = copy.deepcopy(p.meta)
        clean_meta.pop('effective_date', None)
        return p._replace(meta=clean_meta)

    new_meta = {'original_date': entry.date}
    effective_date_entry = entry._replace(date=date, meta={**entry.meta, **new_meta},
                                          postings=[cleaned(hold_posting), cleaned(original_posting)])
    return effective_date_entry


def rand_counter(n=10, repr=int):
    values = [x for x in range(n)]
    random.shuffle(values)
    i = 0

    while i < n:
        value = values[i]
        i += 1
        yield repr(value)


def build_config(config):
    # Config may contain more than just accounts, but the non-account
    # configurations are not valid account names.
    holding_accts = {}
    formats = {}
    if config:
        holding_accts = literal_eval(config)
        formats = {k: holding_accts.pop(k, None) or v
                   for k, v in DEFAULT_FORMATS.items()}

    if not holding_accts:
        if DEBUG:
            print("effective_date: Using default config", file=sys.stderr)
        holding_accts = {
                'Expenses': {'earlier': 'Liabilities:Hold:Expenses', 'later': 'Assets:Hold:Expenses'},
                'Income':   {'earlier': 'Assets:Hold:Income', 'later': 'Liabilities:Hold:Income'},
                }
        formats = DEFAULT_FORMATS | formats

    def hexformat(i):
        return hex(i)[2:].zfill(formats['RANDOM_LEN'])

    return holding_accts, formats, hexformat


def make_link(entry_date, formats, hexformat, rand_gens):
    date_str = entry_date.strftime(formats['DATE_FORMAT'])
    # Fail collision test: rand_str = ''.join(random.choice(string.ascii_uppercase) for i in range(3))
    if entry_date not in rand_gens:
        rand_gens[entry_date] = rand_counter(
            HEX_BASE**formats['RANDOM_LEN'], hexformat)
    rand_str = next(rand_gens[entry_date])

    link = formats['LINK_FORMAT'].format(date=date_str, rand=rand_str)
    return link


def effective_date(entries, options_map, config):
    """Effective dates

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
    holding_accts, formats, hexformat = build_config(config)
    rand_gens = {}
    interesting_entries = []
    filtered_entries = []
    new_accounts = set()
    for entry in entries:
        if isinstance(entry, data.Transaction) and has_posting_with_valid_effective_date(entry):
            interesting_entries.append(entry)
        else:
            filtered_entries.append(entry)

    # if DEBUG:
    #     print("effective_date: ------")
    #     for e in interesting_entries:
    #         printer.print_entry(e)
    #     print("effective_date: ------")

    # add a link to each effective date entry. this gets copied over to the newly created effective date
    # entries, and thus links each set of effective date entries
    interesting_entries_linked = []
    for entry in interesting_entries:
        link = make_link(entry.date, formats, hexformat, rand_gens)
        new_entry = entry._replace(links=(entry.links or set()) | set([link]))
        interesting_entries_linked.append(new_entry)

    new_entries = []
    for entry in interesting_entries_linked:
        modified_entry_postings = []
        for posting in entry.postings:
            if not has_valid_effective_date(posting):
                modified_entry_postings += [posting]
            else:
                found_acct = ''
                for acct in holding_accts:
                    if posting.account.startswith(acct):
                        found_acct = acct

                # find earlier or later (is this necessary?)
                holding_account = holding_accts[found_acct]['earlier']
                if posting.meta['effective_date'] > entry.date:
                    holding_account = holding_accts[found_acct]['later']

                # Replace posting in original entry with holding account
                new_posting = posting._replace(account=posting.account.replace(found_acct, holding_account))
                new_accounts.add(new_posting.account)
                modified_entry_postings.append(new_posting)

                # Create new entry at effective_date
                hold_posting = new_posting._replace(units=-posting.units)
                new_entry = create_new_effective_date_entry(entry, posting.meta['effective_date'],
                                                            hold_posting, posting)
                new_entries.append(new_entry)
        modified_entry = entry._replace(postings=modified_entry_postings)
        new_entries.append(modified_entry)

    # if DEBUG:
    #     print("Output results:")
    #     for e in new_entries:
    #         printer.print_entry(e)

    if DEBUG:
        elapsed_time = time.time() - start_time
        print("effective_date [{:.1f}s]: {} entries inserted.".format(elapsed_time, len(new_entries)))

    new_open_entries = common.create_open_directives(new_accounts, entries, meta_desc='<effective_date>')
    retval = new_open_entries + new_entries + filtered_entries
    return retval, errors


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
            link = DEFAULT_FORMATS['LINK_FORMAT'].format(rand_string)
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

# TODO
# -----------------------------------------------------------------------------------------------------------
# Bug:
# below will fail because expense account was opened too late in the source:
# 2014-01-01 open Expenses:Taxes:Federal
#
# 2014-02-01 * "Estimated taxes for 2013"
# Liabilities:Mastercard    -2000 USD
# Expenses:Taxes:Federal  2000 USD
#   effective_date: 2013-12-31
