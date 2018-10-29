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
.. _pydcop_commands_generate_agents:

pydcop generate agents
======================

generate a set of agents

Examples
========

Simply generate 10 agents with a 100 capacity. Note that we do not need to pass a DCOP
file in that case::

  pydcop generate agents --count 10 --capacity 100

Generate agents and hosting costs


"""
import logging
import re
from typing import List, Tuple, Dict

from pydcop.dcop.objects import AgentDef, create_agents, Variable
from pydcop.dcop.yamldcop import yaml_agents, load_dcop_from_file

logger = logging.getLogger("pydcop.cli.generate")


def init_cli_parser(parent_parser):
    parser = parent_parser.add_parser("agents", help="Generate a set of agents")
    parser.set_defaults(func=generate)

    parser.add_argument(
        "--mode",
        type=str,
        required=True,
        choices=["variables", "count"],
        help="Agents generation mode. When 'variables' is used, one agent "
        "is generated for each agent and the '--dcop_files' option is required. "
        "When using 'count', '--count' is required",
    )

    parser.add_argument("--dcop_files", type=str, nargs="+", help="dcop file(s)")

    parser.add_argument("--count", type=int, help="Number of agents")

    parser.add_argument(
        "--agent_prefix", type=str, default="a", help="Prefix when creating agent"
    )

    parser.add_argument(
        "--capacity", type=int, required=True, help="Capacity of agents"
    )

    parser.add_argument(
        "--hosting",
        choices=["None", "name_mapping"],
        required=False,
        default="None",
        help="Hosting cost generation method.",
    )
    parser.add_argument(
        "--hosting_default",
        type=int,
        required=False,
        help="Default hosting cost, mandatory when using --hosting",
    )

    parser.add_argument(
        "--routes",
        choices=["None", "uniform"],
        required=False,
        default="None",
        help="Route cost generation method.",
    )
    parser.add_argument(
        "--routes_default",
        type=int,
        required=False,
        help="Default routes cost, mandatory when using --routes",
    )

    # TODO: non-uniform route costs, derived from graph
    #

def generate(args):
    agents_name = generate_agents_names(args.count, args.agent_prefix)

    if args.hosting and args.hosting != "None":
        pass

    hosting_costs = {}
    if args.hosting and args.hosting != "None":
        if not args.dcop_files:
            raise ValueError(
                f"Missing dcop file when using {args.hosting} hosting cost generation"
            )
        logger.info("loading dcop from {}".format(args.dcop_files))
        dcop = load_dcop_from_file(args.dcop_files)

        if not args.hosting_default:
            raise ValueError(
                f"Missing --hosting_default when using {args.hosting} hosting cost generation"
            )

        hosting_costs = generate_hosting_costs(
            args.hosting, agents_name, dcop.variables
        )


    agents = []
    for agt_name in agents_name:
        kw = {}
        if agt_name in hosting_costs:
            kw["hosting_costs"] = hosting_costs[agt_name]
        if args.hosting_default:
            kw["default_hosting_cost"] = args.hosting_default
        if args.capacity:
            kw["capacity"] = args.capacity
        if args.routes_default:
            kw["default_route"] = args.routes_default
        agents.append(AgentDef(agt_name, **kw))

    serialized = yaml_agents(agents)

    if args.output:
        output_file = args.output
        with open(output_file, encoding="utf-8", mode="w") as fo:
            fo.write(serialized)
    else:
        print(serialized)


def generate_agents_names(agent_count: int, agent_prefix="a"):

def generate_agents_names(
    mode: str, count=None, variables=None, agent_prefix="a"
) -> List[str]:
    if mode == "count":
        return generate_agents_from_count(count, agent_prefix=agent_prefix)
    elif mode == "variables":
        return generate_agents_from_variables(variables, agent_prefix=agent_prefix)
    raise ValueError(f"Invalid mode {mode}")


def generate_agents_from_count(agent_count: int, agent_prefix="a") -> List[str]:
    digit_count = len(str(agent_count - 1))
    agents = [f"{agent_prefix}{i:0{digit_count}d}" for i in range(agent_count)]
    return agents


def generate_agents_from_variables(variables: List[str], agent_prefix="a") -> List[str]:
    prefix_length = len(find_prefix(variables))

    return [agent_prefix + variable[prefix_length:] for variable in variables]


def generate_hosting_costs(mode: str, agents: List[str], variables: List[str]):
    if mode == "name_mapping":
        costs = {}
        mappings = find_corresponding_variables(list(agents), list(variables))
        for agt_name in agents:
            agt_costs = {}
            if agt_name in mappings:
                agt_costs[mappings[agt_name]] = 0
            costs[agt_name] = agt_costs
        return costs


def find_corresponding_variables(
    agents: List[str], variables: List[str], agt_prefix="a", var_prefix="v"
) -> Dict[str, str]:
    mapping = {}
    agt_regexp = re.compile(f"{agt_prefix}(?P<index_agt>\d+)")
    var_regexp = re.compile(f"{var_prefix}(?P<index_var>\d+)")

    indexed_vars = {}
    for variable in variables:
        m = var_regexp.match(variable)
        if m:
            index = int(m.group("index_var"))
            indexed_vars[index] = variable

    for agent in agents:
        m = agt_regexp.match(agent)
        if m:
            index = int(m.group("index_agt"))
            if index in indexed_vars:
                mapping[agent] = indexed_vars[index]

    return mapping


def find_prefix(names: List[str]) -> str:
    """
    Find a common prefix in a list of string?
    Parameters
    ----------
    names: list of str

    Returns
    -------
    prefix: str
    """
    prefix_lenght = 1
    prefix = ""
    while True:
        prefix_test = names[0][:prefix_lenght]
        if all(name[:prefix_lenght] == prefix_test for name in names):
            prefix_lenght += 1
            prefix = prefix_test
            prefix_test = names[0][:prefix_lenght]
            continue
        break

    return prefix
