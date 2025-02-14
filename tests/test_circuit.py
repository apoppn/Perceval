# MIT License
#
# Copyright (c) 2022 Quandela
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import pytest
from pathlib import Path

from perceval import BackendFactory, CircuitAnalyser, Circuit, P, BasicState, pdisplay, Matrix
import perceval.lib.phys as phys
import perceval.lib.symb as symb
import sympy as sp
import numpy as np


def strip_line_12(s: str) -> str:
    return s.strip().replace("            ", "")


def test_helloword():
    c = symb.BS()
    assert c.m == 2
    definition = c.definition()
    assert strip_line_12(definition.pdisplay()) == strip_line_12("""
            ⎡cos(theta)               I*exp(-I*phi)*sin(theta)⎤
            ⎣I*exp(I*phi)*sin(theta)  cos(theta)              ⎦
    """)
    expected = [P(name='phi', value=0, min_v=0, max_v=2*sp.pi),
                P(name='theta', value=sp.pi/4, min_v=0, max_v=2*sp.pi)]
    for p_res, p_exp in zip(c.get_parameters(True), expected):
        assert str(p_res) == str(p_exp)
    assert c.U.is_unitary()
    for backend_name in [None, "SLOS", "Naive"]:
        simulator = BackendFactory().get_backend(backend_name)(c.U)
        expected_outputs = {
            BasicState("|0,1>"): 0.5,
            BasicState("|1,0>"): 0.5
        }
        input_state = BasicState("|0,1>")
        count = 0
        for output_state in simulator.allstate_iterator(input_state):
            assert output_state in expected_outputs
            assert pytest.approx(expected_outputs[output_state]) == simulator.prob(input_state, output_state)
            count += 1
        assert count == len(expected_outputs)
        ca = CircuitAnalyser(simulator,
                             [BasicState([0, 1]), BasicState([1, 0]), BasicState([1, 1])],  # the input states
                             "*"  # all possible output states that can be generated with 1 or 2 photons
                             )
        assert strip_line_12(ca.pdisplay()) == strip_line_12("""
            +-------+-------+-------+-------+-------+-------+
            |       | |1,0> | |0,1> | |2,0> | |1,1> | |0,2> |
            +-------+-------+-------+-------+-------+-------+
            | |0,1> |  1/2  |  1/2  |   0   |   0   |   0   |
            | |1,0> |  1/2  |  1/2  |   0   |   0   |   0   |
            | |1,1> |   0   |   0   |  1/2  |   0   |  1/2  |
            +-------+-------+-------+-------+-------+-------+
        """)


def test_empty_circuit():
    c = Circuit(4)
    m = c.compute_unitary(False)
    assert m.shape == (4, 4)
    assert np.allclose(m, Matrix.eye(4))
    assert c.pdisplay().replace(" ", "") == """

0:────:0 (depth 0)


1:────:1 (depth 0)


2:────:2 (depth 0)


3:────:3 (depth 0)

""".replace(" ", "")


def test_sbs_definition():
    phi = P("phi")
    theta = P("theta")
    bs = symb.BS(theta=theta, phi=phi)
    assert strip_line_12(bs.compute_unitary(use_symbolic=True).pdisplay()) == strip_line_12("""
            ⎡cos(theta)               I*exp(-I*phi)*sin(theta)⎤
            ⎣I*exp(I*phi)*sin(theta)  cos(theta)              ⎦""")


