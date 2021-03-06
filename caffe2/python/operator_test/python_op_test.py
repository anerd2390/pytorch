from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals
from caffe2.python import core, workspace
from caffe2.python.core import CreatePythonOperator
import caffe2.python.hypothesis_test_util as hu
from hypothesis import given
import hypothesis.strategies as st
import numpy as np
import unittest

if workspace.is_asan:
    # Numba seems to be not compatible with ASAN (at least at Facebook)
    # so if we are in asan mode, we disable Numba which further disables
    # the numba python op test.
    HAS_NUMBA = False
else:
    try:
        import numba
        HAS_NUMBA = True
    except ImportError:
        HAS_NUMBA = False


class PythonOpTest(hu.HypothesisTestCase):
    @unittest.skipIf(not HAS_NUMBA, "")
    @given(x=hu.tensor(),
           n=st.integers(min_value=1, max_value=20),
           w=st.integers(min_value=1, max_value=20))
    def test_multithreaded_evaluation_numba_nogil(self, x, n, w):
        @numba.jit(nopython=True, nogil=True)
        def g(input_, output):
            output[...] = input_

        def f(inputs, outputs):
            outputs[0].reshape(inputs[0].shape)
            g(inputs[0].data, outputs[0].data)

        ops = [CreatePythonOperator(f, ["x"], [str(i)]) for i in range(n)]
        net = core.Net("net")
        net.Proto().op.extend(ops)
        net.Proto().type = "dag"
        net.Proto().num_workers = w
        iters = 100
        plan = core.Plan("plan")
        plan.AddStep(core.ExecutionStep("test-step", net, iters))
        workspace.FeedBlob("x", x)
        workspace.RunPlan(plan.Proto().SerializeToString())
        for i in range(n):
            y = workspace.FetchBlob(str(i))
            np.testing.assert_almost_equal(x, y)


if __name__ == "__main__":
    import unittest
    unittest.main()
