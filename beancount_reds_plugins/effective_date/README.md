Effective dates plugin for Beancount
------------------------------------

Double entry bookkeeping requires each transaction to occur instantaneously in time. In
Beancount, that means each transaction must occur on a single date. However, it is
occasionally useful to view different legs (postings) of a transaction as occurring
across different dates. Booking a payment to a different date from its associated
expenses, is one common use case.

For example, consider:

````
2014-12-15 * "Annual Insurance payment for 2015"
    Liabilities:Credit-Card   100 USD
    Expenses:Insurance
````

Here, the payment was made in Dec 2014 for an expense to be booked to 2015. To reflect
this, one could book it thus:

````
2014-12-15 * "Annual Insurance payment for 2015"
    Liabilities:Credit-Card   100 USD
    Assets:Hold:Insurance

2015-01-01 * "Annual Insurance payment for 2015"
    Assets:Hold:Insurance  -100 USD
    Expenses:Insurance
````

The expense is booked in 2015, while the credit card transaction, in 2014. The
"Assets:Hold:Insurance" account holds the money for the period in between.

This plugin automates the process above. One can simply enter a single transaction with
an `effective_date` metadata field for the posting (not the transaction) that needs to
occur later (or earlier). This keeps the source clean and intuitive:

````
2014-12-15 * "Annual Insurance payment for 2015"
    Liabilities:Credit-Card   100 USD
    Expenses:Insurance
      effective_date: 2015-01-01
````
gets rewritten into:
````
2014-12-15 * "Annual Insurance payment for 2015" ^edate-141215-xlu
    Liabilities:Credit-Card   100 USD
    Assets:Hold:Insurance
      effective_date: 2015-01-01

2015-01-01 * "Annual Insurance payment for 2015" ^edate-141215-xlu
    original_date: 2014-12-15
    Assets:Hold:Insurance  -100 USD
    Expenses:Insurance
````

The plugin allows for postings to occur on multiple different dates. For example:

````
2015-02-01 * "Car insurance: 3 months"
 Liabilities:Mastercard    -600 USD
 Expenses:Car:Insurance     200 USD
   effective_date: 2015-03-01
 Expenses:Car:Insurance     200 USD
   effective_date: 2015-04-01
 Expenses:Car:Insurance     200 USD
   effective_date: 2015-05-01
````


## Features
- an `original_date` metadata is inserted into newly created transactions
- the `effective_date` per-posting metadata is left untouched. This way, the original
  and new entries both have pointers back to each other
- a beancount link links the transactions set. It's human readable: ^edate-141215-9a7
  means the original transaction was on 2014-12-15

See `examples.bc` for more examples, and for how to configure the plugin with your choice
of holding accounts and see `DEFAULT_FORMATS` in `effective_date.py` for how to configure
the link format.