def test_sbs():
    bs = symb.BS()
    assert bs.U.pdisplay() == "⎡sqrt(2)/2    sqrt(2)*I/2⎤\n⎣sqrt(2)*I/2  sqrt(2)/2  ⎦"
    for backend in ["SLOS", "Naive"]:
        simulator_backend = BackendFactory().get_backend(backend)
        sbs = simulator_backend(bs.U)
        for _ in range(10):
            out = sbs.sample(BasicState("|0,1>"))
            assert str(out) == "|0,1>" or str(out) == "|1,0>"
        ca = CircuitAnalyser(sbs, [BasicState([0, 1]), BasicState([1, 0])])
        ca.compute()
        assert ca.pdisplay(nsimplify=True) == strip_line_12("""
            +-------+-------+-------+
            |       | |0,1> | |1,0> |
            +-------+-------+-------+
            | |0,1> |  1/2  |  1/2  |
            | |1,0> |  1/2  |  1/2  |
            +-------+-------+-------+""")
        assert ca.pdisplay(nsimplify=False) == strip_line_12("""
            +-------+-------+-------+
            |       | |0,1> | |1,0> |
            +-------+-------+-------+
            | |0,1> |  0.5  |  0.5  |
            | |1,0> |  0.5  |  0.5  |
            +-------+-------+-------+""")


def test_sbs_0():
    bs = symb.BS(R=1)
    assert bs.U.pdisplay() == "⎡1  0⎤\n⎣0  1⎦"
    for backend in ["SLOS", "Naive"]:
        simulator_backend = BackendFactory().get_backend(backend)
        sbs = simulator_backend(bs.U)
        for _ in range(10):
            out = sbs.sample(BasicState("|0,1>"))
            assert str(out) == "|0,1>"


def test_sbs_1():
    bs = symb.BS(R=0)
    assert bs.U.pdisplay() == "⎡0  I⎤\n⎣I  0⎦"
    for backend in ["SLOS", "Naive"]:
        simulator_backend = BackendFactory().get_backend(backend)
        sbs = simulator_backend(bs.U)
        for _ in range(10):
            out = sbs.sample(BasicState("|0,1>"))
            assert str(out) == "|1,0>"


def test_parameter():
    r = P("r")
    bs = symb.BS(R=r)
    try:
        bs.compute_unitary(use_symbolic=False)
    except TypeError:
        pass
    else:
        raise Exception("Exception should have been generated")
    assert bs.compute_unitary(use_symbolic=True).pdisplay() == strip_line_12("""
            ⎡sqrt(r)        I*sqrt(1 - r)⎤
            ⎣I*sqrt(1 - r)  sqrt(r)      ⎦""")


def test_double_parameter_ok():
    phi1 = P("phi")
    phys.BS(phi_a=phi1, phi_b=phi1)


def test_double_parameter_dup():
    phi1 = P("phi")
    phi2 = P("phi")
    try:
        phys.BS(phi_a=phi1, phi_b=phi2)
    except RuntimeError:
        pass
    else:
        raise Exception("Exception should have been generated for two parameters with same name")


def test_double_parameter_dup_multi():
    phi1 = P("phi")
    phi2 = P("phi")
    try:
        symb.BS(phi=phi1) // symb.BS(phi=phi2)
    except RuntimeError:
        pass
    else:
        raise Exception("Exception should have been generated for two parameters with same name")


def test_build_composition():
    a = symb.BS()
    b = symb.BS()
    c = a // b
    assert c.U.pdisplay() == "⎡0  I⎤\n⎣I  0⎦"


def test_build_composition_2():
    c = symb.BS() // phys.PS(phi=sp.pi/2)
    assert c.U.pdisplay() == "⎡sqrt(2)*I/2  -sqrt(2)/2⎤\n⎣sqrt(2)*I/2  sqrt(2)/2 ⎦"


def test_build_composition_3():
    c = symb.BS() // (0, phys.PS(phi=sp.pi/2))
    assert c.U.pdisplay() == "⎡sqrt(2)*I/2  -sqrt(2)/2⎤\n⎣sqrt(2)*I/2  sqrt(2)/2 ⎦"


def test_build_composition_4():
    c = symb.BS() // (1, phys.PS(phi=sp.pi/2))
    assert c.U.pdisplay() == "⎡sqrt(2)/2   sqrt(2)*I/2⎤\n⎣-sqrt(2)/2  sqrt(2)*I/2⎦"


