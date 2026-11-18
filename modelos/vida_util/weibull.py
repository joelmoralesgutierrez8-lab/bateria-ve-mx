"""Distribución de Weibull de 2 parámetros con censura por la derecha.

Parametrización (forma beta, escala eta, ambos > 0):
    F(t) = 1 - exp(-(t/eta)^beta)                 probabilidad de haber llegado al fin de vida en t
    S(t) = exp(-(t/eta)^beta)                     supervivencia
    f(t) = (beta/eta) (t/eta)^(beta-1) S(t)
    h(t) = (beta/eta) (t/eta)^(beta-1)            tasa de falla; beta > 1 = desgaste que se acelera

Log-verosimilitud con censura por la derecha (evento=1 llegó al fin de vida; evento=0 seguía viva al final
de la prueba):
    log L = sum_eventos log f(t_i) + sum_censuradas log S(t_j)

La optimización se hace en (log beta, log eta) para que ambos sean positivos sin restricciones.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.optimize import minimize
from scipy.special import gamma


# ---------------------------------------------------------------- funciones de la distribución
def cdf(t, beta: float, eta: float):
    t = np.clip(np.asarray(t, float), 0, None)
    return -np.expm1(-((t / eta) ** beta))


def supervivencia(t, beta: float, eta: float):
    t = np.clip(np.asarray(t, float), 0, None)
    return np.exp(-((t / eta) ** beta))


def pdf(t, beta: float, eta: float):
    t = np.asarray(t, float)
    z = np.where(t > 0, t / eta, 0.0)
    return np.where(t > 0, (beta / eta) * z ** (beta - 1) * np.exp(-(z**beta)), 0.0)


def hazard(t, beta: float, eta: float):
    t = np.asarray(t, float)
    return (beta / eta) * (t / eta) ** (beta - 1)


def media(beta: float, eta: float) -> float:
    return eta * gamma(1 + 1 / beta)


def cuantil(p, beta: float, eta: float):
    return eta * (-np.log1p(-np.asarray(p, float))) ** (1 / beta)


# ---------------------------------------------------------------- ajuste
def _validar(t, evento):
    t = np.asarray(t, float)
    evento = np.asarray(evento).astype(bool)
    if t.shape != evento.shape or t.ndim != 1:
        raise ValueError("t y evento deben ser vectores del mismo largo")
    if np.any(t <= 0) or not np.all(np.isfinite(t)):
        raise ValueError("los tiempos deben ser positivos y finitos")
    if evento.sum() == 0:
        raise ValueError("sin ningún fin de vida observado la Weibull no es identificable")
    return t, evento


def log_verosimilitud(beta: float, eta: float, t, evento) -> float:
    t, evento = np.asarray(t, float), np.asarray(evento, bool)
    z = (t / eta) ** beta
    log_f = np.log(beta) - np.log(eta) + (beta - 1) * np.log(t / eta) - z
    return float(log_f[evento].sum() - z[~evento].sum())


@dataclass
class AjusteWeibull:
    beta: float
    eta: float
    log_verosimilitud: float
    n: int
    n_eventos: int
    convergio: bool

    def como_dict(self) -> dict:
        return {
            "beta": self.beta,
            "eta": self.eta,
            "vida_media": media(self.beta, self.eta),
            "b10": float(cuantil(0.10, self.beta, self.eta)),   # tiempo al que falla el 10%
            "mediana": float(cuantil(0.50, self.beta, self.eta)),
            "log_verosimilitud": self.log_verosimilitud,
            "n": self.n,
            "n_eventos": self.n_eventos,
            "convergio": self.convergio,
        }


def ajustar(t, evento) -> AjusteWeibull:
    """MLE de (beta, eta) con censura por la derecha."""
    t, evento = _validar(t, evento)

    def nll(theta):
        b, e = np.exp(theta)
        return -log_verosimilitud(b, e, t, evento)

    x0 = np.log([2.0, np.median(t[evento])])
    res = minimize(nll, x0, method="Nelder-Mead", options={"xatol": 1e-8, "fatol": 1e-10, "maxiter": 5000})
    res = minimize(nll, res.x, method="BFGS")                # pulido
    b, e = np.exp(res.x)
    return AjusteWeibull(float(b), float(e), float(-res.fun), len(t), int(evento.sum()), bool(res.success))


def ajustar_beta_comun(grupos: dict[str, tuple]) -> dict:
    """Weibull con forma beta COMPARTIDA y escala eta propia de cada grupo.

    Útil cuando los grupos miden el tiempo en unidades distintas (ciclos completos vs ciclos de manejo):
    beta no depende de la unidad del tiempo, eta sí. grupos = {nombre: (t, evento)}.
    """
    nombres = list(grupos)
    datos = {k: _validar(*grupos[k]) for k in nombres}

    def nll(theta):
        b = np.exp(theta[0])
        return -sum(log_verosimilitud(b, np.exp(theta[i + 1]), *datos[k]) for i, k in enumerate(nombres))

    x0 = np.log([2.0] + [np.median(datos[k][0][datos[k][1]]) for k in nombres])
    res = minimize(nll, x0, method="Nelder-Mead", options={"xatol": 1e-8, "fatol": 1e-10, "maxiter": 20000})
    res = minimize(nll, res.x, method="BFGS")
    b = float(np.exp(res.x[0]))
    return {
        "beta": b,
        "eta": {k: float(np.exp(res.x[i + 1])) for i, k in enumerate(nombres)},
        "log_verosimilitud": float(-res.fun),
        "convergio": bool(res.success),
    }


def prueba_beta_comun(grupos: dict[str, tuple]) -> dict:
    """Razón de verosimilitudes: beta común (k+1 parámetros) vs beta libre por grupo (2k parámetros).
    p pequeño = las formas de degradación difieren entre conjuntos y no conviene compartir beta."""
    from scipy.stats import chi2

    comun = ajustar_beta_comun(grupos)
    libres = {k: ajustar(*v) for k, v in grupos.items()}
    ll_libre = sum(a.log_verosimilitud for a in libres.values())
    estadistico = 2 * (ll_libre - comun["log_verosimilitud"])
    gl = len(grupos) - 1
    return {"estadistico_lr": float(estadistico), "grados_libertad": gl,
            "p_valor": float(chi2.sf(max(estadistico, 0.0), gl)),
            "beta_por_grupo": {k: a.beta for k, a in libres.items()}, "beta_comun": comun["beta"]}


def bootstrap(t, evento, repeticiones: int, rng: np.random.Generator, nivel: float = 0.90,
              min_eventos_distintos: int = 2) -> dict:
    """Bootstrap no paramétrico por UNIDAD (celda): remuestrea celdas completas con reemplazo.
    Una réplica con menos de `min_eventos_distintos` tiempos de falla distintos deja beta sin identificar
    (tiende a infinito), así que se descarta y se cuenta en `replicas_descartadas`."""
    t, evento = _validar(t, evento)
    n = len(t)
    betas, etas, descartadas = [], [], 0
    for _ in range(repeticiones):
        idx = rng.integers(0, n, n)
        if len(np.unique(t[idx][evento[idx]])) < min_eventos_distintos:
            descartadas += 1
            continue
        a = ajustar(t[idx], evento[idx])
        betas.append(a.beta)
        etas.append(a.eta)
    alfa = (1 - nivel) / 2
    betas, etas = np.array(betas), np.array(etas)
    return {
        "beta_ic": tuple(np.quantile(betas, [alfa, 1 - alfa])),
        "eta_ic": tuple(np.quantile(etas, [alfa, 1 - alfa])),
        "replicas_validas": len(betas),
        "replicas_descartadas": descartadas,
        "muestras": {"beta": betas, "eta": etas},
    }
