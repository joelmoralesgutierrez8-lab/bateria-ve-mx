"""Semillas fijas para reproducibilidad (seed=42 por defecto)."""
from __future__ import annotations

import os
import random

import numpy as np


def fijar_semillas(semilla: int = 42) -> np.random.Generator:
    """Fija random, numpy (global) y torch si está instalado. Devuelve un Generator de numpy para usar
    explícitamente en el código (preferible al estado global)."""
    random.seed(semilla)
    np.random.seed(semilla)
    os.environ["PYTHONHASHSEED"] = str(semilla)
    try:
        import torch

        torch.manual_seed(semilla)
        torch.use_deterministic_algorithms(True, warn_only=True)
    except ImportError:
        pass
    return np.random.default_rng(semilla)
