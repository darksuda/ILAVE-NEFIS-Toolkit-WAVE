
import sys
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.nefis_reader import NefisReader


DAT = (
    r"D:\dsdar\Documents\codes\operacional\matarani"
    r"\wavm-test_005-Grid_004.dat"
)


with NefisReader(DAT) as reader:

    xp, yp = reader.read_coordinates()

    print("\n========== COORDENADAS ==========")

    print("Dimensiones:", xp.shape)

    print(
        "XP:",
        np.nanmin(xp),
        "->",
        np.nanmax(xp)
    )

    print(
        "YP:",
        np.nanmin(yp),
        "->",
        np.nanmax(yp)
    )

    # Coordenadas de cada celda
    rows, cols = np.indices(xp.shape)

    # Ajustar una transformación afín:
    # X = a + b*col + c*row
    # Y = d + e*col + f*row

    A = np.column_stack([
        np.ones(xp.size),
        cols.ravel(),
        rows.ravel()
    ])

    coef_x, *_ = np.linalg.lstsq(
        A,
        xp.ravel(),
        rcond=None
    )

    coef_y, *_ = np.linalg.lstsq(
        A,
        yp.ravel(),
        rcond=None
    )

    xp_fit = (A @ coef_x).reshape(xp.shape)
    yp_fit = (A @ coef_y).reshape(yp.shape)

    error_x = xp - xp_fit
    error_y = yp - yp_fit

    # Error aproximado en metros.
    lat_center = np.nanmean(yp)

    meters_x = (
        error_x * 111320 * np.cos(
            np.deg2rad(lat_center)
        )
    )

    meters_y = error_y * 111320

    error_m = np.sqrt(
        meters_x**2 + meters_y**2
    )

    print("\n========== AJUSTE GEOGRÁFICO ==========")

    print("Coeficientes X:", coef_x)
    print("Coeficientes Y:", coef_y)

    print(
        "Error máximo:",
        np.nanmax(error_m),
        "metros"
    )

    print(
        "Error medio:",
        np.nanmean(error_m),
        "metros"
    )

    # Tamaño aproximado de celda
    dx = np.sqrt(
        coef_x[1]**2 + coef_y[1]**2
    )

    dy = np.sqrt(
        coef_x[2]**2 + coef_y[2]**2
    )

    cell_x = dx * 111320 * np.cos(
        np.deg2rad(lat_center)
    )

    cell_y = dy * 111320

    print("\n========== TAMAÑO DE CELDA ==========")

    print("Paso horizontal aproximado:", cell_x, "m")
    print("Paso vertical aproximado:", cell_y, "m")

    print("\n========== RESULTADO ==========")

    if np.nanmax(error_m) < min(cell_x, cell_y) * 0.001:

        print(
            "La cuadrícula es prácticamente afín."
        )

        print(
            "Podemos evaluar GeoTIFF directo sin interpolación."
        )

    else:

        print(
            "La cuadrícula presenta curvatura significativa."
        )

        print(
            "Necesitamos estudiar una solución con geolocalización "
            "o reproyección."
        )
