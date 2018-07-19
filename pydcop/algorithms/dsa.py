# BSD-3-Clause License
#
# Copyright 2017 Orange
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice,
#    this list of conditions and the following disclaimer.
#
# 2. Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.
#
# 3. Neither the name of the copyright holder nor the names of its contributors
#    may be used to endorse or promote products derived from this software
#    without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.


"""
DSA : Distributed Stochastic algorithm
--------------------------------------

Distributed Stochastic Algorithms :cite:`zhang_distributed_2005` is a
synchronous, stochastic, local search DCOP algorithm.
  
Algorithm Parameters
^^^^^^^^^^^^^^^^^^^^

**variant**
  'A', 'B' or 'C' ; the variant of the algorithm,
  as defined in :cite:`zhang_distributed_2005` . Defaults to B

**probability**
  probability of changing a value. Defaults to 0.7


Example
^^^^^^^

::

    dcop.py -t 3 solve -a dsa -p variant:C probability:0.3 \
     -d adhoc graph_coloring_csp.yaml
    {
      "assignment": {
        "v1": "G",
        "v2": "R",
        "v3": "G"
      },
      "cost": 0,
      "duration": 1.9972785034179688,
      "status": "TIMEOUT"
    }



"""

import logging
import operator
import random

import functools
from typing import Any, Tuple

from pydcop.algorithms import find_arg_optimal, filter_assignment_dict, \
    generate_assignment_as_dict, ComputationDef, AlgoParameterDef, \
    assignment_cost
from pydcop.infrastructure.computations import MessagePassingComputation, \
    Message, VariableComputation, DcopComputation, register

from pydcop.computations_graph.constraints_hypergraph import \
    VariableComputationNode
from pydcop.dcop.relations import find_optimum


HEADER_SIZE = 100
UNIT_SIZE = 5

# Type of computations graph that must be used with dsa
GRAPH_TYPE = 'constraints_hypergraph'


def algo_name() -> str:
    """

    Returns
    -------
    The name of the algorithm implemented by this module : 'dsa'
    """
    return __name__.split('.')[-1]


def build_computation(comp_def: ComputationDef) -> DcopComputation:
    """Build a DSA computation

    Parameters
    ----------
    comp_def: a ComputationDef object
        the definition of the DSA computation

    Returns
    -------
    MessagePassingComputation
        a message passing computation that implements the DSA algorithm for
        one variable.

    """
    return DsaComputation(comp_def.node.variable,
                          comp_def.node.constraints,
                          mode=comp_def.algo.mode,
                          **comp_def.algo.params,
                          comp_def= comp_def)


def computation_memory(computation: VariableComputationNode) -> float :
    """Return the memory footprint of a DSA computation.

    Notes
    -----
    With DSA, a computation must only remember the current value for each
    of it's neighbors.

    Parameters
    ----------
    computation: VariableComputationNode
        a computation in the hyper-graph computation graph
    links: iterable of links
        links for this computation node. links maps to constraints in the
        computation graph and can be hyper-edges (when the arity of the
        constraint is > 2)

    Returns
    -------
    float:
        the memory footprint of the computation.

    """
    neighbors = set((n for l in computation.links for n in l.nodes
                     if n not in computation.name))
    return len(neighbors) * UNIT_SIZE


def communication_load(src: VariableComputationNode, target: str) -> float:
    """Return the communication load between two variables.

    Notes
    -----
    The only message in DSA is the 'value' messages, which simply contains
    the current value.

    Parameters
    ----------
    src: VariableComputationNode
        The ComputationNode for the source variable.
    target: str
        the name of the other variable `src` is sending messages to


    Returns
    -------
    float
        The size of messages sent from the src variable to the target variable.
    """
    return  UNIT_SIZE + HEADER_SIZE


algo_params = [
    AlgoParameterDef('probability', 'float', None, 0.7),
    AlgoParameterDef('variant', 'str', ['A', 'B', 'C'], 'B'),
    AlgoParameterDef('stop_cycle', 'int', None, None),
]


class DsaMessage(Message):
    def __init__(self, value):
        super().__init__('dsa_value', None)
        self._value = value

    @property
    def value(self):
        return self._value

    @property
    def size(self):
        return 1

    def __str__(self):
        return 'DsaMessage({})'.format(self.value)

    def __repr__(self):
        return 'DsaMessage({})'.format(self.value)

    def __eq__(self, other):
        if type(other) != DsaMessage:
            return False
        if self.value == other.value:
            return True
        return False


