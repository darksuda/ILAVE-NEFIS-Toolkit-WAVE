
import numpy as np
import rasterio

from pathlib import Path
from rasterio.transform import from_origin
from scipy.interpolate import griddata


def export_geotiff(
    data,
    xp,
    yp,
    geographic_grid,
    output_path,
    nodata=-9999.0
):
    """
    Interpola una variable desde una grilla curvilínea
    hacia una grilla geográfica regular EPSG:4326
    y exporta el resultado como GeoTIFF.
    """

    data = np.asarray(data, dtype=np.float64)
    xp = np.asarray(xp, dtype=np.float64)
    yp = np.asarray(yp, dtype=np.float64)

    # 1. Validación
    if data.ndim != 2:
        raise ValueError("Los datos deben ser una matriz 2D.")

    if data.shape != xp.shape or data.shape != yp.shape:
        raise ValueError("Las dimensiones de data, XP e YP deben coincidir.")

    # 2. Puntos originales válidos
    valid = (
        np.isfinite(data) &
        np.isfinite(xp) &
        np.isfinite(yp)
    )

    if not np.any(valid):
        raise ValueError("No existen datos válidos para interpolar.")

    points = np.column_stack((xp[valid], yp[valid]))
    values = data[valid]

    # 3. Grilla geográfica de destino
    lon_grid, lat_grid = np.meshgrid(
        geographic_grid.longitude,
        geographic_grid.latitude
    )

    # 4. Interpolación lineal
    interpolated = griddata(
        points,
        values,
        (lon_grid, lat_grid),
        method="linear",
        fill_value=np.nan
    )

    # 5. Asignar NoData
    raster_data = np.where(
        np.isfinite(interpolated),
        interpolated,
        nodata
    ).astype(np.float32)

    # 6. Transformación geográfica
    resolution_x = geographic_grid.resolution_x
    resolution_y = geographic_grid.resolution_y

    lon_min = float(geographic_grid.longitude[0])
    lat_max = float(geographic_grid.latitude[0])

    # Las coordenadas de la grilla representan centros
    # de píxel. Ajustamos el origen medio píxel.
    transform = from_origin(
        lon_min - resolution_x / 2,
        lat_max + resolution_y / 2,
        resolution_x,
        resolution_y
    )

    # 7. Exportación
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with rasterio.open(
        output_path,
        "w",
        driver="GTiff",
        height=raster_data.shape[0],
        width=raster_data.shape[1],
        count=1,
        dtype="float32",
        crs="EPSG:4326",
        transform=transform,
        nodata=nodata,
        compress="deflate",
        predictor=3
    ) as dst:

        dst.write(raster_data, 1)

        dst.set_band_description(
            1,
            "Interpolated environmental variable"
        )

        dst.update_tags(
            CRS="EPSG:4326",
            interpolation="linear",
            source="NEFIS2NetCDF"
        )

    return output_path
