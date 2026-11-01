import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

import numpy as np
from netCDF4 import Dataset

from src.nefis_reader import NefisReader


DAT = (
    r"D:\dsdar\Documents\codes\operacional\matarani"
    r"\wavm-test_005-Grid_004.dat"
)

NC = "wave_test.nc"

RECORDS = [1, 2, 306, 613, 919, 1224, 1225]

VARIABLES = [
    "HSIGN",
    "DIR",
    "PERIOD",
    "DEPTH"
]


with NefisReader(DAT) as reader:

    with Dataset(NC) as nc:

        for variable in VARIABLES:

            print(f"\nVerificando {variable}")

            for record in RECORDS:

                original = reader.read_matrix(
                    variable,
                    record
                )

                exported = nc.variables[variable][
                    record - 1, :, :
                ]

                exported = np.asarray(exported)

                equal = np.array_equal(
                    original,
                    exported,
                    equal_nan=True
                )

                print(
                    f"Registro {record}: "
                    f"{'OK' if equal else 'DIFERENCIA'}"
                )

                if not equal:

                    difference = np.nanmax(
                        np.abs(
                            original.astype(np.float64)
                            - exported.astype(np.float64)
                        )
                    )

                    print(
                        f"  Diferencia máxima: {difference}"
                    )

print("\nVerificación finalizada.")
