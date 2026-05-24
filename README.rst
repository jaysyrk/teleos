Teleos
======

**Plain-language logic engine — write rules in English, query from any language.**

Think of it like SQL, but for rules instead of data. Instead of writing
business logic as ``if/else`` code buried in your application, you write it in a
``.teleos`` file that reads like English. Any language — Python, Go, JavaScript,
C++, C#, Java — can load that file and query it.

.. code-block:: text

    fact: alice is admin
    fact: charlie is user
    fact: charlie is banned
    rule: if X is admin then X can access Y
    rule: if X is user and not X is banned then X can access Y

    ask:  alice can access document    → true
    ask:  charlie can access document  → false
    why:  charlie can access document  → Cannot prove: charlie can access document
                                          Nearest rule failed because: charlie is banned

Install
-------

.. code-block:: bash

    pip install py-teleos

Quick start
-----------

.. code-block:: python

    import teleos

    engine = teleos.load("rules.teleos")

    engine.ask("alice can access document")   # True
    engine.why("alice can access document")   # proof string
    engine.all("WHO can access report")       # ["alice", "bob"]
    engine.add_fact("dave is admin")          # add at runtime

CLI
---

.. code-block:: bash

    teleos run  rules.teleos   # run all ask:/why:/all: queries
    teleos test rules.teleos   # run all assert: statements
    teleos repl rules.teleos   # interactive session

.teleos syntax
--------------

.. code-block:: text

    # facts
    fact: alice is admin
    fact: alice has score 95

    # rules — variables are ALL CAPS
    rule: if X is admin then X can access Y
    rule: if X has score S and S >= 90 then X gets distinction

    # negation
    rule: if X is user and not X is banned then X can post

    # import another file
    import: base-rules.teleos

    # queries
    ask: alice can access document     → true / false
    why: alice can access document     → proof explanation
    all: WHO gets distinction          → every matching value

    # assertions (for teleos test)
    assert: alice can access document
    assert not: charlie can access document

Language bindings
-----------------

Teleos includes a Rust core (``teleos-core``) that compiles to a shared library
callable from any language via C FFI.

Bindings are available for Go, JavaScript/TypeScript, C++, C#, and Java.

License
-------

MIT
