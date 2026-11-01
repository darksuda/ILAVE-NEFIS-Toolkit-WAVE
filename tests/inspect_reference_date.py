import numpy as np
from src.nefis_reader import NefisReader

dat = r"D:\dsdar\Documents\codes\operacional\matarani\wavm-test_005-Grid_004.dat"

reader = NefisReader(dat)

try:
    reader.open()

    elements = [
        ("PARAMS", "IT01", np.int32),
        ("PARAMS", "IT02", np.int32),
        ("PARAMS", "TSCALE", np.float32),
    ]

    for group, element, dtype in elements:
        print(f"\n{group} / {element}")

        try:
            value = reader.read_element(
                group, element, 1, dtype, 1
            )
            print("Valor:", value[0])
        except Exception as e:
            print("Error:", e)

finally:
    reader.close()
