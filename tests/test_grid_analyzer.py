import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.nefis_reader import NefisReader
from src.grid_analyzer import GridAnalyzer


DAT_PATH = Path(
    r"D:\dsdar\Documents\codes\operacional\matarani"
    r"\wavm-test_005-Grid_004.dat"
)


def main():

    print("\nAbriendo archivo NEFIS...")

    with NefisReader(DAT_PATH) as reader:

        longitude, latitude = reader.read_coordinates()

    print("\nAnalizando geometría de la malla...")

    analyzer = GridAnalyzer(longitude, latitude)
    result = analyzer.analyze()

    print("\n========== RESULTADO ==========")

    print(f"Dimensiones: {result['shape']}")
    print(f"CRS seleccionado: {result['crs']}")

    print("\nResolución espacial:")

    for direction in ("horizontal", "vertical", "overall"):
        stats = result["resolution"][direction]

        print(f"\n  {direction.capitalize()}:")
        print(f"    Mínima:       {stats['minimum']:.3f} m")
        print(f"    Percentil 5:  {stats['p05']:.3f} m")
        print(f"    Mediana:      {stats['median']:.3f} m")
        print(f"    Percentil 95: {stats['p95']:.3f} m")
        print(f"    Máxima:       {stats['maximum']:.3f} m")
        print(f"    Valores atípicos: {stats['outlier_count']}")

    print(
        "\nResolución recomendada inicialmente: "
        f"{result['resolution']['recommended']:.3f} m"
    )
    print("\nExtensión proyectada:")
    for key, value in result["extent"].items():
        print(f"  {key}: {value:.3f} m")


if __name__ == "__main__":
    main()