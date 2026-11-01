import sys
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.nefis_reader import NefisReader


DAT_PATH = Path(
    r"D:\dsdar\Documents\codes\operacional\matarani"
    r"\wavm-test_005-Grid_004.dat"
)

OUTPUT_IMAGE = PROJECT_ROOT / "tests" / "grid_diagnostic.png"


def main():
    with NefisReader(DAT_PATH) as reader:
        xp, yp = reader.read_coordinates()

    # Distancias aproximadas entre puntos consecutivos, en metros.
    lat_rad = np.deg2rad(yp)

    dx = (
        np.diff(xp, axis=1)
        * 111320
        * np.cos(lat_rad[:, :-1])
    )
    dy = np.diff(yp, axis=1) * 111320

    horizontal_spacing = np.hypot(dx, dy)

    dx_vertical = (
        np.diff(xp, axis=0)
        * 111320
        * np.cos(lat_rad[:-1, :])
    )
    dy_vertical = np.diff(yp, axis=0) * 111320

    vertical_spacing = np.hypot(dx_vertical, dy_vertical)
    print("\n--- ESPACIAMIENTO EN LOS BORDES ---")

    print(
        "Última fila (horizontal):",
        np.median(horizontal_spacing[-1, :])
    )

    print(
        "Fila anterior (horizontal):",
        np.median(horizontal_spacing[-2, :])
    )

    print(
        "Última columna (vertical):",
        np.median(vertical_spacing[:, -1])
    )

    print(
        "Columna anterior (vertical):",
        np.median(vertical_spacing[:, -2])
    )

    print("\n--- DIAGNÓSTICO DE LA CUADRÍCULA ---")
    print(f"Dimensiones: {xp.shape}")

    for name, distances in [
        ("Horizontal", horizontal_spacing),
        ("Vertical", vertical_spacing),
    ]:
        print(f"\n{name}:")
        print(f"  Mínimo:  {np.nanmin(distances):.3f} m")
        print(f"  Mediana: {np.nanmedian(distances):.3f} m")
        print(f"  Máximo:  {np.nanmax(distances):.3f} m")

    # Visualización de las líneas de la cuadrícula.
    fig, ax = plt.subplots(figsize=(11, 9))

    # Distribuir uniformemente las líneas de visualización.
    n_lines = 25

    row_indices = np.linspace(
        0, xp.shape[0] - 1, n_lines, dtype=int
    )

    col_indices = np.linspace(
        0, xp.shape[1] - 1, n_lines, dtype=int
    )

    for i in row_indices:
        ax.plot(xp[i, :], yp[i, :], linewidth=0.7)

    for j in col_indices:
        ax.plot(xp[:, j], yp[:, j], linewidth=0.7)



    ax.set_title("Delft3D-WAVE: curvilinear grid")
    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")
    ax.set_aspect("equal", adjustable="datalim")
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(OUTPUT_IMAGE, dpi=200)

    print("\n--- COORDENADAS DE LOS BORDES ---")

    for name, i, j in [
        ("Esquina superior izquierda", 0, 0),
        ("Esquina superior derecha", 0, -1),
        ("Esquina inferior izquierda", -1, 0),
        ("Esquina inferior derecha", -1, -1),
    ]:
        print(f"{name}: XP={xp[i,j]:.8f}, YP={yp[i,j]:.8f}")

    print("\n--- EXTENSIÓN DE LA CUADRÍCULA ---")
    print(f"Longitud: {xp.min():.8f} a {xp.max():.8f}")
    print(f"Latitud:  {yp.min():.8f} a {yp.max():.8f}")

    print("\n--- DIFERENCIAS ENTRE LOS EXTREMOS ---")
    print("Última fila:")
    print("  Δ longitud:", np.diff(xp[-1, :])[-5:])
    print("  Δ latitud:", np.diff(yp[-1, :])[-5:])

    print("Última columna:")
    print("  Δ longitud:", np.diff(xp[:, -1])[-5:])
    print("  Δ latitud:", np.diff(yp[:, -1])[-5:])
    plt.close()

    print(f"\nImagen guardada en:\n{OUTPUT_IMAGE}")


if __name__ == "__main__":
    main()