class DsaComputation(VariableComputation):
    """
    DSAComputation implements several variants of the DSA algorithm.

    See. the following article for a complete description of DSA:
    'Distributed stochastic search and distributed breakout: properties,
    comparison and applications to constraint optimization problems in sensor
    networks', Zhang Weixiong & al, 2005


    Parameters
    ----------
    variable: Variable
        an instance of Variable, whose this computation is responsible for
    constraints: an iterable of constraints objects
        The constraints the variables depends on
    variant: str
        The DSA variant to use (A, B or C)
    probability: float
        The probability threshold for changing value. Used differently
        depending on the variant of DSA. See (Zhang, 2005) for details
    stop_cycle: int
        the number of cycle after which the computation must stop. If not
        given, the computation does not stop automatically.
    mode: str
        'min' or 'max'
    logger: a logger
    comp_def: ComputationDef
        the definition of the computation, given as a ComputationDef instance.

    """
    def __init__(self, variable, constraints, variant='B', probability=0.7,
                 stop_cycle=None,
                 mode='min', comp_def=None):
        super().__init__(variable, comp_def)

        self.probability = probability
        self.variant = variant
        self.stop_cycle = stop_cycle
        self.mode = mode
        self.constraints = list(constraints)
        self.__optimum_dict__ = {c.name: find_optimum(c, self.mode) for c in
                                 self.constraints}

        # some constraints might be unary, and our variable can have several
        # constraints involving the same variable
        self._neighbors = set([v.name for c in constraints
                               for v in c.dimensions if v != variable])
        self._neighbors_values = {}

        # Due to asynchronicity, at a turn n an agent can receive the value
        # of a neighbor for the turn n and the turn (n+1) before receiving
        # all neighbors' value for turn n. We need not to erase the value of
        # turn n
        self._postponed_messages = list()

    def footprint(self):
        return computation_memory(self.computation_def.node)

    def on_start(self):
        # randomly select a value
        self.random_value_selection()
        self.logger.debug('DSA starts : randomly select value %s',
                          self.current_value)
        # send a value msg to all neighbors
        self._send_value()

        # as everything is asynchronous, we might have received our
        # neighbors values even before starting this algorithm. In this case
        # we must treat them now.
        self._on_neighbors_values()

    @register('dsa_value')
    def _on_value_msg(self, variable_name, recv_msg, t):
        if variable_name not in self._neighbors_values:
            self._neighbors_values[variable_name] = recv_msg.value
        else:  # The message is too early
            self.logger.debug('%s received the value of %s for the next turn. '
                              'Processing of this message is postponed until '
                              'next turn', self.name, variable_name)
            self._postponed_messages.append((variable_name, recv_msg.value))

        self.logger.debug('%s received value %s from %s', self.variable.name,
                          recv_msg.value, variable_name)
        self._on_neighbors_values()

    def evaluate_cycle(self):

        if len(self.current_cycle) < len(self.neighbors):
            return

        self.logger.debug('Full neighbors assignment for cycle %s : %s ',
                          self.cycle_count, self.current_cycle)

        self.current_cycle[self.variable.name] = self.current_value
        arg_min, min_cost = self.compute_best_value()
        current_cost = assignment_cost(self.current_cycle, self.constraints)
        delta = current_cost - min_cost

        if  (self.mode == 'min' and delta > 0) or \
                    (self.mode == 'max' and delta < 0):
            pass
    def _on_neighbors_values(self):
        # if we have a value for all neighbors, compute our best value for
        # conflict reduction
        # We also check that we have already selected an initial value,
        # otherwise it makes no sense to compute our gain.
        if len(self._neighbors_values) == len(self.neighbors) and \
                        self.current_value is not None:
            self.logger.debug('%s received values from all neighbors : %s',
                              self.variable.name,
                              self._neighbors_values)
            bests, sum_cost = self._compute_best_value()

            # Compute the current cost before computing the gain
            current_asgt = self._neighbors_values.copy()
            current_asgt[self.name] = self.current_value
            self.__cost__ = self._compute_cost(current_asgt)

            delta = self.current_cost - sum_cost
            self.logger.debug(
                '%s best value : %s with cost %s - improvement %s ',
                self.variable.name,
                bests, sum_cost, delta)

            if (self.mode == 'min' and delta > 0) or \
                    (self.mode == 'max' and delta < 0):
                if self.probability > random.random():
                    self.value_selection(random.choice(bests), sum_cost)
                    self.logger.info('%s select new value %s with cost %s',
                                     self.variable.name, self.current_value,
                                     self.current_cost)
                else:
                    self.logger.info('%s has potential improvement but '
                                     'not value change', self.name)
            elif delta == 0 and self.exists_violated_constraint() and\
                    self.variant in ['B', 'C']:
                # DSA-B and DSA-C may still change their value when no
                # improvement is possible, if there are still conflicts.
                # This helps escaping local optima
                if len(bests) > 1 and self.probability > random.random():
                    bests.remove(self.current_value)
                    self.value_selection(random.choice(bests), sum_cost)

                    self.logger.info('%s select new value %s with same cost  '
                                     '%s (DSA B/C)', self.variable.name,
                                     self.current_value, sum_cost)
            elif delta == 0 and self.variant == 'C':
                # DSA-C may change the value event with no conflict nor
                # improvement.
                if len(bests) > 1 and self.probability > random.random():
                    bests.remove(self.current_value)
                    self.value_selection(random.choice(bests), sum_cost)

                    self.logger.info('%s select new value %s with no conflict '
                                     'and same cost  %s (DSA-C)',
                                     self.variable.name, self.current_value,
                                     sum_cost)
            else:
                self.logger.debug('%s has no possible improvement : '
                                  'do not change value', self.name)
            self._neighbors_values.clear()
            self._send_value()

            # Begining of next turn: process the postponed messages
            while self._postponed_messages:
                neighbor, value = self._postponed_messages.pop()
                self.logger.debug(
                    '%s process postponed received value %s from %s',
                    self.name, value, neighbor)
                self._neighbors_values[neighbor] = value
            # In case every messages have been postponed, even it shouldn't
            # be possible. And for debugging messages
            # self._on_neighbors_values()

        else:
            # Still waiting for other neighbors
            self.logger.debug(
                '%s waiting for values from other neighbors (got %s)',
                self.name, [n for n in self._neighbors_values])

    def _compute_best_value(self):

        reduced_cs = []
        concerned_vars = set()
        for c in self.constraints:
            asgt = filter_assignment_dict(self._neighbors_values, c.dimensions)
            reduced_cs.append(c.slice(asgt))
            concerned_vars.update(c.dimensions)

        var_val, rel_val = find_arg_optimal(self.variable,
                                            lambda x: functools.reduce(
                                                operator.add,
                                                [f(x) for f in reduced_cs]),
                                            self.mode
                                            )
        for var in concerned_vars:
            if hasattr(var, 'cost_for_val'):
                if var.name == self.name:
                    rel_val += var.cost_for_val(self.current_value)
                else:
                    rel_val += var.cost_for_val(
                        self._neighbors_values[var.name])

        return var_val, rel_val


    def compute_best_value(self) -> Tuple[Any, float]:

        arg_min, min_cost = None, float('inf')
        for value in self.variable.domain:
            self.current_cycle[self.variable.name] = value
            cost = assignment_cost(self.current_cycle, self.constraints)
            if cost < min_cost:
                min_cost, arg_min = cost, value

        # FIXME : take into account variable cost
        return arg_min, min_cost



    def _send_value(self):
        # We consider sending the value as the start of a new cycle in DSA:
        self.new_cycle()
        if self.stop_cycle and self.cycle_count >= self.stop_cycle:
            self.finished()
            return

        for n in self.neighbors:
            msg = DsaMessage(self.current_value)
            self.post_msg(n, msg)

    def _compute_cost(self, assignment, constraints=None):
        constraints = self.constraints if constraints is None else constraints
        # Cost for constraints:
        cost = functools.reduce(operator.add, [f(**filter_assignment_dict(
            assignment, f.dimensions)) for f in constraints], 0)
        # Cost for variable, if any:
        concerned_vars = set(v for c in constraints for v in c.dimensions)
        for v in concerned_vars:
            if hasattr(v, 'cost_for_val'):
                cost += v.cost_for_val(assignment[v.name])

        return cost

    def _compute_boundary(self, constraints):
        constraints_list = list()
        optimum = 0
        for c in constraints:
            variables = [v for v in c.dimensions if v != self._variable]
            boundary = None
            for asgt in generate_assignment_as_dict(variables):
                rel = c.slice(filter_assignment_dict(asgt, c.dimensions))
                for val in self._variable.domain:
                    rel_val = rel(val)
                    if boundary is None:
                        boundary = rel_val
                    elif self.mode == 'max' and rel_val > boundary:
                        boundary = rel_val
                    elif self.mode == 'min' and rel_val < boundary:
                        boundary = rel_val
            constraints_list.append(c)
            optimum += boundary
        return constraints_list, optimum

    def exists_violated_constraint(self) -> bool:
        """
        Tells if there is a violated soft constraint regarding the current
        assignment
        :return: a boolean
        """
        for c in self.constraints:
            asgt = self._neighbors_values.copy()
            asgt[self.name] = self.current_value
            const = c(**filter_assignment_dict(asgt, c.dimensions))
            if const != self.__optimum_dict__[c.name]:
                return True
        return False
