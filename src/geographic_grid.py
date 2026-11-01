
import numpy as np

from dataclasses import dataclass
from pyproj import CRS, Transformer


@dataclass
class GeographicGrid:
    longitude: np.ndarray
    latitude: np.ndarray
    resolution_x: float
    resolution_y: float

    @property
    def shape(self):
        return self.latitude.size, self.longitude.size

    @property
    def extent(self):
        return (
            float(self.longitude[0]),
            float(self.latitude[-1]),
            float(self.longitude[-1]),
            float(self.latitude[0])
        )


def build_geographic_grid(
    xp,
    yp,
    resolution_factor=1.0
):
    """
    Construye una grilla geográfica regular EPSG:4326
    a partir de las coordenadas curvilíneas XP/YP.

    La resolución se estima mediante el área de las celdas
    originales, considerando la rotación de la grilla.
    """

    xp = np.asarray(xp, dtype=np.float64)
    yp = np.asarray(yp, dtype=np.float64)

    # --------------------------------------------------
    # 1. Validar coordenadas
    # --------------------------------------------------

    if xp.ndim != 2 or yp.ndim != 2:
        raise ValueError("XP e YP deben ser matrices 2D.")

    if xp.shape != yp.shape:
        raise ValueError("XP e YP deben tener las mismas dimensiones.")

    if min(xp.shape) < 3:
        raise ValueError("La grilla debe tener al menos 3x3 puntos.")

    if not np.isfinite(xp).all() or not np.isfinite(yp).all():
        raise ValueError("XP e YP contienen valores no válidos.")

    if np.any(yp < -90) or np.any(yp > 90):
        raise ValueError("Las latitudes están fuera del rango válido.")

    if np.any(xp < -180) or np.any(xp > 180):
        raise ValueError("Las longitudes están fuera del rango válido.")

    if resolution_factor <= 0:
        raise ValueError("resolution_factor debe ser mayor que cero.")

    # --------------------------------------------------
    # 2. Centro geográfico de la grilla
    # --------------------------------------------------

    lon0 = float(np.mean(xp))
    lat0 = float(np.mean(yp))

    # Proyección azimutal equidistante local.
    # Se utiliza únicamente para calcular distancias y áreas.
    local_crs = CRS.from_proj4(
        f"+proj=aeqd +lat_0={lat0} +lon_0={lon0} "
        "+datum=WGS84 +units=m +no_defs"
    )

    transformer = Transformer.from_crs(
        "EPSG:4326",
        local_crs,
        always_xy=True
    )

    east, north = transformer.transform(xp, yp)

    east = np.asarray(east)
    north = np.asarray(north)

    # --------------------------------------------------
    # 3. Calcular el Jacobiano de la grilla
    # --------------------------------------------------

    # Derivadas respecto a las columnas.
    dE_dcol = np.gradient(east, axis=1)
    dN_dcol = np.gradient(north, axis=1)

    # Derivadas respecto a las filas.
    dE_drow = np.gradient(east, axis=0)
    dN_drow = np.gradient(north, axis=0)

    # Determinante del Jacobiano:
    # área física representada por cada celda original.
    cell_area = np.abs(
        dE_dcol * dN_drow -
        dE_drow * dN_dcol
    )

    valid_area = cell_area[
        np.isfinite(cell_area) & (cell_area > 0)
    ]

    if valid_area.size == 0:
        raise ValueError(
            "No se pudieron calcular áreas válidas para la grilla."
        )

    # Área mediana de las celdas originales.
    median_cell_area = float(np.median(valid_area))

    # Resolución equivalente en metros.
    resolution_m = np.sqrt(median_cell_area)

    resolution_m *= resolution_factor

    # --------------------------------------------------
    # 4. Convertir resolución a grados geográficos
    # --------------------------------------------------

    meters_per_degree_lon = (
        111320.0 * np.cos(np.deg2rad(lat0))
    )

    meters_per_degree_lat = 110574.0

    resolution_x = resolution_m / meters_per_degree_lon
    resolution_y = resolution_m / meters_per_degree_lat

    # --------------------------------------------------
    # 5. Extensión geográfica original
    # --------------------------------------------------

    lon_min = float(np.min(xp))
    lon_max = float(np.max(xp))

    lat_min = float(np.min(yp))
    lat_max = float(np.max(yp))

    # --------------------------------------------------
    # 6. Construir grilla regular
    # --------------------------------------------------

    nx = max(
        2,
        int(np.ceil((lon_max - lon_min) / resolution_x)) + 1
    )

    ny = max(
        2,
        int(np.ceil((lat_max - lat_min) / resolution_y)) + 1
    )

    longitude = np.linspace(
        lon_min,
        lon_max,
        nx
    )

    # Latitud descendente: norte -> sur.
    latitude = np.linspace(
        lat_max,
        lat_min,
        ny
    )

    # Resoluciones efectivas después de ajustar dimensiones.
    actual_resolution_x = (
        (lon_max - lon_min) / (nx - 1)
    )

    actual_resolution_y = (
        (lat_max - lat_min) / (ny - 1)
    )

    return GeographicGrid(
        longitude=longitude,
        latitude=latitude,
        resolution_x=float(actual_resolution_x),
        resolution_y=float(actual_resolution_y)
    )
