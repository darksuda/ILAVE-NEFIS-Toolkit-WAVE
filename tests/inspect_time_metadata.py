from src.nefis_reader import NefisReader

dat = r"D:\dsdar\Documents\codes\operacional\matarani\wavm-test_005-Grid_004.dat"

reader = NefisReader(dat)

try:
    reader.open()

    print("\n=== METADATOS TEMPORALES ===")

    print("TSCALE:", reader.read_tscale())

    for record in [0, 1, 2, 10, 100, 1224]:
        print(f"Registro {record}: {reader.read_time(record)}")

finally:
    reader.close()