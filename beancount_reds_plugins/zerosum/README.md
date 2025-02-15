## Description
Beancount [1] plugin to find matching pairs of postings that sum up to zero. Useful in
de-duplication, and tracking things such as reimbursements, rebates, etc.

## Motivation
Transfers of money between accounts is common. Consider an example where money is
transferred between a bank and an investment account. Once transactions are downloaded
from both institutions, they would look like this:

```
2005-01-01 * "Outgoing transfer to ZTrade"
  Assets:Banks:Bank_of_Ameriplus  -20 USD
  Assets:Investments:ZTrade        20 USD

2005-01-03 * "Incoming transfer from Bank"
  Assets:Investments:ZTrade        20 USD
  Assets:Banks:Bank_of_Ameriplus  -20 USD
```


This presents a problem: one of these is a duplicate that must be identified and
commented out. Doing so presents a secondary problem: since the transfer was realized on
different days in each institution, using any single date would not be quite correct.

Instead, the following transactions better represent reality:

```
2005-01-01 * "Outgoing transfer to ZTrade"
  Assets:Banks:Bank_of_Ameriplus  -20 USD
  ZeroSumAccount:Transfers

2005-01-03 * "Incoming transfer from Bank"
  Assets:Investments:ZTrade        20 USD
  ZeroSumAccount:Transfers
```


The "ZeroSumAccount:Transfers" account will temporarily hold the money but will
eventually sum up to zero (hence the name). The advantages are:

- the money is in neither physical account while it is being transferred, but yet is
still yours, which is represented correctly above.

- De-duplication is rendered unnecessary. Transactions from both institutions co-exist
correctly.
    
- Import/conversion (from say, a bank .csv or .ofx) is easier, because your import
scripts don't have to figure out where a transfer goes, and can simply assign transfers
to  ZeroSumAccount:Transfers

- Errors can be identified easily since the ZeroSumAccount:Transfers will sum to a
non-zero value.

I've found such "zerosum" accounts to be very useful in several other scenarios as well.
For example:

- reimbursements: I book these to a reimbursement account at the time of purchase, and
  at the time the reimbursement arrives. Assets:Reimbursement:Workplace account tracks
  reimbursements. When the zerosum plugin is used, it moves all matches to a different
  account, and so, only the outstanding reimbursements (the ones not yet paid) are left
  behind in Assets:Reimbursements:Workplace

- mail in rebates: the Assets:Rebates account tracks all mail-in rebates. When the
  zerosum plugin is used, it moves all matches to a different account, and so, only the
  outstanding rebates are in Assets:Rebates

## What this plugin does
This plugin identifies sets of postings in the specified ZeroSum accounts that sum up to
zero, and moves them to a specified target account. This target account will always sum
up to zero and needs no further attention. The postings remaining in the original
ZeroSum accounts were the ones that could not be matched, and need further attention
from the user.

The following examples will be matched and moved by this plugin:

#### Example 1:
```
    Input:
        2005-01-01 Transfer
          Assets:Bank_of_Ameriplus  -20 USD
          ZeroSumAccount:Transfers


        2005-01-03 Transfer
          Assets:TB_Trading  20 USD
          ZeroSumAccount:Transfers

    Output:
        2005-01-01 Transfer
          Assets:Bank_of_Ameriplus  -20 USD
          ZeroSumAccount-Matched:Transfers


        2005-01-03 Transfer
          Assets:TB_Trading  20 USD
          ZeroSumAccount-Matched:Transfers
```


#### Example 2:
````    
    2005-01-01 Transfer
      Assets:Bank_of_Ameriplus  -20 USD
      ZeroSumAccount:Transfers   10 USD
      ZeroSumAccount:Transfers   10 USD


    2005-01-03 Transfer
      Assets:TB_Trading_A  10 USD
      ZeroSumAccount:Transfers


    2005-01-04 Transfer
      Assets:TB_Trading_B  10 USD
      ZeroSumAccount:Transfers
````    


The following examples will NOT be matched:

