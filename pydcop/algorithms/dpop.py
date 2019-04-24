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

DPOP: Dynamic Programming Optimization Protocol
-----------------------------------------------

Dynamic Programming Optimization Protocol  is an optimal,
inference-based, dcop algorithm implementing a dynamic programming procedure
in a distributed way :cite:`petcu_distributed_2004`.

TODO



"""
from random import choice
from typing import Iterable

from pydcop.infrastructure.computations import Message, VariableComputation, register
from pydcop.dcop.objects import Variable
from pydcop.dcop.relations import (
    NAryMatrixRelation,
    RelationProtocol,
    Constraint,
    get_data_type_max,
    get_data_type_min,
    generate_assignment,
    generate_assignment_as_dict,
    filter_assignment_dict,
    find_arg_optimal,
    DEFAULT_TYPE,
)
from pydcop.algorithms import ALGO_STOP, ALGO_CONTINUE, ComputationDef

GRAPH_TYPE = "pseudotree"


def build_computation(comp_def: ComputationDef):

    parent = None
    children = []
    for l in comp_def.node.links:
        if l.type == "parent" and l.source == comp_def.node.name:
            parent = l.target
        if l.type == "children" and l.source == comp_def.node.name:
            children.append(l.target)

    constraints = [r for r in comp_def.node.constraints]

    computation = DpopAlgo(
        comp_def.node.variable, parent, children, constraints, comp_def=comp_def
    )
    return computation


class DpopMessage(Message):
    def __init__(self, msg_type, content):
        super(DpopMessage, self).__init__(msg_type, content)

    @property
    def size(self):
        # Dpop messages
        # UTIL : multi-dimensional matrices
        # VALUE :

        if self.type == "UTIL":
            # UTIL messages are multi-dimensional matrices
            shape = self.content.shape
            size = 1
            for s in shape:
                size *= s
            return size

        elif self.type == "VALUE":
            # VALUE message are a value assignment for each var in the
            # separator of the sender
            return len(self.content[0]) * 2

    def __str__(self):
        return "DpopMessage({}, {})".format(self._msg_type, self._content)


def join_utils(u1: Constraint, u2: Constraint) -> Constraint:
    """
    Build a new relation by joining the two relations u1 and u2.

    The dimension of the new relation is the union of the dimensions of u1
    and u2. As order is important for most operation, variables for u1 are
    listed first, followed by variables from u2 that where already used by u1
    (in the order in which they appear in u2.dimension).

    For any complete assignment, the value of this new relation is the sum of
    the values from u1 and u2 for the subset of this assignment that apply to
    their respective dimension.

    For more details, see the definition of the join operator in Petcu Phd
    Thesis.

    :param u1: n-ary relation
    :param u2: n-ary relation
    :return: a new relation
    """
    #
    dims = u1.dimensions[:]
    for d2 in u2.dimensions:
        if d2 not in dims:
            dims.append(d2)

    u_j = NAryMatrixRelation(dims, name="joined_utils")
    for ass in generate_assignment_as_dict(dims):

        # FIXME use dict for assignement
        # for Get AND sett value

        u1_ass = filter_assignment_dict(ass, u1.dimensions)
        u2_ass = filter_assignment_dict(ass, u2.dimensions)
        s = u1(**u1_ass) + u2(**u2_ass)
        u_j = u_j.set_value_for_assignment(ass, s)

    return u_j


def projection(a_rel, a_var, mode="max"):
    """

    The project of a relation a_rel along the variable a_var is the
    optimization of the matrix along the axis of this variable.

    The result of `projection(a_rel, a_var)` is also a relation, with one less
    dimension than a_rel (the a_var dimension).
    each possible instantiation of the variable other than a_var,
    the optimal instantiation for a_var is chosen and the corresponding
    utility recorded in projection(a_rel, a_var)

    Also see definition in Petcu 2007

    :param a_rel: the projected relation
    :param a_var: the variable over which to project
    :param mode: 'max (default) for maximization, 'min' for minimization.

    :return: the new relation resulting from the projection
    """

    remaining_vars = a_rel.dimensions.copy()
    remaining_vars.remove(a_var)

    # the new relation resulting from the projection
    proj_rel = NAryMatrixRelation(remaining_vars)

    all_assignments = generate_assignment(remaining_vars)
    for partial_assignment in all_assignments:
        # for each assignment, look for the max value when iterating over
        # aVar domain

        if mode == "min":
            best_val = get_data_type_max(DEFAULT_TYPE)
        else:
            best_val = get_data_type_min(DEFAULT_TYPE)

        for val in a_var.domain:
            full_assignment = _add_var_to_assignment(
                partial_assignment, a_rel.dimensions, a_var, val
            )

            current_val = a_rel.get_value_for_assignment(full_assignment)
            if (mode == "max" and best_val < current_val) or (
                mode == "min" and best_val > current_val
            ):
                best_val = current_val

        proj_rel = proj_rel.set_value_for_assignment(partial_assignment, best_val)

    return proj_rel


def _add_var_to_assignment(partial_assignt, ass_vars, new_var, new_value):
    """
    Add a value for a variable in an assignment.
    The given partial assignment is not modified and a new assignment is
    returned, augmented with the value for the new variable, in the right
    position according to `ass_vars`.

    :param partial_assignt: a partial assignment represented as a list of
    values, the order of the values maps the order of the corresponding
    variables in `ass_vars`
    :param ass_vars: a list of variables corresponding to the list to the
    variables whose values are given by `partial_assignt`, augmented with one
    extra variable 'new_var' whose value is given by `new_value`.
    :param new_var: variable that must be added in the assignment
    :param new_value: value to add in the assignement for the new variable

    """

    if len(partial_assignt) + 1 != len(ass_vars):
        raise ValueError("Length of partial assignment and variables do not " "match.")
    full_assignment = partial_assignt[:]
    for i in range(len(ass_vars)):
        if ass_vars[i] == new_var:
            full_assignment.insert(i, new_value)
    return full_assignment


class DpopAlgo(VariableComputation):
    """
    DPOP: Dynamic Programming Optimization Protocol

    This class represents the DPOP algorithm.

    When running this algorithm, the DFS tree must be already defined and the
    children, parents and pseudo-parents must be known.

    Two kind of messages:
    * UTIL message:
      sent from children to parent, contains a relation (as a
      multi-dimensional matrix) with one dimension for each variable in our
      separator.
    * VALUE messages :
      contains the value of the parent of the node and the values of all
      variables that were present in our UTIl message to our parent (that is
      to say, our separator) .

    """


        In DPOP:
        * A computation represents, and select a value for, one variable.
        * A constraint is managed (i.e. referenced) by a single computation object:
          this means that, when building the computations, each constraint must only be
          passed as argument to a single computation.
        * A constraint must always be managed by the lowest node in the DFS
          tree that the relation depends on (which is especially important for
          non-binary relation). The pseudo-tree building mechanism already
          takes care of this.


        :param variable: The Variable object managed by this algorithm

        :param parent: the parent for this node. A node has at most one parent
        but may have 0-n pseudo-parents. Pseudo parent are not given
        explicitly but can be deduced from the constraints and children
        (if the union of the constraints' scopes contains a variable that is not a
        children, it must necessarily be a pseudo-parent).
        If the variable shares a constraints with its parent (which is the
        most common case), it must be present in the relation arg.

        :param children: the children variables of the variable argument,
        in the DFS tree

        :param constraints: constraints managed by this computation. These
        relations will be used when calculating costs. It must
        depends on the variable arg. Unary relation are also supported.
        Remember that a relation must always be managed by the lowest node in
        the DFS tree that the relation depends on (which is especially
        important for non-binary relation).


        :param mode: type of optimization to perform, 'min' or 'max'

    def __init__(
        self,
        variable: Variable,
        parent: str,
        children: Iterable[str],
        constraints: Iterable[Constraint],
        comp_def=None,
    ):
        """
        """
        super().__init__(variable, comp_def)

        assert comp_def.algo.algo == "dpop"

        self._mode = comp_def.algo.mode
        self._parent = parent
        self._children = children
        self._constraints = constraints

        if hasattr(self._variable, "cost_for_val"):
            costs = []
            for d in self._variable.domain:
                costs.append(self._variable.cost_for_val(d))
            self._joined_utils = NAryMatrixRelation(
                [self._variable], costs, name="joined_utils"
            )

        else:
            self._joined_utils = NAryMatrixRelation([], name="joined_utils")

        self._children_separator = {}

        self._waited_children = []
        if not self.is_leaf:
            # If we are not a leaf, we must wait for the util messages from
            # our children.
            # This must be done in __init__ and not in on_start because we
            # may get an util message from one of our children before
            # running on_start, if this child computation start faster of
            # before us
            self._waited_children = self._children[:]

    def footprint(self):
        return computation_memory(self.computation_def.node)

    @property
    def is_root(self):
        return self._parent is None

    @property
    def is_leaf(self):
        return len(self._children) == 0

    @property
    def is_stable(self):
        return False

    def on_start(self):
        msg_count, msg_size = 0, 0

        if self.is_leaf and not self.is_root:
            # If we are a leaf in the DFS Tree we can immediately compute
            # our util and send it to our parent.
            # Note: as a leaf, our separator is the union of our parents and
            # pseudo-parents
            util = self._compute_utils_msg()
            self.logger.info(
                "Leaf %s init message %s -> %s  : %s",
                self._variable.name,
                self._variable.name,
                self._parent,
                util,
            )
            msg = DpopMessage("UTIL", util)
            self.post_msg(self._parent, msg)
            msg_count += 1
            msg_size += msg.size

        elif self.is_leaf:
            # we are both root and leaf : means we are a isolated variable we
            #  can select our own value alone:
            if self._constraints:
                for r in self._constraints:
                    self._joined_utils = join_utils(self._joined_utils, r)

                values, current_cost = find_arg_optimal(
                    self._variable, self._joined_utils, self._mode
                )

                self.select_value_and_finish(values[0], float(current_cost))
            else:
                # If the variable is not constrained, we can simply take a value at
                # random:
                value = choice(self._variable.domain)
                self.select_value_and_finish(value, 0.0)

    def stop_condition(self):
        # dpop stop condition is easy at it only selects one single value !
        if self.current_value is not None:
            return ALGO_STOP
        else:
            return ALGO_CONTINUE

    def select_value_and_finish(self, value, cost):
        """
        Select a value for this variable.

        DPOP is not iterative, once we have selected our value the algorithm
        is finished for this computation.

        Parameters
        ----------
        value: any (depends on the domain)
            the selected value
        cost: float
            the local cost for this value

        """

        self.value_selection(value, cost)
        self.stop()
        self.finished()
        self.logger.info("Value selected at %s : %s - %s", self.name, value, cost)

    @register("UTIL")
    def _on_util_message(self, variable_name, recv_msg, t):
        self.logger.debug("Util message from %s : %r ", variable_name, recv_msg.content)
        utils = recv_msg.content
        msg_count, msg_size = 0, 0

        # accumulate util messages until we got the UTIL from all our children
        self._joined_utils = join_utils(self._joined_utils, utils)
        try:
            self._waited_children.remove(variable_name)
        except ValueError as e:
            self.logger.error(
                "Unexpected UTIL message from %s on %s : %r ",
                variable_name,
                self.name,
                recv_msg,
            )
            raise e
        # keep a reference of the separator of this children, we need it when
        # computing the value message
        self._children_separator[variable_name] = utils.dimensions

        if len(self._waited_children) == 0:

            if self.is_root:
                # We are the root of the DFS tree and have received all utils
                # we can select our own value and start the VALUE phase.

                # The root obviously has no parent nor pseudo parent, yet it
                # may have unary relations (with it-self!)
                for r in self._constraints:
                    self._joined_utils = join_utils(self._joined_utils, r)

                values, current_cost = find_arg_optimal(
                    self._variable, self._joined_utils, self._mode
                )
                selected_value = values[0]

                self.logger.info(
                    "ROOT: On UNTIL message from %s, send value "
                    "msg to childrens %s ",
                    variable_name,
                    self._children,
                )
                for c in self._children:
                    msg = DpopMessage("VALUE", ([self._variable], [selected_value]))
                    self.post_msg(c, msg)
                    msg_count += 1
                    msg_size += msg.size

                self.select_value_and_finish(selected_value, float(current_cost))
            else:
                # We have received the Utils msg from all our children, we can
                # now compute our own utils relation by joining the accumulated
                # util with the relations with our parent and pseudo_parents.
                util = self._compute_utils_msg()
                msg = DpopMessage("UTIL", util)
                self.logger.info(
                    "On UTIL message from %s, send UTILS msg " "to parent %s ",
                    variable_name,
                    self._children,
                )
                self.post_msg(self._parent, msg)
                msg_count += 1
                msg_size += msg.size

    def _compute_utils_msg(self):

        for r in self._constraints:
            self._joined_utils = join_utils(self._joined_utils, r)

        # use projection to eliminate self out of the message to our parent
        util = projection(self._joined_utils, self._variable, self._mode)

        return util

    @register("VALUE")
    def _on_value_message(self, variable_name, recv_msg, t):
        self.logger.debug(
            '{}: on value message from {} : "{}"'.format(
                self.name, variable_name, recv_msg
            )
        )

        value = recv_msg.content
        msg_count, msg_size = 0, 0

        # Value msg contains the optimal assignment for all variables in our
        # separator : sep_vars, sep_values = value
        value_dict = {k.name: v for k, v in zip(*value)}
        self.logger.debug("Slicing relation on %s", value_dict)

        # as the value msg contains values for all variables in our
        # separator, slicing the util on these variables produces a relation
        # with a single dimension, our own variable.
        rel = self._joined_utils.slice(value_dict)

        self.logger.debug("Relation after slicing %s", rel)

        values, current_cost = find_arg_optimal(self._variable, rel, self._mode)
        selected_value = values[0]

        for c in self._children:
            variables_msg = [self._variable]
            values_msg = [selected_value]

            # own_separator intersection child_separator union
            # self.current_value
            for v in self._children_separator[c]:
                try:
                    values_msg.append(value_dict[v.name])
                    variables_msg.append(v)
                except KeyError:
                    # we want an intersection, we can ignore the variable if
                    # not in value_dict
                    pass
            msg = DpopMessage("VALUE", (variables_msg, values_msg))
            msg_count += 1
            msg_size += msg.size
            self.post_msg(c, msg)

        self.select_value_and_finish(selected_value, float(current_cost))
