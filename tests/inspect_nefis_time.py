
from pathlib import Path

from src.nefis_reader import NefisReader

dat = Path(
    r"D:\dsdar\Documents\codes\operacional\matarani\wavm-test_005-Grid_004.dat"
)
def_file = dat.with_suffix(".def")

reader = NefisReader(str(dat), str(def_file))

try:
    reader.open()

    print("\n=== GRUPOS Y ELEMENTOS TEMPORALES ===")

    # Inspeccionamos los grupos y elementos que el lector
    # ya conoce o utiliza.
    for name in dir(reader):
        if not name.startswith("_"):
            print(name)

finally:
    reader.close()
