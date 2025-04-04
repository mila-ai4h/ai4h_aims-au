"""RunIf test configurator.

Adapted from:
https://github.com/Lightning-AI/lightning/blob/master/tests/tests_pytorch/helpers/runif.py
"""
import os
import sys
from typing import Optional

import dotenv
import pytest
import torch
from packaging.version import Version
from pkg_resources import get_distribution

import qut01.utils.config
from tests.helpers.module_available import (
    _DEEPSPEED_AVAILABLE,
    _IS_ON_MILA_CLUSTER,
    _IS_WINDOWS,
    _RPC_AVAILABLE,
)


class RunIf:
    """RunIf wrapper for conditional skipping of tests.

    Fully compatible with `@pytest.mark`.

    Example:

        @RunIf(min_torch="1.8")
        @pytest.mark.parametrize("arg1", [1.0, 2.0])
        def test_wrapper(arg1):
            assert arg1 > 0
    """

    def __new__(
        self,
        min_gpus: int = 0,
        min_torch: Optional[str] = None,
        max_torch: Optional[str] = None,
        min_python: Optional[str] = None,
        skip_windows: bool = False,
        only_on_mila_cluster: bool = False,
        has_mlflow_installed: bool = False,
        has_comet_api_key: bool = False,
        rpc: bool = False,
        deepspeed: bool = False,
        **kwargs,
    ):
        """Validates and checks the required platform/runtime settings for the test.

        Args:
            min_gpus: min number of gpus required to run test
            min_torch: minimum pytorch version to run test
            max_torch: maximum pytorch version to run test
            min_python: minimum python version required to run test
            skip_windows: skip test for Windows platform
            only_on_mila_cluster: only run test on Mila cluster environment
            has_mlflow_installed: requires MLFlow to be installed to run test
            has_comet_api_key: requires a comet api key env variable to run test
            rpc: requires Remote Procedure Call (RPC)
            deepspeed: if `deepspeed` module is required to run the test
            kwargs: native pytest.mark.skipif keyword arguments
        """
        conditions = []
        reasons = []

        if min_gpus:
            conditions.append(torch.cuda.device_count() < min_gpus)
            reasons.append(f"GPUs>={min_gpus}")

        if min_torch:
            torch_version = get_distribution("torch").version
            conditions.append(Version(torch_version) < Version(min_torch))
            reasons.append(f"torch>={min_torch}")

        if max_torch:
            torch_version = get_distribution("torch").version
            conditions.append(Version(torch_version) >= Version(max_torch))
            reasons.append(f"torch<{max_torch}")

        if min_python:
            py_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
            conditions.append(Version(py_version) < Version(min_python))
            reasons.append(f"python>={min_python}")

        if skip_windows:
            conditions.append(_IS_WINDOWS)
            reasons.append("does not run on Windows")

        if only_on_mila_cluster:
            conditions.append(not _IS_ON_MILA_CLUSTER)
            reasons.append("can only run on Mila cluster")

        if has_mlflow_installed:
            try:
                import mlflow

                conditions.append(False)
            except ImportError:
                conditions.append(True)
                reasons.append("can only run if MLFlow is installed")

        if has_comet_api_key:
            # this one might be in a .dotenv file, so we'll load one if possible
            dotenv_path = qut01.utils.config.get_framework_dotenv_path()
            if dotenv_path is not None:
                dotenv.load_dotenv(dotenv_path=str(dotenv_path), override=True, verbose=True)
            comet_api_key = os.getenv("COMET_API_KEY")
            conditions.append(comet_api_key is None)
            reasons.append("can only run with `COMET_API_KEY` defined")

        if rpc:
            conditions.append(not _RPC_AVAILABLE)
            reasons.append("RPC")

        if deepspeed:
            conditions.append(not _DEEPSPEED_AVAILABLE)
            reasons.append("Deepspeed")

        reasons = [rs for cond, rs in zip(conditions, reasons) if cond]
        return pytest.mark.skipif(
            condition=any(conditions),
            reason=f"Requires: [{' + '.join(reasons)}]",
            **kwargs,
        )
