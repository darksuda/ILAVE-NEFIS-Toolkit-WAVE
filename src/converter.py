
from pathlib import Path

from .nefis_reader import NefisReader
from .netcdf_writer import NetCDFWriter


def convert_nefis_to_netcdf(
    dat_path,
    output_path,
    progress_callback=None
):

    dat_path = Path(dat_path)
    output_path = Path(output_path)

    if not dat_path.exists():
        raise FileNotFoundError(
            f"No se encontró el archivo: {dat_path}"
        )

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    # ----------------------------------
    # ABRIR NEFIS
    # ----------------------------------

    with NefisReader(dat_path) as reader:

        # Obtener escala temporal y fecha de referencia
        tscale = reader.read_tscale()
        reference_datetime = reader.read_reference_datetime()

        print("Reference datetime:", reference_datetime)

        # Obtener coordenadas
        xp, yp = reader.read_coordinates()

        # Número de registros
        n_records = reader.read_record_count()

        # ----------------------------------
        # CREAR NETCDF
        # ----------------------------------

        with NetCDFWriter(
            output_path,
            n_records,
            xp,
            yp,
            tscale,
            reference_datetime
        ) as writer:

            # ----------------------------------
            # PROCESAR REGISTROS
            # ----------------------------------

            for record in range(1, n_records + 1):

                index = record - 1

                # Tiempo NEFIS
                time_value = reader.read_time(record)

                writer.write_time(
                    index,
                    time_value
                )

                # Variables espaciales
                from .config import VARIABLES

                for variable in VARIABLES:

                    data = reader.read_matrix(
                        variable,
                        record
                    )

                    writer.write_matrix(
                        variable,
                        index,
                        data
                    )

                # ----------------------------------
                # REPORTAR PROGRESO
                # ----------------------------------

                if progress_callback is not None:

                    progress_callback(
                        record,
                        n_records
                    )

    return output_path
