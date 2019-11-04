from compiler.data_structures import Program
from compiler.passes.analyses.bs_analysis import BSAnalysis

import networkx as nx
import json
from collections import defaultdict

# Use-def chain
# https://en.wikipedia.org/wiki/Use-define_chain
# https://github.com/lilott8/ChemCompiler-Deprecated-/blob/master/src/main/java/compilation/datastructures/basicblock/DependencySlicedBasicBlock.java

# RUN COMMAND: python3 main.py -i tests/test_cases/slice/slice1.bs -t ir
# Stick to formats that have libraries between languages : JSON recommend
# NetworkX goes away at this stage
# Be aware of certain flow displays of mfsim
# Goals: Build def-use chain, implicitly building the needed DAGs, Dependency Graph


class Chain(object):

    def __init__(self, block: int, instruction: int):
        self.block = -1
        self.instruction = -1


class Slicer(BSAnalysis):

    def __init__(self):
        super().__init__("Slicer")
        self.multi_use = dict()

    def analyze(self, program: Program) -> dict:
        self.multi_use = self.build_def_use_chain(program)
        return {'name': self.name, 'result': None}

    def build_def_use_chain(self, program: Program) -> dict:
        deps = dict()
        defs = dict()
        uses = list()
        used = defaultdict(list)
        many_use = defaultdict(list)
        use_json = dict()
        conds = dict()

        for root in program.functions:
            self.log.info("Function: {}".format(root))

            # sorted blocks so always same order each time
            for nid, block in sorted(program.functions[root]['blocks'].items()):
                i_counter = 1
                self.log.info("\tBlock: {}".format(nid))

                for instruction in block.instructions:
                    self.log.info("\t\t{}".format(instruction))

                    # DEF: DISPENSE, ...
                    if str(type(instruction)) == "<class 'compiler.data_structures.ir.Dispense'>":
                        ins = str(instruction).split('=')
                        var = ins[0].strip()
                        exp = ins[1:]

                        deps[var] = exp
                        defs[var] = (nid, i_counter)

                    # USE && DEF: MIX, HEAT, SPLIT, ...
                    if (str(type(instruction)) == "<class 'compiler.data_structures.ir.Mix'>" or
                            str(type(instruction)) == "<class 'compiler.data_structures.ir.Heat'>" or
                            str(type(instruction)) == "<class 'compiler.data_structures.ir.Split'>"):

                        ins = str(instruction).split('=')
                        var = ins[0].strip()
                        exp = ins[1:]
                        parts = str(exp)[7:-3].split(',')

                        deps[var] = exp
                        defs[var] = (nid, i_counter)
                        uses.extend([(parts[0].strip(), (nid, i_counter)), (parts[1].strip(), (nid, i_counter))])

                    # CONTROL FLOW: CONDITIONAL
                    if str(type(instruction)) == "<class 'compiler.data_structures.ir.Conditional'>":
                        tmp = str(instruction).split('\t')
                        data = (tmp[2].strip()[3:], tmp[3].strip()[3:])
                        conds[(nid, i_counter)] = data

                        # maybe recurse, or save where the branches are...
                        # maybe if was a graph then could see where the join edges go
                        # if 2 edges goto same node and both use a variable, mark the variable as used
                        # if encountered again, then add

                    # Line Counter
                    i_counter += 1

        # find the possible conflicts
        for u in uses:
            used[u[0]].append(u[1])
        for u in used:
            # TODO: figure out with conditionals
            # check if multi use occurred one after the other,
            # but not on the same level like in an if/else
            if len(used[u]) > 1:
                self.log.warn("\n{}, {}".format(conds, used[u]))
                many_use[u] = used[u]  # adds all uses, but usually need the last ones

        # print statements with the log format info = green, warn = yellow, error = red
        self.log.info("\nDeps: \n{} \nDefs: \n{} \nUses: \n{} \nUsed:  \n{} \nMulti-Used: \n{}"
                      .format(deps, defs, uses, dict(used), dict(many_use)))

        # output data file
        for u in many_use:
            use_json[u] = "{}".format(many_use[u])
        with open('data.txt', 'w') as outfile:
            json.dump(use_json, outfile)

        return use_json

