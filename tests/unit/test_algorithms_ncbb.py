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
import pytest

from pydcop.algorithms import ComputationDef, AlgorithmDef
from pydcop.algorithms.ncbb import NcbbAlgo
from pydcop.computations_graph.pseudotree import PseudoTreeNode, build_computation_graph
from pydcop.dcop.objects import Variable
from pydcop.dcop.relations import constraint_from_str


@pytest.fixture
def single_variable_pb():
    x1 = Variable("x1", ["R", "B"])
    # build the pseudo-tree for this problem
    g = build_computation_graph(None, constraints=[], variables=[x1])
    return g


@pytest.fixture
def two_variables_pb():
    # a very simple problem with two variables
    x1 = Variable("x1", ["R", "B"])
    x2 = Variable("x2", ["R", "B"])
    diff_x1_x2 = constraint_from_str("c1", "1 if x1 == x2 else 0", [x1, x2])
    # build the pseudo-tree for this problem
    g = build_computation_graph(None, constraints=[diff_x1_x2], variables=[x1, x2])
    return g


@pytest.fixture
def three_variables_pb():
    # a very simple problem with 3 variables
    x1 = Variable("x1", ["R", "B"])
    x2 = Variable("x2", ["R", "B"])
    x3 = Variable("x3", ["R", "B"])
    diff_x1_x2 = constraint_from_str("c1", "1 if x1 == x2 else 0", [x1, x2])
    diff_x1_x3 = constraint_from_str("c2", "1 if x1 == x3 else 0", [x1, x3])
    # build the pseudo-tree for this problem
    g = build_computation_graph(
        None, constraints=[diff_x1_x2, diff_x1_x3], variables=[x1, x2, x3]
    )
    return g


@pytest.fixture
def toy_pb():
    # A toy problem with 5 variables and 5 constraints.
    # The objective here is to have a problem that is simple enough to be solved
    # manually and used in test, but that is representative enough to be meaningful.
    # For example, it includes a loop to make sure we have pseudo parents
    v_a = Variable("A", ["R", "B"])
    v_b = Variable("B", ["R", "B"])
    v_c = Variable("C", ["R", "B"])
    v_d = Variable("D", ["R", "B"])
    v_e = Variable("E", ["R", "B"])
    c1 = constraint_from_str("c1", "1 if A == B else 0", [v_a, v_b])
    c2 = constraint_from_str("c2", "1 if A == C else 0", [v_a, v_c])
    c3 = constraint_from_str("c3", "1 if A == D else 0", [v_a, v_d])
    c4 = constraint_from_str("c4", "1 if B == D else 0", [v_b, v_d])
    c5 = constraint_from_str("c5", "1 if D == E else 0", [v_d, v_e])

    # build the pseudo-tree for this problem
    g = build_computation_graph(
        None, constraints=[c1, c2, c3, c4, c5], variables=[v_a, v_b, v_c, v_d, v_e]
    )
    return g


def get_computation_instance(graph, name):

    # Get the computation node for x1
    comp_node = graph.computation(name)

    # Create the ComputationDef and computation instance
    algo_def = AlgorithmDef.build_with_default_param("ncbb")
    comp_def = ComputationDef(comp_node, algo_def)
    comp = NcbbAlgo(comp_def)
    comp._msg_sender = MagicMock()

    return comp


def test_create_computation_no_links(single_variable_pb):

    comp = get_computation_instance(single_variable_pb, "x1")

    assert comp._mode == "min"
    assert comp.is_leaf
    assert comp.is_root
    assert comp.name == "x1"


def test_create_computation_one_neighbor(two_variables_pb):

    # Get the computation instance for x1
    comp = get_computation_instance(two_variables_pb, "x1")

    assert comp._mode == "min"
    assert comp.is_leaf or comp.is_root
    assert comp.name == "x1"


def test_create_computation_three_variables(three_variables_pb):

    # Check computation instance for x1
    comp = get_computation_instance(three_variables_pb, "x1")

    assert comp._mode == "min"
    assert not comp.is_leaf
    assert comp.is_root
    assert comp.name == "x1"
    assert set(comp._children) == {"x2", "x3"}

    # Check computation instance for x2
    comp = get_computation_instance(three_variables_pb, "x2")

    assert comp._mode == "min"
    assert comp.is_leaf
    assert not comp.is_root
    assert comp.name == "x2"
    assert not comp._children
    assert comp._parent == "x1"
    assert comp._ancestors == ["x1"]


def test_create_computations(toy_pb):
    comp_a = get_computation_instance(toy_pb, "A")

    assert comp_a.is_root
    assert set(comp_a._descendants) == {"D", "B", "C"}

    comp_d = get_computation_instance(toy_pb, "D")
    assert not comp_d.is_root
    assert comp_d._parent == "B"
    assert set(comp_d._ancestors) == {"A", "B"}

