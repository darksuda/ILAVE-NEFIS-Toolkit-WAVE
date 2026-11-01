import numpy as np
from datetime import datetime, timedelta
from src.nefis_reader import NefisReader
from src.config import NEFIS_GROUP

dat = r"D:\dsdar\Documents\codes\operacional\matarani\wavm-test_005-Grid_004.dat"

reader = NefisReader(dat)
reference = datetime(2023, 8, 1, 0, 0, 0)

try:
    reader.open()

    count = reader.read_record_count()
    tscale = reader.read_tscale()

    times = []

    for record in range(1, count + 1):
        value = reader.read_element(
            NEFIS_GROUP, "TIME", record, np.int32, 1
        )[0]

        times.append(int(value))

    differences = np.diff(times)

    print("Registros:", count)
    print("TSCALE:", tscale)
    print("Intervalos únicos:", np.unique(differences))
    print("Primer TIME:", times[0])
    print("Último TIME:", times[-1])

    print("\nPrimera fecha:", reference + timedelta(seconds=times[0] * tscale))
    print("Última fecha:", reference + timedelta(seconds=times[-1] * tscale))

    print("Intervalos constantes:", np.all(differences == differences[0]))

finally:
    reader.close()
