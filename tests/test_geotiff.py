
import sys
from pathlib import Path

import numpy as np
import rasterio
from netCDF4 import Dataset

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.nefis_reader import NefisReader
from src.geographic_grid import build_geographic_grid
from src.geotiff_writer import export_geotiff


# ==================================================
# CONFIGURACIÓN
# ==================================================

DAT_PATH = Path(
    r"D:\dsdar\Documents\codes\operacional\matarani"
    r"\wavm-test_005-Grid_004.dat"
)

NETCDF_PATH = Path(
    r"D:\dsdar\Documents\codes\operacional\NEFIS2NetCDF"
    r"\wave_test.nc"
)

OUTPUT_PATH = Path(
    r"D:\dsdar\Documents\codes\operacional\NEFIS2NetCDF"
    r"\tests\HSIGN_record_001.tif"
)

VARIABLE = "HSIGN"
RECORD = 1


# ==================================================
# PROCESO PRINCIPAL
# ==================================================

def main():

    # 1. Comprobar archivos
    print("\n1. Comprobando archivos...")

    if not DAT_PATH.exists():
        raise FileNotFoundError(f"No existe: {DAT_PATH}")

    if not NETCDF_PATH.exists():
        raise FileNotFoundError(f"No existe: {NETCDF_PATH}")

    print("NEFIS:", DAT_PATH)
    print("NetCDF:", NETCDF_PATH)

    # 2. Leer coordenadas originales
    print("\n2. Leyendo coordenadas NEFIS...")

    with NefisReader(DAT_PATH) as reader:
        xp, yp = reader.read_coordinates()

    print("Dimensiones originales:", xp.shape)

    # 3. Construir grilla geográfica
    print("\n3. Construyendo grilla geográfica...")

    geographic_grid = build_geographic_grid(xp, yp)

    print("CRS: EPSG:4326")
    print("Dimensiones:", geographic_grid.shape)
    print("Resolución X:", geographic_grid.resolution_x)
    print("Resolución Y:", geographic_grid.resolution_y)

    # 4. Leer variable desde NetCDF
    print("\n4. Leyendo variable NetCDF...")

    variable_name = VARIABLE.replace("-", "_")

    with Dataset(NETCDF_PATH, "r") as nc:

        if variable_name not in nc.variables:
            raise KeyError(
                f"La variable {variable_name} no existe en el NetCDF."
            )

        if RECORD < 1 or RECORD > len(nc.dimensions["time"]):
            raise ValueError("Número de registro fuera de rango.")

        raw_data = nc.variables[variable_name][RECORD - 1, :, :]

        data = np.ma.filled(raw_data, np.nan)
        data = np.asarray(data, dtype=np.float64)

    print("Variable:", VARIABLE)
    print("Registro:", RECORD)
    print("Dimensiones:", data.shape)

    valid_data = data[np.isfinite(data)]

    if valid_data.size == 0:
        raise ValueError("La variable no contiene datos válidos.")

    print("Mínimo:", np.min(valid_data))
    print("Máximo:", np.max(valid_data))

    # 5. Exportar GeoTIFF
    print("\n5. Exportando GeoTIFF...")

    result = export_geotiff(
        data=data,
        xp=xp,
        yp=yp,
        geographic_grid=geographic_grid,
        output_path=OUTPUT_PATH
    )

    print("Archivo generado:", result)

    # 6. Verificar GeoTIFF
    print("\n6. Verificando GeoTIFF...")

    with rasterio.open(result) as src:

        raster = src.read(1)

        print("CRS:", src.crs)
        print("Dimensiones:", src.height, src.width)
        print("Resolución:", src.res)
        print("NoData:", src.nodata)
        print("Transformación:", src.transform)
        # Verificar coordenadas del centro del primer píxel
        pixel_lon, pixel_lat = src.xy(0, 0)

        expected_lon = geographic_grid.longitude[0]
        expected_lat = geographic_grid.latitude[0]

        print("\nVerificación geográfica:")
        print("Centro del primer píxel:", pixel_lon, pixel_lat)
        print("Coordenada esperada:", expected_lon, expected_lat)

        print(
            "Error longitudinal:",
            abs(pixel_lon - expected_lon),
            "grados"
        )

        print(
            "Error latitudinal:",
            abs(pixel_lat - expected_lat),
            "grados"
        )
        valid = raster != src.nodata

        print("Píxeles válidos:", np.count_nonzero(valid))
        print("Píxeles NoData:", np.count_nonzero(~valid))

        if np.any(valid):
            print("Mínimo raster:", raster[valid].min())
            print("Máximo raster:", raster[valid].max())

    print("\nPRUEBA FINALIZADA")


if __name__ == "__main__":
    main()
