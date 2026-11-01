
import ctypes
from datetime import datetime
import os
import numpy as np

from pathlib import Path

from .config import (
    DLL_PATH,
    DTYPES,
    NEFIS_GROUP
)


class NefisReader:

    def __init__(self, dat_path):

        self.dat_path = Path(dat_path)
        self.def_path = self.dat_path.with_suffix(".def")

        self.fd = ctypes.c_int(-1)
        self.lib = None
        self.is_open = False
        self.dll_directory = None

        self.nx = None
        self.ny = None

        self._validate_files()
        self._load_dll()
        self._configure_functions()

    # --------------------------------------
    # VALIDATE FILES
    # --------------------------------------

    def _validate_files(self):

        if not self.dat_path.exists():
            raise FileNotFoundError(
                f"DAT file not found: {self.dat_path}"
            )

        if self.dat_path.suffix.lower() != ".dat":
            raise ValueError(
                "Input file must have .dat extension."
            )

        if not self.def_path.exists():
            raise FileNotFoundError(
                f"DEF file not found: {self.def_path}"
            )

    # --------------------------------------
    # FIND NEFIS DLL
    # --------------------------------------

    @staticmethod
    def find_dll():

        candidates = []

        if DLL_PATH:
            candidates.append(Path(DLL_PATH))

        delft_home = os.environ.get("DELFT3D_HOME")

        if delft_home:
            home = Path(delft_home)

            candidates.extend([
                home / "x64" / "dwaves" / "bin" / "nefis.dll",
                home / "x64" / "bin" / "nefis.dll",
                home / "nefis.dll"
            ])

        program_files = Path(
            os.environ.get(
                "ProgramFiles",
                r"C:\Program Files"
            )
        )

        deltares = program_files / "Deltares"

        if deltares.exists():

            for installation in deltares.glob("Delft3D*"):

                candidates.extend([
                    installation / "x64" / "dwaves" / "bin" / "nefis.dll",
                    installation / "x64" / "bin" / "nefis.dll"
                ])

        for candidate in candidates:

            if candidate.is_file():
                return candidate.resolve()

        raise FileNotFoundError(
            "Could not locate nefis.dll. "
            "Set NEFIS_DLL_PATH to its full path."
        )

    # --------------------------------------
    # LOAD DLL
    # --------------------------------------

    def _load_dll(self):

        dll_path = self.find_dll()

        try:

            self.dll_directory = os.add_dll_directory(
                str(dll_path.parent)
            )

            self.lib = ctypes.CDLL(str(dll_path))

        except OSError as exc:

            if self.dll_directory is not None:
                self.dll_directory.close()
                self.dll_directory = None

            raise RuntimeError(
                f"Could not load nefis.dll: {exc}"
            ) from exc

    # --------------------------------------
    # CONFIGURE C FUNCTIONS
    # --------------------------------------

    def _configure_functions(self):

        self.lib.Crenef.argtypes = [
            ctypes.POINTER(ctypes.c_int),
            ctypes.c_char_p,
            ctypes.c_char_p,
            ctypes.POINTER(ctypes.c_char),
            ctypes.c_char
        ]
        self.lib.Crenef.restype = ctypes.c_int

        self.lib.Clsnef.argtypes = [
            ctypes.POINTER(ctypes.c_int)
        ]
        self.lib.Clsnef.restype = ctypes.c_int

        self.lib.Getelt.argtypes = [
            ctypes.POINTER(ctypes.c_int),
            ctypes.c_char_p,
            ctypes.c_char_p,
            ctypes.POINTER(ctypes.c_int),
            ctypes.POINTER(ctypes.c_int),
            ctypes.POINTER(ctypes.c_int),
            ctypes.c_void_p
        ]
        self.lib.Getelt.restype = ctypes.c_int

        self.lib.Inqelm.argtypes = [
            ctypes.POINTER(ctypes.c_int),
            ctypes.c_char_p,
            ctypes.c_char_p,
            ctypes.POINTER(ctypes.c_int),
            ctypes.c_char_p,
            ctypes.c_char_p,
            ctypes.c_char_p,
            ctypes.POINTER(ctypes.c_int),
            ctypes.POINTER(ctypes.c_int)
        ]
        self.lib.Inqelm.restype = ctypes.c_int

        self.lib.Inqmxi.argtypes = [
            ctypes.POINTER(ctypes.c_int),
            ctypes.c_char_p,
            ctypes.POINTER(ctypes.c_int)
        ]
        self.lib.Inqmxi.restype = ctypes.c_int

    # --------------------------------------
    # OPEN NEFIS
    # --------------------------------------

    def open(self):

        if self.is_open:
            return

        endian = ctypes.c_char(b"N")

        error = self.lib.Crenef(
            ctypes.byref(self.fd),
            os.fsencode(str(self.dat_path)),
            os.fsencode(str(self.def_path)),
            ctypes.byref(endian),
            ctypes.c_char(b"r")
        )

        if error != 0:
            raise RuntimeError(
                f"Crenef failed. Error code: {error}"
            )

        self.is_open = True

        print("NEFIS opened successfully.")

    # --------------------------------------
    # READ NEFIS ELEMENT
    # --------------------------------------

    def read_element(
        self,
        group,
        element,
        record,
        dtype,
        count
    ):

        if not self.is_open:
            raise RuntimeError(
                "NEFIS file is not open."
            )

        group_buffer = ctypes.create_string_buffer(
            group.encode(),
            17
        )

        element_buffer = ctypes.create_string_buffer(
            element.encode(),
            17
        )

        uindex = (ctypes.c_int * 3)(
            record,
            record,
            1
        )

        usrord = (ctypes.c_int * 1)(1)

        data = np.empty(count, dtype=dtype)

        buffer_length = ctypes.c_int(data.nbytes)

        error = self.lib.Getelt(
            ctypes.byref(self.fd),
            ctypes.cast(group_buffer, ctypes.c_char_p),
            ctypes.cast(element_buffer, ctypes.c_char_p),
            uindex,
            usrord,
            ctypes.byref(buffer_length),
            ctypes.c_void_p(data.ctypes.data)
        )

        if error != 0:
            raise RuntimeError(
                f"Getelt failed: group={group}, "
                f"variable={element}, "
                f"record={record}, error={error}"
            )

        return data

    # --------------------------------------
    # READ SPATIAL MATRIX
    # --------------------------------------

    def read_matrix(self, name, record):

        if self.nx is None or self.ny is None:
            raise RuntimeError(
                "Grid dimensions have not been initialized."
            )

        dtype = DTYPES.get(name, np.float32)

        data = self.read_element(
            NEFIS_GROUP,
            name,
            record,
            dtype,
            self.nx * self.ny
        )

        return data.reshape((self.ny, self.nx))

    # --------------------------------------
    # READ COORDINATES
    # --------------------------------------
    def read_element_dimensions(self, element):

        elmtyp = ctypes.create_string_buffer(9)
        elmqty = ctypes.create_string_buffer(17)
        elmunt = ctypes.create_string_buffer(17)
        elmdes = ctypes.create_string_buffer(65)

        nbytes = ctypes.c_int()
        ndm = ctypes.c_int(5)
        dims = (ctypes.c_int * 5)()

        error = self.lib.Inqelm(
            ctypes.byref(self.fd),
            element.encode(),
            elmtyp,
            ctypes.byref(nbytes),
            elmqty,
            elmunt,
            elmdes,
            ctypes.byref(ndm),
            dims
        )

        if error != 0:
            raise RuntimeError(
                f"Inqelm failed for {element}: error {error}"
            )

        return tuple(dims[:ndm.value])

    def read_coordinates(self):

        xp_dims = self.read_element_dimensions("XP")
        yp_dims = self.read_element_dimensions("YP")

        if len(xp_dims) != 2 or len(yp_dims) != 2:
            raise ValueError("XP and YP must be two-dimensional.")

        if xp_dims != yp_dims:
            raise ValueError(
                f"XP and YP dimensions differ: {xp_dims}, {yp_dims}"
            )

        self.nx = xp_dims[0]
        self.ny = xp_dims[1]

        xp = self.read_matrix("XP", 1)
        yp = self.read_matrix("YP", 1)

        return xp, yp
    def read_record_count(self):

        max_index = ctypes.c_int(0)

        error = self.lib.Inqmxi(
            ctypes.byref(self.fd),
            NEFIS_GROUP.encode(),
            ctypes.byref(max_index)
        )

        if error != 0:
            raise RuntimeError(
                f"Inqmxi failed: error {error}"
            )

        if max_index.value <= 0:
            raise ValueError("No records found in NEFIS group.")

        return max_index.value

    # --------------------------------------
    # READ TSCALE
    # --------------------------------------

    def read_tscale(self):

        data = self.read_element(
            "PARAMS",
            "TSCALE",
            1,
            np.float32,
            1
        )

        return float(data[0])

    # --------------------------------------
    # READ REFERENCE DATETIME
    # --------------------------------------

    def read_reference_datetime(self):

        date_value = int(
            self.read_element(
                "PARAMS", "IT01", 1, np.int32, 1
            )[0]
        )

        time_value = int(
            self.read_element(
                "PARAMS", "IT02", 1, np.int32, 1
            )[0]
        )

        date_text = str(date_value)

        if len(date_text) == 8:
            date_format = "%Y%m%d"
        elif len(date_text) == 6:
            date_format = "%y%m%d"
        else:
            raise ValueError(
                f"Unsupported NEFIS reference date: {date_value}"
            )

        time_text = f"{time_value:06d}"

        if len(time_text) != 6:
            raise ValueError(
                f"Invalid NEFIS reference time: {time_value}"
            )

        return datetime.strptime(
            date_text + time_text,
            date_format + "%H%M%S"
        )

    # --------------------------------------
    # READ TIME
    # --------------------------------------

    def read_time(self, record):

        data = self.read_element(
            NEFIS_GROUP,
            "TIME",
            record,
            np.int32,
            1
        )

        return int(data[0])

    # --------------------------------------
    # CLOSE NEFIS
    # --------------------------------------

    def close(self):

        try:

            if self.is_open:

                error = self.lib.Clsnef(
                    ctypes.byref(self.fd)
                )

                self.is_open = False

                if error != 0:
                    raise RuntimeError(
                        f"Clsnef failed. Error code: {error}"
                    )

                print("NEFIS closed successfully.")

        finally:

            if self.dll_directory is not None:
                self.dll_directory.close()
                self.dll_directory = None

    # --------------------------------------
    # CONTEXT MANAGER
    # --------------------------------------

    def __enter__(self):

        self.open()
        return self

    def __exit__(
        self,
        exc_type,
        exc_value,
        traceback
    ):

        self.close()
        return False
