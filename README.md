# ILAVE NEFIS Toolkit – WAVE MODULE

**ILAVE NEFIS Toolkit – WAVE MODULE** is a Python desktop application designed to process Delft3D-WAVE 4 simulation outputs stored in NEFIS format.

It provides a graphical interface to convert, visualize, and extract numerical simulation data into widely used scientific data formats.

## Features

### 1. NEFIS to NetCDF
- Reads Delft3D-WAVE NEFIS `.dat` and `.def` files.
- Automatically detects spatial grid dimensions.
- Automatically detects the number of simulation records.
- Extracts spatial and temporal simulation variables.
- Preserves simulation calendar dates and timestamps.
- Supports compressed NetCDF output.

### 2. GeoTIFF Export
- Exports selected simulation variables as GeoTIFF files.
- Generates geographic grids in EPSG:4326.
- Supports spatial interpolation.
- Uses simulation dates in output filenames.

### 3. Time Series Extraction
- Interactive spatial grid visualization.
- Geographic point selection.
- Nearest-neighbor and linear interpolation.
- CSV export with geographic coordinates and calendar timestamps.

## Requirements

- Windows 10 or later.
- Python 3.11 or later.
- Delft3D-WAVE 4 installation providing a compatible `nefis.dll`.
- A matching NEFIS `.dat` and `.def` file pair.

## Installation

Clone the repository:

```bash
git clone https://github.com/darksuda/NEFIS2NetCDF.git
cd NEFIS2NetCDF
```

Create and activate a virtual environment:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

Install the required dependencies:

```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## NEFIS Library Configuration

ILAVE NEFIS Toolkit – WAVE MODULE requires `nefis.dll`, which is provided by Delft3D.

**The NEFIS library is not included in this repository and is not redistributed with the application.**

The application attempts to locate the DLL automatically in common Delft3D installation directories.

If automatic detection fails, configure its location using one of the following environment variables.

### Option 1: Specify the full DLL path

```powershell
$env:NEFIS_DLL_PATH = "C:\Path\To\nefis.dll"
```

### Option 2: Specify the Delft3D installation directory

```powershell
$env:DELFT3D_HOME = "C:\Program Files\Deltares\Delft3D 4.05.01"
```

These settings apply to the current PowerShell session.

## Running the Application

From the project root, activate the virtual environment and execute:

```powershell
python main.py
```

## Building the Windows Application

A Windows executable can be generated using the included build script.

Make sure the virtual environment and dependencies are installed, then run:

```powershell
.\build.bat
```

The packaged application will be generated inside:

```text
dist/
└── ILAVE NEFIS Toolkit - WAVE MODULE/
    ├── ILAVE NEFIS Toolkit - WAVE MODULE.exe
    └── _internal/
```

The executable requires a compatible Delft3D NEFIS library installation. The `nefis.dll` file is not bundled with the application.

## Input Files

The application requires a matching pair of NEFIS files:

```text
simulation.dat
simulation.def
```

Both files must have the same base filename and be located in the same directory.

## Output Formats

| Format | Description |
|---|---|
| NetCDF | Spatial and temporal simulation data, including calendar timestamps. |
| GeoTIFF | Geographic raster outputs in EPSG:4326. |
| CSV | Extracted time series at selected geographic locations. |

## Project Structure

```text
ILAVE-NEFIS-Toolkit-WAVE/
│
├── src/
│   ├── config.py
│   ├── nefis_reader.py
│   ├── netcdf_writer.py
│   ├── converter.py
│   ├── geographic_grid.py
│   ├── geotiff_writer.py
│   ├── grid_analyzer.py
│   └── gui.py
│
├── tests/
│
├── resources/
│
├── main.py
├── requirements.txt
├── build.bat
├── .gitignore
└── README.md
```

## Limitations

- Designed specifically for Delft3D-WAVE 4 NEFIS outputs.
- Requires a compatible NEFIS library installation.
- Delft3D and `nefis.dll` are not bundled or redistributed.
- Compatibility with other Delft3D versions has not been established.

## License

No license has been specified yet.

All rights reserved by default until a license is explicitly added.

## Author

**Carlo André Ilave Barboza**

GitHub: https://github.com/darksuda