def test_invalid_ifloor():
    try:
        phys.BS() // (1, phys.BS())
    except AssertionError:
        pass
    else:
        raise Exception('invalid ifloor should have fail')


def test_unitary():
    assert phys.BS().U.is_unitary()
    assert symb.BS().U.is_unitary()


def _gen_phys_bs(i: int):
    return phys.BS(R=P("R%d" % i))


# noinspection PyTypeChecker
def test_generator():
    c = Circuit.generic_interferometer(5, _gen_phys_bs)
    assert len(c.get_parameters()) == 5*4/2
    c = Circuit.generic_interferometer(5, _gen_phys_bs, depth=1)
    assert len(c.get_parameters()) == 2
    c = Circuit.generic_interferometer(5, _gen_phys_bs, depth=2)
    assert len(c.get_parameters()) == 4


def test_iterator():
    c = Circuit(3)
    comps = [(0, 1), (1, 2), (0, 1)]
    for k in range(len(comps)):
        c.add(comps[k], phys.BS(R=1/(k+1)))

    d = Circuit(4)
    d.add((0, 1, 2), c, merge=False)
    d.add((2, 3), phys.BS(R=1/4))
    comps.append((2, 3))

    l_comp = list(d.__iter__())

    assert len(l_comp) == 4
    for i in range(4):
        assert float(l_comp[i][1]["R"]) == 1/(i+1) and l_comp[i][0] == comps[i]


def test_evolve():
    c = phys.BS()
    for backend_name in ["SLOS", "Naive"]:
        simulator = BackendFactory().get_backend(backend_name)(c)
        assert str(simulator.evolve(BasicState("|1,0>"))) == "sqrt(2)/2*|1,0>+sqrt(2)/2*|0,1>"


def test_visualization_ucircuit(capfd):
    c = (phys.Circuit(3, U=Matrix.random_unitary(3), name="U1")
         // (0, phys.PS(sp.pi/2))
         // phys.Circuit(3, U=Matrix.random_unitary(3), name="U2"))
    pdisplay(c, output_format="text")
    out, err = capfd.readouterr()
    assert out.strip() == """
    ╭─────╮╭───────────╮╭─────╮
0:──┤U1   ├┤PS phi=pi/2├┤U2   ├──:0 (depth 3)
    │     │╰───────────╯│     │
    │     │             │     │
1:──┤     ├─────────────┤     ├──:1 (depth 2)
    │     │             │     │
    │     │             │     │
2:──┤     ├─────────────┤     ├──:2 (depth 2)
    ╰─────╯             ╰─────╯
""".strip()


TEST_DATA_DIR = Path(__file__).resolve().parent / 'data'

def test_depths_ncomponents():
    assert phys.PS(0).depths() == [1]
    assert phys.PS(0).ncomponents() == 1
    c = (phys.Circuit(3, U=Matrix.random_unitary(3), name="U1")
         // (0, phys.PS(sp.pi / 2))
         // phys.Circuit(3, U=Matrix.random_unitary(3), name="U2"))
    assert c.depths() == [3, 2, 2]
    assert c.ncomponents() == 3
    with open(TEST_DATA_DIR / 'u_random_8', "r") as f:
        M = Matrix(f)
        ub = (Circuit(2)
              // symb.BS()
              // (0, symb.PS(phi=P("φ_a")))
              // symb.BS()
              // (0, symb.PS(phi=P("φ_b"))))
        C1 = Circuit.decomposition(M, ub, shape="triangle")
        assert C1 is not None and C1.depths() == [28, 38, 32, 26, 20, 14, 8, 2]
        assert C1.ncomponents() == 112


def test_reflexivity():
    c = phys.BS(R=1/3)
    assert pytest.approx(c.compute_unitary(use_symbolic=False)[0,0]) == np.sqrt(1/3)
