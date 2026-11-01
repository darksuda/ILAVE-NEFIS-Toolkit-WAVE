import numpy as np
from netCDF4 import Dataset

from .config import (
    VARIABLES,
    DTYPES,
    NETCDF_FORMAT,
    COMPRESSION_LEVEL
)


class NetCDFWriter:

    def __init__(
        self,
        output_path,
        n_records,
        xp,
        yp,
        tscale,
        reference_datetime
    ):

        self.output_path = output_path
        self.n_records = n_records

        self.xp = xp
        self.yp = yp
        self.tscale = tscale
        self.reference_datetime = reference_datetime

        self.ny, self.nx = xp.shape

        if yp.shape != xp.shape:
            raise ValueError("XP and YP dimensions do not match.")

        self.nc = None
        self.nc_variables = {}

    def create(self):

        self.nc = Dataset(
            self.output_path,
            "w",
            format=NETCDF_FORMAT
        )

        self._create_dimensions()
        self._create_metadata()
        self._create_coordinates()
        self._create_time()
        self._create_spatial_variables()

    def _create_dimensions(self):

        self.nc.createDimension("time", self.n_records)
        self.nc.createDimension("y", self.ny)
        self.nc.createDimension("x", self.nx)

    def _create_metadata(self):

        self.nc.title = "Delft3D-WAVE simulation"
        self.nc.source = "Delft3D NEFIS"
        self.nc.history = "Converted from NEFIS to NetCDF"
        self.nc.Conventions = "CF-1.8"

    def _create_coordinates(self):

        longitude = self.nc.createVariable(
            "longitude",
            "f4",
            ("y", "x"),
            zlib=True,
            complevel=COMPRESSION_LEVEL
        )

        latitude = self.nc.createVariable(
            "latitude",
            "f4",
            ("y", "x"),
            zlib=True,
            complevel=COMPRESSION_LEVEL
        )

        longitude[:, :] = self.xp
        latitude[:, :] = self.yp

        longitude.units = "degrees_east"
        longitude.standard_name = "longitude"

        latitude.units = "degrees_north"
        latitude.standard_name = "latitude"

    def _create_time(self):

        self.time_var = self.nc.createVariable(
            "time",
            "i8",
            ("time",)
        )

        self.time_var.units = (
            "seconds since "
            + self.reference_datetime.strftime("%Y-%m-%d %H:%M:%S")
        )
        self.time_var.calendar = "proleptic_gregorian"
        self.time_var.standard_name = "time"
        self.time_var.long_name = "Time"


        self.time_var[:] = np.zeros(
            self.n_records,
            dtype=np.int64
        )

    def write_time(self, index, time_value):

        seconds = int(time_value * self.tscale)
        self.time_var[index] = seconds

    def _create_spatial_variables(self):

        for name in VARIABLES:

            dtype = DTYPES.get(name, np.float32)
            nc_name = name.replace("-", "_")

            nc_var = self.nc.createVariable(
                nc_name,
                "i4" if dtype == np.int32 else "f4",
                ("time", "y", "x"),
                zlib=True,
                complevel=COMPRESSION_LEVEL,
                shuffle=True,
                chunksizes=(1, self.ny, self.nx)
            )

            nc_var.source_name = name
            nc_var.long_name = name

            self.nc_variables[name] = nc_var

    def write_matrix(self, name, index, data):

        self.nc_variables[name][index, :, :] = data

    def close(self):

        if self.nc is not None:
            self.nc.close()
            self.nc = None

    def __enter__(self):

        self.create()
        return self

    def __exit__(self, exc_type, exc_value, traceback):

        self.close()
        return False