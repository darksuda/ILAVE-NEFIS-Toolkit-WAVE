
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.nefis_reader import NefisReader
from src.geographic_grid import build_geographic_grid


DAT_PATH = Path(
    r"D:\dsdar\Documents\codes\operacional\matarani"
    r"\wavm-test_005-Grid_004.dat"
)


def main():

    with NefisReader(DAT_PATH) as reader:
        xp, yp = reader.read_coordinates()

    grid = build_geographic_grid(xp, yp)

    print("\n--- CUADRÍCULA GEOGRÁFICA ---")
    print("CRS: EPSG:4326")
    print("Dimensiones:", grid.shape)

    print(f"Resolución X: {grid.resolution_x:.8f}°")
    print(f"Resolución Y: {grid.resolution_y:.8f}°")

    print("\nExtensión:")
    print("Longitud:", grid.longitude.min(), grid.longitude.max())
    print("Latitud:", grid.latitude.min(), grid.latitude.max())

    print("\nResolución aproximada en metros:")
    print(
        f"Horizontal: "
        f"{grid.resolution_x * 111320 * abs(__import__('numpy').cos(__import__('numpy').deg2rad(grid.latitude.mean()))):.2f} m"
    )
    print(f"Vertical: {grid.resolution_y * 110574:.2f} m")


if __name__ == "__main__":
    main()
