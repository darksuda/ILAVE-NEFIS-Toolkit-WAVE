from pathlib import Path
from src.nefis_reader import NefisReader

dat = Path(r"D:\dsdar\Documents\codes\operacional\matarani\wavm-test_005-Grid_004.dat")

with NefisReader(dat) as reader:

    xp, yp = reader.read_coordinates()
    n_records = reader.read_record_count()

    print("NX:", reader.nx)
    print("NY:", reader.ny)
    print("XP shape:", xp.shape)
    print("YP shape:", yp.shape)
    print("Records:", n_records)
