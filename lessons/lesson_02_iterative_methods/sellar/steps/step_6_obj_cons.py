"""Sellar walkthrough - Step 6: add the objective and constraints.

The MDA is only the *analysis*. To make it an optimizable model we add the
objective and the two constraints as ``ExecComp`` one-liners (an ``ExecComp`` is
just a tiny ExplicitComponent - a green FUNC box in Lesson 1's vocabulary)::

    obj  = x**2 + z2 + y1 + exp(-y2)
    con1 = 3.16 - y1        (feasible when <= 0)
    con2 = y2 - 24.0        (feasible when <= 0)

Two structural changes come with this step:

1. **Wrap the two coupled disciplines in a ``cycle`` subgroup and put the solver
   on that subgroup.** A nonlinear solver's job is only the loop; obj/con are
   pure feed-forward and must sit *outside* it, or the solver would needlessly
   iterate them too.
2. **Switch from explicit ``connect`` to ``promotes``.** Promotion connects
   same-named variables automatically (d1's output ``y1`` to d2's input ``y1``,
   d2's output ``y2`` to d1's input ``y2``), which is the idiomatic OpenMDAO way
   and how the official docs write Sellar. It also exposes ``y1``/``y2`` by name
   so obj/con can read them.

The model now has everything an optimizer needs - design variables (z, x), an
objective, and constraints - which sets up week 3 (add a driver; the blue OPT
pill from Lesson 1).

Run from the repository root (with the ``eng-des-opt-course`` environment active)::

    python lessons/lesson_02_iterative_methods/sellar/steps/step_6_obj_cons.py
"""

from __future__ import annotations

import numpy as np
import openmdao.api as om


class SellarDis1(om.ExplicitComponent):
    """Discipline 1: ``y1 = z1**2 + z2 + x - 0.2 * y2``."""

    def setup(self):
        self.add_input("z", val=np.zeros(2))
        self.add_input("x", val=0.0)
        self.add_input("y2", val=1.0)
        self.add_output("y1", val=1.0)

    def setup_partials(self):
        self.declare_partials("*", "*", method="fd")

    def compute(self, inputs, outputs):
        z1 = inputs["z"][0]
        z2 = inputs["z"][1]
        x = inputs["x"]
        y2 = inputs["y2"]
        outputs["y1"] = z1**2 + z2 + x - 0.2 * y2


class SellarDis2(om.ExplicitComponent):
    """Discipline 2: ``y2 = sqrt(y1) + z1 + z2``."""

    def setup(self):
        self.add_input("z", val=np.zeros(2))
        self.add_input("y1", val=1.0)
        self.add_output("y2", val=1.0)

    def setup_partials(self):
        self.declare_partials("*", "*", method="fd")

    def compute(self, inputs, outputs):
        z1 = inputs["z"][0]
        z2 = inputs["z"][1]
        y1 = inputs["y1"]
        if y1.real < 0.0:
            y1 *= -1
        outputs["y2"] = y1**0.5 + z1 + z2


class SellarMDA(om.Group):
    """The Sellar MDA plus objective and constraints."""

    def setup(self):
        # The coupled disciplines live in their own subgroup so the solver wraps
        # only the loop. promotes=['*'] lifts z, x, y1, y2 to this group's level.
        cycle = self.add_subsystem("cycle", om.Group(), promotes=["*"])
        cycle.add_subsystem(
            "d1", SellarDis1(),
            promotes_inputs=["x", "z", "y2"], promotes_outputs=["y1"],
        )
        cycle.add_subsystem(
            "d2", SellarDis2(),
            promotes_inputs=["z", "y1"], promotes_outputs=["y2"],
        )
        cycle.nonlinear_solver = om.NonlinearBlockGS()

        self.set_input_defaults("x", val=1.0)
        self.set_input_defaults("z", val=np.array([5.0, 2.0]))

        self.add_subsystem(
            "obj_cmp",
            om.ExecComp("obj = x**2 + z[1] + y1 + exp(-y2)", z=np.array([0.0, 0.0]), x=0.0),
            promotes=["x", "z", "y1", "y2", "obj"],
        )
        self.add_subsystem("con_cmp1", om.ExecComp("con1 = 3.16 - y1"), promotes=["con1", "y1"])
        self.add_subsystem("con_cmp2", om.ExecComp("con2 = y2 - 24.0"), promotes=["con2", "y2"])


def main():
    prob = om.Problem(model=SellarMDA())
    prob.setup()

    prob.set_val("z", [5.0, 2.0])
    prob.set_val("x", 1.0)
    prob.run_model()

    print(f"y1   = {prob.get_val('y1')[0]:.4f}   (expected 25.5883)")
    print(f"y2   = {prob.get_val('y2')[0]:.4f}   (expected 12.0585)")
    print(f"obj  = {prob.get_val('obj')[0]:.4f}   (expected 28.5883)")
    print(f"con1 = {prob.get_val('con1')[0]:.4f}   (expected -22.4283)")
    print(f"con2 = {prob.get_val('con2')[0]:.4f}   (expected -11.9415)")


if __name__ == "__main__":
    main()
