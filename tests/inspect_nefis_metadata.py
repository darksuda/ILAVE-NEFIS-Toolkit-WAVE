import ctypes
from pathlib import Path
from src.nefis_reader import NefisReader

dat = Path(r"D:\dsdar\Documents\codes\operacional\matarani\wavm-test_005-Grid_004.dat")

with NefisReader(dat) as reader:

    lib = reader.lib

    # Configurar Inqelm
    lib.Inqelm.argtypes = [
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
    lib.Inqelm.restype = ctypes.c_int

    # Consultar dimensiones de XP e YP
    for name in [b"XP", b"YP"]:

        elmtyp = ctypes.create_string_buffer(9)
        elmqty = ctypes.create_string_buffer(17)
        elmunt = ctypes.create_string_buffer(17)
        elmdes = ctypes.create_string_buffer(65)

        nbytes = ctypes.c_int()
        ndm = ctypes.c_int(5)
        dims = (ctypes.c_int * 5)()

        error = lib.Inqelm(
            ctypes.byref(reader.fd),
            name,
            elmtyp,
            ctypes.byref(nbytes),
            elmqty,
            elmunt,
            elmdes,
            ctypes.byref(ndm),
            dims
        )

        print(f"\nELEMENT: {name.decode()}")
        print("Error:", error)

        if error == 0:
            print("Type:", elmtyp.value)
            print("Dimensions:", list(dims)[:ndm.value])

    # Configurar Inqmxi
    lib.Inqmxi.argtypes = [
        ctypes.POINTER(ctypes.c_int),
        ctypes.c_char_p,
        ctypes.POINTER(ctypes.c_int)
    ]
    lib.Inqmxi.restype = ctypes.c_int

    max_index = ctypes.c_int(0)

    error = lib.Inqmxi(
        ctypes.byref(reader.fd),
        b"map-series",
        ctypes.byref(max_index)
    )

    print("\nMAXIMUM GROUP INDEX")
    print("Error:", error)
    print("Records:", max_index.value)
