"""Classifies Capital Gains accounts into Short and Long

Invoke it in your beancount source this way:
plugin "long_short" "{
   'generic_account':     'Income:Capital-Gains',
   'short_account_rep':   ['Capital-Gains', 'Capital-Gains:Short'], # Replaces the former string with the latter
   'long_account_rep':    ['Capital-Gains', 'Capital-Gains:Long'],
   }"


"""

import time

from beancount.core import data
from beancount.core import getters
from ast import literal_eval

DEBUG = 1

__plugins__ = ('long_short',)


def pretty_print_transaction(t):
    print(t.date)
    for p in t.postings:
        print("            ", p.account, p.position)
    print("")


def long_short(entries, options_map, config):
    """Replace :Capital-Gains: in transactions with :Capital-Gains:Short: and/or :Capital-Gains:Long:
    """

    start_time = time.time()
    rewrite_count_short = rewrite_count_long = 0
    errors = []

    config_obj = literal_eval(config)
    generic_account = config_obj.pop('generic_account', {})
    # Turn into regex
    short_account_replacement = config_obj.pop('short_account_rep', {})
    long_account_replacement = config_obj.pop('long_account_rep', {})

    short_account = generic_account.replace(short_account_replacement[0], short_account_replacement[1])
    long_account  = generic_account.replace(long_account_replacement[0],  long_account_replacement[1])


    for entry in entries:

        # identify reduction transactions
        # determine long vs short for each lot
        # replace cap gains account with above

        def isreduction(entry):
            return any(posting.cost and posting.units.number < 0 for posting in entry.postings)

        def contains_shortlong_postings(entry):
            return any(posting.account in [short_account, long_account] for posting in entry.postings)

        def contains_generic(entry):
            return any(posting.account == generic_account for posting in entry.postings)

        def is_interesting_entry(entry):
            return isreduction(entry) and contains_generic(entry) and not contains_shortlong_postings(entry)

        def reductions(entry):
            return [posting for posting in entry.postings if (posting.cost and posting.units.number < 0)]

        def sale_type(p, entry_date):
            length_held = entry_date - p.cost.date
            gain = (p.price.number - p.cost.number) * abs(p.units.number)
            # TODO: account for leap years
            # check https://thispointer.com/python-get-difference-between-two-dates-in-years/
            return length_held.days <= 365, gain

        if isinstance(entry, data.Transaction) and is_interesting_entry(entry):
            sale_types = [sale_type(p, entry.date) for p in reductions(entry)]
            short_gains = sum(s[1] for s in sale_types if s[0] is True)
            long_gains = sum(s[1] for s in sale_types) - short_gains

            # remove generic gains postings
            orig_gains_postings = [p for p in entry.postings if p.account == generic_account]
            orig_p = orig_gains_postings[0]
            orig_sum = sum(p.units.number for p in orig_gains_postings)
            assert orig_sum == -1 * (short_gains + long_gains)
            for p in orig_gains_postings:
                entry.postings.remove(p)

            # create and add upto two new postings
            if short_gains:
                new_units = orig_p.units._replace(number = short_gains * -1)
                new_posting = orig_p._replace(account=short_account, units=new_units)
                rewrite_count_short += 1
                entry.postings.append(new_posting)

            if long_gains:
                new_units = orig_p.units._replace(number = long_gains * -1)
                new_posting = orig_p._replace(account=long_account, units=new_units)
                rewrite_count_long += 1
                entry.postings.append(new_posting)

            # TODO: catch cases where this doesn't work
            # - selling in a different currency?

    # create open entries
    new_accounts = []
    if rewrite_count_short:
        new_accounts.append(short_account)
    if rewrite_count_long:
        new_accounts.append(long_account)
    new_open_entries = create_open_directives(new_accounts, entries)
    if DEBUG:
        elapsed_time = time.time() - start_time
        print("Capital gains classifier [{:.1f}s]: {} short, {} long postings added.".format(elapsed_time,
            rewrite_count_short, rewrite_count_long))
    return(new_open_entries + entries, errors)


def create_open_directives(new_accounts, entries):
    if not entries:
        return []
    meta = data.new_metadata('<zerosum>', 0)
    # Ensure that the accounts we're going to use to book the postings exist, by
    # creating open entries for those that we generated that weren't already
    # existing accounts.
    earliest_date = entries[0].date
    open_entries = getters.get_account_open_close(entries)
    new_open_entries = []
    for account_ in sorted(new_accounts):
        if account_ not in open_entries:
            meta = data.new_metadata(meta['filename'], 0)
            open_entry = data.Open(meta, earliest_date, account_, None, None)
            new_open_entries.append(open_entry)
    return(new_open_entries)