#### Example A:
````    
    2005-01-01 Transfer
      Assets:Bank_of_Ameriplus  -20 USD
      ZeroSumAccount:Transfers   10 USD
      ZeroSumAccount:Transfers   10 USD


    2005-01-03 Transfer
      Assets:TB_Trading  20 USD
      ZeroSumAccount:Transfers
````    


#### Example B:
````    
    2005-01-01 Transfer
      Assets:Bank_of_Ameriplus  -20 USD
      ZeroSumAccount:Transfers


    2005-01-03 Transfer
      Assets:TB_Trading_A  10 USD
      ZeroSumAccount:Transfers


    2005-01-03 Transfer
      Assets:TB_Trading_B  10 USD
      ZeroSumAccount:Transfers
````    


The plugin also automatically adds "Open" directives for the target accounts to which
matched transactions are moved.

## Invoking the plugin
First, an example:

```
# After installation via pip:
    plugin "beancount_reds_plugins.zerosum.zerosum" "{
     'zerosum_accounts' : {
       'Assets:Zero-Sum-Accounts:Bank-Account-Transfers' : ('Assets:ZSA-Matched:Bank-Account-Transfers', 30),
       'Assets:Zero-Sum-Accounts:Credit-Card-Payments'   : ('Assets:ZSA-Matched:Credit-Card-Payments'  ,  6),
       'Assets:Zero-Sum-Accounts:Temporary'              : ('Assets:ZSA-Matched:Temporary'             , 90),
      }
    }"
```

The argument is a dictionary where the keys are the accounts on which the plugin should
operate. The values are (target_account, date_range), where the target_account is the
account to which the plugin should move matched postings, and the date_range is the
range over which to check for matches for that account.

The optional 'account_name_replace' can be used to specify a substring replacement in
the source accounts, making the config below equivalent to the config above:

```
    plugin "beancount_reds_plugins.zerosum.zerosum" "{
     'zerosum_accounts' : {
       'Assets:Zero-Sum-Accounts:Bank-Account-Transfers' : ('', 30),
       'Assets:Zero-Sum-Accounts:Credit-Card-Payments'   : ('',  6),
       'Assets:Zero-Sum-Accounts:Temporary'              : ('', 90),
     },
     'account_name_replace' : ('Zero-Sum-Accounts', 'ZSA-Matched')
    }"
```

## Features

Optionally, the plugin can add transaction level or posting level links, tying together
related transactions or postings. Transaction level links use Beancount's linking
feature. Beancount does not support posting level links, and thus, these use metadata.
Both use the same sequential link ids.

To use these, see the following options documented at the top of `zerosum.py`:
- 'match_metadata'
- 'match_metadata_name'
- 'link_transactions'
- 'link_prefix'

## Example
See the included zerosum-example.beancount as the minimum beancount file for this example.

bean-query output:

```
$ bean-query zerosum-example.beancount
Zerosum: 2/4 postings matched. 0 multiple matches. 2 new accounts added.
Input file: "Beancount"
Ready with 13 directives (14 postings in 6 transactions).

beancount> balances
                account                  sum_posi
---------------------------------------- --------
Assets:Bank:Checking                      125 USD
Assets:Rebates                             50 USD
Assets:Reimbursements-Received:Workplace
Assets:Reimbursements:Workplace             7 USD
Assets:Zerosum-Matched:Rebates
Liabilities:Credit-Card                  -582 USD
Expenses:Electronics                      400 USD
beancount>
```


As you can see, the received reimbursement got moved into the specified target
account (Assets:Reimbursements-Received:Workplace), while the one not received
(for $7) remains in its original account. Same for the rebate. Target accounts
always sum up to zero.


## References

[1] Beancount: https://bitbucket.org/blais/beancount/, http://furius.ca/beancount/

[2] https://groups.google.com/d/msg/beancount/z9sPboW4U3c/UfJbIVzwmpMJ

[3] https://groups.google.com/forum/#!topic/beancount/MU6KozsmqGQ

