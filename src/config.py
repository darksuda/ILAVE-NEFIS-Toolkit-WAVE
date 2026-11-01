
import os
import numpy as np

APP_NAME = "ILAVE NEFIS Toolkit - WAVE MODULE"
APP_VERSION = "1.0.0"

# NEFIS DLL: ruta opcional configurada por el usuario.
# Si no se especifica, NefisReader buscará automáticamente
# la instalación de Delft3D.

DLL_PATH = os.environ.get("NEFIS_DLL_PATH")

# NEFIS configuration
NEFIS_GROUP = "map-series"

# Variables to extract
VARIABLES = [
    "CODE",
    "HSIGN",
    "DIR",
    "PDIR",
    "PERIOD",
    "DEPTH",
    "VELOC-X",
    "VELOC-Y",
    "TRANSP-X",
    "TRANSP-Y",
    "DSPR",
    "RTP",
    "DISSIP",
    "LEAK",
    "QB",
    "UBOT",
    "STEEPW",
    "WLENGTH",
    "TPS",
    "TM02",
    "TMM10",
    "DHSIGN",
    "DRTM01",
    "SETUP",
    "FX",
    "FY",
    "TP"
]

# Data types
DTYPES = {
    "CODE": np.int32
}

# NetCDF configuration
NETCDF_FORMAT = "NETCDF4"
COMPRESSION_LEVEL = 4
