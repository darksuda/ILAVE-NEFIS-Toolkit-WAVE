import numpy as np
from src.nefis_reader import NefisReader
from src.config import NEFIS_GROUP

dat = r"D:\dsdar\Documents\codes\operacional\matarani\wavm-test_005-Grid_004.dat"

reader = NefisReader(dat)

try:
    reader.open()

    for element in ["TIME", "DaiTIME"]:
        print(f"\nProbando {NEFIS_GROUP} / {element}")

        try:
            for record in [1, 2, 3, 10, 100, 1225]:
                value = reader.read_element(
                    NEFIS_GROUP,
                    element,
                    record,
                    np.int32,
                    1
                )
                print(f"Registro {record}: {value[0]}")

        except Exception as e:
            print("Error:", e)

finally:
    reader.close()
