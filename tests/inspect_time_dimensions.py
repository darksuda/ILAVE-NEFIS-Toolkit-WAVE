import ctypes
from src.nefis_reader import NefisReader

dat = r"D:\dsdar\Documents\codes\operacional\matarani\wavm-test_005-Grid_004.dat"

reader = NefisReader(dat)

try:
    reader.open()

    for element in ["TIME", "IT01", "IT02", "TSCALE"]:
        print(f"\n=== {element} ===")

        try:
            dims = reader.read_element_dimensions(element)
            print("Dimensiones:", dims)

        except Exception as e:
            print("Error:", e)

finally:
    reader.close()
