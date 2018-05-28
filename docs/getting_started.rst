Getting started
===============

This small tutorial will guide you to solve your first DCOP using pyDCOP.

Solving your first DCOP
-----------------------

Once you have installed pyDCOP (and activated the python venv you have
installed it in), create a text file ``graph_coloring.py`` with following
content::

    name: graph coloring
    objective: min

    domains:
      colors:
        values: [R, G]

    variables:
      v1:
        domain: colors
      v2:
        domain: colors
      v3:
        domain: colors

    constraints:
        pref_1:
          type: extensional
          variables: v1
          values:
            -0.1: R
            0.1: G

        pref_2:
          type: extensional
          variables: v2
          values:
            -0.1: G
            0.1: R

        pref_3:
          type: extensional
          variables: v3
          values:
            -0.1: G
            0.1: R

        diff_1_2:
          type: intention
          function: 10 if v1 == v2 else 0

        diff_2_3:
          type: intention
          function: 10 if v3 == v2 else 0

    agents: [a1, a2, a3, a4, a5]

You don't need for the moment to understand everything in this file, it's
enough to know that this represents a graph coloring problem, modelled as a
DCOP with 3 variables (this example is taken from :cite:`Farinelli2008`).

Now you can simply run the following command to
:ref:`solve<pydcop_commands_solve>`
this DCOP with the
:ref:`dpop algorithm<implementation_reference_algorithms_dpop>`::

  pydcop solve -algo dpop  graph_coloring.yaml

This should output a result simular to this::

  {
    "assignment": {
      "v1": "R",
      "v2": "G",
      "v3": "R"
    },
    "cost": -0.1,
    "cycle": 1,
    "msg_count": 49,
    "msg_size": 16,
    "status": "FINISHED",
    "time": 0.006229691000044113,
    "violation": 0
  }

Congratulation, you have solve your first DCOP using pyDCOP !!

Of course you can solve it with any other dcop algorithm implemented by
pyDCOP. Some algorithms have no default termination condition, in this case
you can stop the execution with ``CTRL+C`` or use the ``--timeout`` option::

  pydcop  --timeout 3 solve -algo mgm  graph_coloring.yaml

You may notice that with this command the assignment in the result is not
always the same and not always the result we fuond using dpop.
This is because mgm is a *local search* algorithm, which can be trapped in a
local minima.
On the other hand dpop is a *complete algorithm* and will always return the
optimal assignment (if your problem is small enough to use dpop on it !).


Analysing results
-----------------






Analysing results

* end results
* run-time metrics
* plotting the results