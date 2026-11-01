import numpy as np
from pyproj import CRS, Transformer


class GridAnalyzer:
    """
    Analiza una malla curvilínea definida mediante XP/YP.

    Las coordenadas de entrada se interpretan como longitud
    y latitud en grados decimales.
    """

    def __init__(self, longitude, latitude):

        self.longitude = np.asarray(longitude, dtype=np.float64)
        self.latitude = np.asarray(latitude, dtype=np.float64)

        if self.longitude.shape != self.latitude.shape:
            raise ValueError(
                "Longitude y latitude deben tener la misma dimensión."
            )

        if self.longitude.ndim != 2:
            raise ValueError("La malla debe ser bidimensional.")

        if min(self.longitude.shape) < 2:
            raise ValueError("La malla debe tener al menos 2 filas y 2 columnas.")

        if not np.all(np.isfinite(self.longitude)):
            raise ValueError("Hay coordenadas de longitud no válidas.")

        if not np.all(np.isfinite(self.latitude)):
            raise ValueError("Hay coordenadas de latitud no válidas.")

        if np.any(np.abs(self.latitude) > 90):
            raise ValueError("Se encontraron latitudes fuera de rango.")

        if np.any(np.abs(self.longitude) > 180):
            raise ValueError("Se encontraron longitudes fuera de rango.")

        self.ny, self.nx = self.longitude.shape

        self.crs = None
        self.transformer = None
        self.x = None
        self.y = None

    def select_crs(self):
        """
        Selecciona una zona UTM a partir del centro geográfico
        de la malla. Es una selección inicial que debe validarse
        para dominios que cruzan límites de zona.
        """

        lon_center = float(np.mean(self.longitude))
        lat_center = float(np.mean(self.latitude))

        zone = int((lon_center + 180) // 6) + 1
        zone = max(1, min(zone, 60))

        epsg = (32600 if lat_center >= 0 else 32700) + zone

        self.crs = CRS.from_epsg(epsg)

        self.transformer = Transformer.from_crs(
            "EPSG:4326",
            self.crs,
            always_xy=True
        )

        self.x, self.y = self.transformer.transform(
            self.longitude,
            self.latitude
        )

        self.x = np.asarray(self.x, dtype=np.float64)
        self.y = np.asarray(self.y, dtype=np.float64)

        if not np.all(np.isfinite(self.x)) or not np.all(np.isfinite(self.y)):
            raise ValueError("La proyección produjo coordenadas no válidas.")

        return self.crs

    def _neighbor_distances(self):

        if self.x is None:
            self.select_crs()

        dx = np.hypot(
            np.diff(self.x, axis=1),
            np.diff(self.y, axis=1)
        )

        dy = np.hypot(
            np.diff(self.x, axis=0),
            np.diff(self.y, axis=0)
        )

        return dx, dy

    @staticmethod
    def _spacing_statistics(values):

        values = np.asarray(values, dtype=np.float64)
        finite = values[np.isfinite(values)]

        if finite.size == 0:
            return {
                "count": 0,
                "minimum": float("nan"),
                "median": float("nan"),
                "maximum": float("nan"),
                "p05": float("nan"),
                "p95": float("nan"),
                "outlier_count": 0
            }

        median = float(np.median(finite))

        # Umbrales iniciales de diagnóstico, no criterios universales.
        outliers = (finite < median * 0.5) | (finite > median * 1.5)

        return {
            "count": int(finite.size),
            "minimum": float(np.min(finite)),
            "median": median,
            "maximum": float(np.max(finite)),
            "p05": float(np.percentile(finite, 5)),
            "p95": float(np.percentile(finite, 95)),
            "outlier_count": int(np.count_nonzero(outliers))
        }

    def estimate_resolution(self):

        dx, dy = self._neighbor_distances()

        horizontal = self._spacing_statistics(dx)
        vertical = self._spacing_statistics(dy)

        all_distances = np.concatenate([
            dx.ravel(),
            dy.ravel()
        ])

        valid = all_distances[
            np.isfinite(all_distances) & (all_distances > 0)
        ]

        if valid.size == 0:
            raise ValueError(
                "No se pudo calcular un espaciamiento positivo."
            )

        overall = self._spacing_statistics(valid)

        return {
            "horizontal": horizontal,
            "vertical": vertical,
            "overall": overall,
            "recommended": overall["median"]
        }

    def get_extent(self):

        if self.x is None:
            self.select_crs()

        return {
            "xmin": float(np.min(self.x)),
            "xmax": float(np.max(self.x)),
            "ymin": float(np.min(self.y)),
            "ymax": float(np.max(self.y))
        }

    def analyze(self):

        self.select_crs()

        resolution = self.estimate_resolution()
        extent = self.get_extent()

        return {
            "shape": (self.ny, self.nx),
            "crs": self.crs.to_string(),
            "resolution": resolution,
            "extent": extent
        }