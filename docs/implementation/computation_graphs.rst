

.. _concepts_graph:

DCOP graph models
=================


When solving a DCOP, The first step performed by pyDCOP is to build a graph
of computations.
This **computation graph**  must not be confused with the constraints graph ;
while they may sometime be similar.
The constraints graph is stricly a graph representation of the
Constraints Optimization Problem (COP) while the **computation graph**
depends on the method (aka algorithm) used to solve this problem.


A computation graph is a graph
where vertices represent **computations**
and edges represent **communication** between these computations.
Computation send and receive messages one with another,
along the edges of the graph.
Computations are defined as the basic unit of work needed when solving a DCOP,
their exact definition depends on the algorithm used.
Most algorithms define computations for the decision variables of the DCOP,
but some algorithm can define computations for constraints as well,
or even groups of variables.

Pydcop defines at the moment 3 kinds of computation graphs:

 * Constraints hyper-graph
 * Pseudo-tree (aka DFS Tree)
 * Factor graph


When solving a DCOP, as each algorithm require a specific type of graph,
pydcop can automatically infer the computation graph model from the algorithm
you're using.


Constraints hyper-graph
-----------------------

This is the most straightforward computation graph :
vertices (i.e. computations) directly maps to the variables of the DCOP
and edges maps to constraints.
As a classical constraint graph can only represents binary variable,
pyDCOP uses an hyper-graph, where hyper-edges can represent n-ary constraints.

The kind of graph is used by algorithms like
:ref:`MGM <implementation_reference_algorithms_mgm>`
:ref:`DSA <implementation_reference_algorithms_dsa>`, etc.

Factor graph
------------

A factor graph is a bipartite graph where...

This kind of graph is used by
:ref:`MaxSum <implementation_reference_algorithms_maxsum>` and
most GDL-based algorithms.



Pseudo-tree
-----------


The only algorithm currently implemented in pyDCOP that uses tha pseudo-tree
computation graph is
:ref:`DPOP <implementation_reference_algorithms_dpop>`



Implementing a new graph model
------------------------------


A module for a computation graph type typically contains

* class(es) representing the nodes of the graph (i.e. the computation),
  extending ComputationNode

* class representing the edges (extending Link)

* a class representing the graph

* a (mandatory) method  to build a computation graph from a Dcop object :

    def build_computation_graph(dcop: DCOP)-> ComputationPseudoTree:
