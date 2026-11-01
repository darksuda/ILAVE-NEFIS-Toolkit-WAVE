
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
import threading
import queue
import csv

import numpy as np
from netCDF4 import Dataset, num2date
from scipy.interpolate import griddata

from .config import APP_NAME, APP_VERSION
from .converter import convert_nefis_to_netcdf
from .geographic_grid import build_geographic_grid
from .geotiff_writer import export_geotiff

from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import (
    FigureCanvasTkAgg,
    NavigationToolbar2Tk
)

import cartopy.crs as ccrs
import cartopy.feature as cfeature


class NEFIS2NetCDFApp:

    def __init__(self, root):

        self.root = root
        self.root.title(f"{APP_NAME} v{APP_VERSION}")
        self.root.geometry("1000x850")
        self.root.minsize(800, 650)

        self.queue = queue.Queue()
        self.running = False

        self.create_interface()
        self.root.after(100, self.process_queue)

    # ==================================================
    # INTERFAZ GENERAL
    # ==================================================

    def create_interface(self):

        style = ttk.Style()
        style.theme_use("clam")

        style.configure(
            "Title.TLabel",
            font=("Segoe UI", 17, "bold")
        )

        style.configure(
            "Subtitle.TLabel",
            font=("Segoe UI", 9)
        )

        style.configure("TButton", padding=7)

        main = ttk.Frame(self.root, padding=15)
        main.pack(fill="both", expand=True)

        ttk.Label(
            main,
            text="NEFIS2NetCDF",
            style="Title.TLabel"
        ).pack(anchor="w")

        ttk.Label(
            main,
            text="Delft3D-WAVE data processing and export",
            style="Subtitle.TLabel"
        ).pack(anchor="w", pady=(0, 15))

        self.notebook = ttk.Notebook(main)
        self.notebook.pack(fill="both", expand=True)

        self.tab_netcdf = ttk.Frame(self.notebook, padding=15)
        self.tab_geotiff = ttk.Frame(self.notebook, padding=15)
        self.tab_timeseries = ttk.Frame(self.notebook)

        self.notebook.add(self.tab_netcdf, text="NetCDF")
        self.notebook.add(self.tab_geotiff, text="GeoTIFF")
        self.notebook.add(self.tab_timeseries, text="Time Series")

        self.create_netcdf_tab()
        self.create_geotiff_tab()
        self.create_timeseries_tab()

        footer = ttk.Frame(main)
        footer.pack(fill="x", pady=(12, 0))

        self.progress = ttk.Progressbar(
            footer,
            mode="determinate",
            maximum=100
        )
        self.progress.pack(fill="x")

        self.status_var = tk.StringVar(value="Ready")

        ttk.Label(
            footer,
            textvariable=self.status_var
        ).pack(anchor="w", pady=(5, 0))

    # ==================================================
    # DETECCIÓN DE VARIABLES
    # ==================================================

    @staticmethod
    def get_spatiotemporal_variables(nc):

        if "longitude" not in nc.variables:
            raise KeyError("NetCDF has no longitude variable.")

        if "latitude" not in nc.variables:
            raise KeyError("NetCDF has no latitude variable.")

        if "time" not in nc.variables:
            raise KeyError("NetCDF has no time variable.")

        lon_var = nc.variables["longitude"]
        lat_var = nc.variables["latitude"]
        time_var = nc.variables["time"]

        if lon_var.dimensions != lat_var.dimensions:
            raise ValueError(
                "Longitude and latitude dimensions do not match."
            )

        if len(lon_var.dimensions) != 2:
            raise ValueError(
                "Expected two-dimensional geographic coordinates."
            )

        if len(time_var.dimensions) != 1:
            raise ValueError(
                "Expected a one-dimensional time variable."
            )

        spatial_dimensions = tuple(lon_var.dimensions)
        time_dimension = time_var.dimensions[0]

        expected_dimensions = (
            time_dimension,
        ) + spatial_dimensions

        available = []

        for name, variable in nc.variables.items():

            if variable.dimensions != expected_dimensions:
                continue

            if variable.shape[0] != len(nc.dimensions[time_dimension]):
                continue

            available.append(name)

        return available

    # ==================================================
    # NETCDF
    # ==================================================

    def create_netcdf_tab(self):

        frame = self.tab_netcdf

        ttk.Label(
            frame,
            text="NEFIS to NetCDF conversion",
            font=("Segoe UI", 12, "bold")
        ).pack(anchor="w", pady=(0, 15))

        self.nefis_path = tk.StringVar()
        self.netcdf_folder = tk.StringVar()
        self.netcdf_name = tk.StringVar(value="output.nc")

        self.add_file_selector(
            frame,
            "NEFIS input (.dat or .def)",
            self.nefis_path,
            self.select_nefis
        )

        self.add_folder_selector(
            frame,
            "Output folder",
            self.netcdf_folder
        )

        self.add_entry(
            frame,
            "Output filename",
            self.netcdf_name
        )

        ttk.Separator(frame).pack(fill="x", pady=20)

        ttk.Button(
            frame,
            text="Convert to NetCDF",
            command=self.start_netcdf_conversion
        ).pack(anchor="w")

    # ==================================================
    # GEOTIFF
    # ==================================================

    def create_geotiff_tab(self):

        frame = self.tab_geotiff

        ttk.Label(
            frame,
            text="NetCDF to GeoTIFF",
            font=("Segoe UI", 12, "bold")
        ).pack(anchor="w", pady=(0, 15))

        self.geotiff_input = tk.StringVar()
        self.geotiff_folder = tk.StringVar()
        self.geotiff_variable = tk.StringVar()
        self.geotiff_record = tk.StringVar(value="1")

        self.add_file_selector(
            frame,
            "Input NetCDF",
            self.geotiff_input,
            self.select_geotiff_input,
            [("NetCDF files", "*.nc")]
        )

        self.add_folder_selector(
            frame,
            "Output folder",
            self.geotiff_folder
        )

        ttk.Label(
            frame,
            text="Variable"
        ).pack(anchor="w", pady=(12, 3))

        self.geotiff_variable_combo = ttk.Combobox(
            frame,
            textvariable=self.geotiff_variable,
            values=[],
            state="readonly"
        )
        self.geotiff_variable_combo.pack(fill="x")

        ttk.Label(
            frame,
            text="Frame / Record number"
        ).pack(anchor="w", pady=(12, 3))

        self.geotiff_record_spin = ttk.Spinbox(
            frame,
            from_=1,
            to=1,
            textvariable=self.geotiff_record,
            width=15,
            command=self.update_geotiff_info
        )
        self.geotiff_record_spin.pack(anchor="w")

        self.geotiff_record_spin.bind(
            "<FocusOut>",
            lambda event: self.update_geotiff_info()
        )

        self.geotiff_record_spin.bind(
            "<Return>",
            lambda event: self.update_geotiff_info()
        )

        self.geotiff_info = tk.StringVar(
            value="Select a NetCDF file to inspect its time records."
        )

        ttk.Label(
            frame,
            textvariable=self.geotiff_info,
            justify="left",
            wraplength=680
        ).pack(anchor="w", pady=12)

        ttk.Separator(frame).pack(fill="x", pady=15)

        ttk.Button(
            frame,
            text="Export GeoTIFF",
            command=self.start_geotiff_export
        ).pack(anchor="w")

    # ==================================================
    # TIME SERIES - SCROLLABLE CONTAINER
    # ==================================================

    def create_timeseries_tab(self):

        container = ttk.Frame(self.tab_timeseries)
        container.pack(fill="both", expand=True)

        self.ts_scroll_canvas = tk.Canvas(
            container,
            highlightthickness=0
        )

        scrollbar = ttk.Scrollbar(
            container,
            orient="vertical",
            command=self.ts_scroll_canvas.yview
        )

        self.ts_scroll_canvas.configure(
            yscrollcommand=scrollbar.set
        )

        scrollbar.pack(side="right", fill="y")
        self.ts_scroll_canvas.pack(
            side="left",
            fill="both",
            expand=True
        )

        self.ts_content = ttk.Frame(
            self.ts_scroll_canvas,
            padding=15
        )

        self.ts_scroll_window = self.ts_scroll_canvas.create_window(
            (0, 0),
            window=self.ts_content,
            anchor="nw"
        )

        self.ts_content.bind(
            "<Configure>",
            lambda event: self.ts_scroll_canvas.configure(
                scrollregion=self.ts_scroll_canvas.bbox("all")
            )
        )

        self.ts_scroll_canvas.bind(
            "<Configure>",
            lambda event: self.ts_scroll_canvas.itemconfigure(
                self.ts_scroll_window,
                width=event.width
            )
        )

        # Scroll vertical con la rueda del ratón
        self.ts_scroll_canvas.bind_all(
            "<MouseWheel>",
            self.on_ts_mousewheel
        )

        self.ts_scroll_canvas.bind_all(
            "<Button-4>",
            self.on_ts_mousewheel_linux
        )

        self.ts_scroll_canvas.bind_all(
            "<Button-5>",
            self.on_ts_mousewheel_linux
        )

        frame = self.ts_content

        ttk.Label(
            frame,
            text="Geographic point time series",
            font=("Segoe UI", 12, "bold")
        ).pack(anchor="w", pady=(0, 15))

        self.ts_input = tk.StringVar()
        self.ts_folder = tk.StringVar()
        self.ts_lon = tk.StringVar()
        self.ts_lat = tk.StringVar()
        self.ts_method = tk.StringVar(value="nearest")

        self.add_file_selector(
            frame,
            "Input NetCDF",
            self.ts_input,
            self.select_timeseries_input,
            [("NetCDF files", "*.nc")]
        )

        self.add_folder_selector(
            frame,
            "Output folder",
            self.ts_folder
        )

        coordinates = ttk.Frame(frame)
        coordinates.pack(fill="x", pady=10)

        left = ttk.Frame(coordinates)
        left.pack(
            side="left",
            fill="x",
            expand=True,
            padx=(0, 5)
        )

        right = ttk.Frame(coordinates)
        right.pack(
            side="left",
            fill="x",
            expand=True,
            padx=(5, 0)
        )

        ttk.Label(left, text="Longitude").pack(anchor="w")

        ttk.Entry(
            left,
            textvariable=self.ts_lon
        ).pack(fill="x")

        ttk.Label(right, text="Latitude").pack(anchor="w")

        ttk.Entry(
            right,
            textvariable=self.ts_lat
        ).pack(fill="x")

        ttk.Label(
            frame,
            text="Select a geographic point on the grid:"
        ).pack(anchor="w", pady=(12, 5))

        self.ts_map_frame = ttk.Frame(frame)
        self.ts_map_frame.pack(fill="x", expand=True)

        self.ts_figure = Figure(
            figsize=(10, 6),
            dpi=100
        )

        self.ts_ax = self.ts_figure.add_subplot(
            111,
            projection=ccrs.PlateCarree()
        )

        self.ts_ax.set_title(
            "Load a NetCDF file to display the grid"
        )

        self.ts_canvas = FigureCanvasTkAgg(
            self.ts_figure,
            master=self.ts_map_frame
        )

        self.ts_toolbar = NavigationToolbar2Tk(
            self.ts_canvas,
            self.ts_map_frame,
            pack_toolbar=False
        )

        self.ts_toolbar.update()
        self.ts_toolbar.pack(side="top", fill="x")

        self.ts_canvas.get_tk_widget().pack(
            side="top",
            fill="both",
            expand=True
        )

        self.ts_canvas.mpl_connect(
            "button_press_event",
            self.on_map_click
        )

        # Registrar zoom una sola vez
        self.ts_canvas.mpl_connect(
            "scroll_event",
            self.on_map_scroll
        )

        self.ts_lon_grid = None
        self.ts_lat_grid = None
        self.ts_selected_point = None

        ttk.Label(
            frame,
            text="Extraction method"
        ).pack(anchor="w", pady=(15, 3))

        ttk.Radiobutton(
            frame,
            text="Nearest grid point",
            variable=self.ts_method,
            value="nearest"
        ).pack(anchor="w")

        ttk.Radiobutton(
            frame,
            text="Spatial interpolation (linear)",
            variable=self.ts_method,
            value="linear"
        ).pack(anchor="w")

        ttk.Label(
            frame,
            text="Variables (hold Ctrl to select multiple)"
        ).pack(anchor="w", pady=(15, 3))

        self.ts_variable_info = tk.StringVar(
            value="Load a NetCDF file to detect available variables."
        )

        ttk.Label(
            frame,
            textvariable=self.ts_variable_info
        ).pack(anchor="w", pady=(0, 5))

        list_frame = ttk.Frame(frame)
        list_frame.pack(fill="x", expand=True)

        self.ts_variables = tk.Listbox(
            list_frame,
            selectmode="extended",
            height=10,
            exportselection=False
        )

        variable_scrollbar = ttk.Scrollbar(
            list_frame,
            orient="vertical",
            command=self.ts_variables.yview
        )

        self.ts_variables.configure(
            yscrollcommand=variable_scrollbar.set
        )

        self.ts_variables.pack(
            side="left",
            fill="both",
            expand=True
        )

        variable_scrollbar.pack(
            side="right",
            fill="y"
        )

        ttk.Button(
            frame,
            text="Extract Time Series",
            command=self.start_timeseries
        ).pack(anchor="w", pady=15)

    # ==================================================
    # SCROLL DE TIME SERIES
    # ==================================================

    def on_ts_mousewheel(self, event):

        if self.notebook.select() != str(self.tab_timeseries):
            return

        # No desplazar la pestaña cuando el cursor está sobre el mapa.
        widget = event.widget

        while widget is not None:

            if widget == self.ts_map_frame:
                return

            widget = getattr(widget, "master", None)

        direction = -1 if event.delta > 0 else 1

        self.ts_scroll_canvas.yview_scroll(
            direction * 3,
            "units"
        )

        return "break"

    def on_ts_mousewheel_linux(self, event):

        if self.notebook.select() != str(self.tab_timeseries):
            return

        widget = event.widget

        while widget is not None:

            if widget == self.ts_map_frame:
                return

            widget = getattr(widget, "master", None)

        direction = -1 if event.num == 4 else 1

        self.ts_scroll_canvas.yview_scroll(
            direction * 3,
            "units"
        )

        return "break"

    # ==================================================
    # ZOOM DEL MAPA
    # ==================================================

    def on_map_scroll(self, event):

        if event.inaxes != self.ts_ax:
            return

        if event.xdata is None or event.ydata is None:
            return

        x_min, x_max = self.ts_ax.get_xlim()
        y_min, y_max = self.ts_ax.get_ylim()

        if event.button == "up":
            factor = 0.8
        elif event.button == "down":
            factor = 1.25
        else:
            return

        new_width = (x_max - x_min) * factor
        new_height = (y_max - y_min) * factor

        x_ratio = (
            (event.xdata - x_min) /
            (x_max - x_min)
        )

        y_ratio = (
            (event.ydata - y_min) /
            (y_max - y_min)
        )

        self.ts_ax.set_xlim(
            event.xdata - new_width * x_ratio,
            event.xdata + new_width * (1 - x_ratio)
        )

        self.ts_ax.set_ylim(
            event.ydata - new_height * y_ratio,
            event.ydata + new_height * (1 - y_ratio)
        )

        self.ts_canvas.draw_idle()

    # ==================================================
    # COMPONENTES
    # ==================================================

    def add_file_selector(
        self,
        parent,
        label,
        variable,
        callback,
        filetypes=None
    ):

        container = ttk.Frame(parent)
        container.pack(fill="x", pady=7)

        ttk.Label(
            container,
            text=label
        ).pack(anchor="w")

        row = ttk.Frame(container)
        row.pack(fill="x", pady=3)

        ttk.Entry(
            row,
            textvariable=variable
        ).pack(
            side="left",
            fill="x",
            expand=True
        )

        ttk.Button(
            row,
            text="Browse",
            command=callback
        ).pack(side="left", padx=(5, 0))

    def add_folder_selector(self, parent, label, variable):

        container = ttk.Frame(parent)
        container.pack(fill="x", pady=7)

        ttk.Label(
            container,
            text=label
        ).pack(anchor="w")

        row = ttk.Frame(container)
        row.pack(fill="x", pady=3)

        ttk.Entry(
            row,
            textvariable=variable
        ).pack(
            side="left",
            fill="x",
            expand=True
        )

        ttk.Button(
            row,
            text="Browse",
            command=lambda: self.select_folder(variable)
        ).pack(side="left", padx=(5, 0))

    def add_entry(self, parent, label, variable):

        container = ttk.Frame(parent)
        container.pack(fill="x", pady=7)

        ttk.Label(
            container,
            text=label
        ).pack(anchor="w")

        ttk.Entry(
            container,
            textvariable=variable
        ).pack(fill="x", pady=3)

    # ==================================================
    # SELECTORES DE ARCHIVOS
    # ==================================================

    def select_nefis(self):

        path = filedialog.askopenfilename(
            filetypes=[
                ("NEFIS files", "*.dat *.def"),
                ("All files", "*.*")
            ]
        )

        if path:
            self.nefis_path.set(path)

    def select_folder(self, variable):

        path = filedialog.askdirectory()

        if path:
            variable.set(path)

    def select_geotiff_input(self):

        path = filedialog.askopenfilename(
            filetypes=[("NetCDF files", "*.nc")]
        )

        if not path:
            return

        self.geotiff_input.set(path)
        self.geotiff_folder.set(str(Path(path).parent))

        try:

            with Dataset(path, "r") as nc:
                variables = self.get_spatiotemporal_variables(nc)

            self.geotiff_variable_combo.configure(
                values=variables
            )

            if variables:
                self.geotiff_variable.set(variables[0])
            else:
                self.geotiff_variable.set("")
                messagebox.showwarning(
                    "No variables",
                    "No time-dependent spatial variables were found."
                )

            self.update_geotiff_info()

        except Exception as error:

            messagebox.showerror(
                "NetCDF error",
                str(error)
            )

    def select_timeseries_input(self):

        path = filedialog.askopenfilename(
            filetypes=[("NetCDF files", "*.nc")]
        )

        if not path:
            return

        self.ts_input.set(path)
        self.ts_folder.set(str(Path(path).parent))

        self.load_timeseries_variables()
        self.load_timeseries_map()

    # ==================================================
    # CARGA AUTOMÁTICA DE VARIABLES
    # ==================================================

    def load_timeseries_variables(self):

        source = Path(self.ts_input.get())

        self.ts_variables.delete(0, "end")

        if not source.exists():
            return

        try:

            with Dataset(source, "r") as nc:
                variables = self.get_spatiotemporal_variables(nc)

            for variable in variables:
                self.ts_variables.insert("end", variable)

            if variables:
                self.ts_variables.selection_set(0)

            self.ts_variable_info.set(
                f"{len(variables)} spatial time-dependent variables detected."
            )

            if not variables:
                self.ts_variable_info.set(
                    "No valid spatial time-dependent variables found."
                )

        except Exception as error:

            self.ts_variable_info.set(
                f"Error detecting variables: {error}"
            )

            messagebox.showerror(
                "Variable detection error",
                str(error)
            )

    # ==================================================
    # MAPA INTERACTIVO
    # ==================================================

    def load_timeseries_map(self):

        source = Path(self.ts_input.get())

        if not source.exists():
            return

        try:

            with Dataset(source, "r") as nc:

                self.ts_lon_grid = np.asarray(
                    nc.variables["longitude"][:],
                    dtype=np.float64
                )

                self.ts_lat_grid = np.asarray(
                    nc.variables["latitude"][:],
                    dtype=np.float64
                )

            lon = self.ts_lon_grid
            lat = self.ts_lat_grid

            self.ts_ax.clear()

            # Océano
            self.ts_ax.set_facecolor("#b9dce9")

            # Continente y costa GSHHG Full.
            # No se añade Natural Earth COASTLINE.
            land = cfeature.GSHHSFeature(
                scale="full",
                levels=[1],
                facecolor="#e8d8b5",
                edgecolor="#555555"
            )

            self.ts_ax.add_feature(
                land,
                zorder=1
            )

            # Grilla Delft3D: únicamente líneas.
            self.ts_ax.plot(
                lon,
                lat,
                color="#1769aa",
                linewidth=0.35,
                alpha=0.85,
                transform=ccrs.PlateCarree(),
                zorder=4
            )

            self.ts_ax.plot(
                lon.T,
                lat.T,
                color="#1769aa",
                linewidth=0.35,
                alpha=0.85,
                transform=ccrs.PlateCarree(),
                zorder=4
            )

            # Extensión geográfica
            lon_min = np.nanmin(lon)
            lon_max = np.nanmax(lon)
            lat_min = np.nanmin(lat)
            lat_max = np.nanmax(lat)

            lon_margin = (lon_max - lon_min) * 0.08
            lat_margin = (lat_max - lat_min) * 0.08

            self.ts_ax.set_extent(
                [
                    lon_min - lon_margin,
                    lon_max + lon_margin,
                    lat_min - lat_margin,
                    lat_max + lat_margin
                ],
                crs=ccrs.PlateCarree()
            )

            self.ts_ax.set_title(
                "Click on the grid to select a point"
            )

            self.ts_ax.set_xlabel("Longitude")
            self.ts_ax.set_ylabel("Latitude")

            self.ts_ax.gridlines(
                draw_labels=True,
                linewidth=0.4,
                alpha=0.4,
                linestyle="--"
            )

            self.ts_selected_point = None

            self.ts_figure.tight_layout()
            self.ts_canvas.draw()

        except Exception as error:

            messagebox.showerror(
                "Map error",
                str(error)
            )

    def on_map_click(self, event):

        if event.inaxes != self.ts_ax:
            return

        if event.xdata is None or event.ydata is None:
            return

        if self.ts_lon_grid is None or self.ts_lat_grid is None:
            return

        lon = float(event.xdata)
        lat = float(event.ydata)

        if (
            lon < np.nanmin(self.ts_lon_grid)
            or lon > np.nanmax(self.ts_lon_grid)
            or lat < np.nanmin(self.ts_lat_grid)
            or lat > np.nanmax(self.ts_lat_grid)
        ):
            return

        self.ts_lon.set(f"{lon:.6f}")
        self.ts_lat.set(f"{lat:.6f}")

        if self.ts_selected_point is not None:
            self.ts_selected_point.remove()

        self.ts_selected_point = self.ts_ax.scatter(
            [lon],
            [lat],
            color="red",
            marker="x",
            s=100,
            linewidths=2,
            transform=ccrs.PlateCarree(),
            zorder=10
        )

        self.ts_canvas.draw_idle()

    # ==================================================
    # INFORMACIÓN TEMPORAL DEL NETCDF
    # ==================================================

    @staticmethod
    def format_calendar_time(time_variable, value, filename=False):

        units = getattr(time_variable, "units", None)

        if not units or " since " not in units.lower():
            raise ValueError(
                "The NetCDF time variable has no valid CF calendar units."
            )

        calendar = getattr(time_variable, "calendar", "standard")

        date = num2date(
            value,
            units=units,
            calendar=calendar
        )

        if filename:
            return date.strftime("%Y%m%d_%H%M%S")

        return date.strftime("%Y-%m-%d %H:%M:%S")

    @staticmethod
    def format_elapsed_time(seconds):

        seconds = int(seconds)

        days = seconds // 86400
        hours = (seconds % 86400) // 3600
        minutes = (seconds % 3600) // 60
        remaining_seconds = seconds % 60

        return (
            f"{days} days, {hours} hours, "
            f"{minutes} minutes, {remaining_seconds} seconds"
        )

    def update_geotiff_info(self):

        path = Path(self.geotiff_input.get())

        if not path.exists():
            return

        try:

            with Dataset(path, "r") as nc:

                if "time" not in nc.variables:
                    raise KeyError("Missing time variable.")

                times = np.asarray(nc.variables["time"][:])
                total = len(times)

                if total == 0:
                    raise ValueError(
                        "The NetCDF contains no records."
                    )

                self.geotiff_record_spin.configure(
                    from_=1,
                    to=total
                )

                try:
                    record = int(self.geotiff_record.get())
                except ValueError:
                    record = 1

                record = max(1, min(record, total))
                self.geotiff_record.set(str(record))

                time_variable = nc.variables["time"]

                first_time = self.format_calendar_time(
                    time_variable, times[0]
                )
                last_time = self.format_calendar_time(
                    time_variable, times[-1]
                )
                selected_time = self.format_calendar_time(
                    time_variable, times[record - 1]
                )

                self.geotiff_info.set(
                    f"Total records: {total}\n"
                    f"First record: {first_time}\n"
                    f"Last record: {last_time}\n"
                    f"Selected record {record}: {selected_time}"
                )

        except Exception as error:

            self.geotiff_info.set(
                f"Error reading time information: {error}"
            )

    # ==================================================
    # CONVERSIÓN NETCDF
    # ==================================================

    def start_netcdf_conversion(self):

        if self.running:
            return

        source = self.nefis_path.get().strip()
        folder = self.netcdf_folder.get().strip()
        filename = self.netcdf_name.get().strip()

        if not source or not folder or not filename:
            messagebox.showwarning(
                "Missing information",
                "Complete all input and output fields."
            )
            return

        source = Path(source)

        if source.suffix.lower() == ".def":
            source = source.with_suffix(".dat")

        if not source.exists():
            messagebox.showerror(
                "Error",
                "The NEFIS DAT file does not exist."
            )
            return

        output = Path(folder) / filename

        if output.suffix.lower() != ".nc":
            output = output.with_suffix(".nc")

        self.run_worker(
            self.convert_worker,
            source,
            output
        )

    def convert_worker(self, source, output):

        try:

            def progress(record, total):

                percent = record / total * 100

                self.queue.put((
                    "progress",
                    percent,
                    f"Converting record {record}/{total}"
                ))

            result = convert_nefis_to_netcdf(
                source,
                output,
                progress_callback=progress
            )

            self.queue.put(("success", str(result)))

        except Exception as error:

            self.queue.put(("error", str(error)))

    # ==================================================
    # EXPORTACIÓN GEOTIFF
    # ==================================================

    def start_geotiff_export(self):

        if self.running:
            return

        try:

            source = Path(self.geotiff_input.get())
            folder = Path(self.geotiff_folder.get())
            variable = self.geotiff_variable.get()
            record = int(self.geotiff_record.get())

            if not source.exists():
                raise FileNotFoundError(
                    "NetCDF file not found."
                )

            if not folder.exists():
                raise FileNotFoundError(
                    "Output folder not found."
                )

            if not variable:
                raise ValueError(
                    "Select a variable."
                )

            with Dataset(source, "r") as nc:

                times = nc.variables["time"][:]
                total = len(times)

                if record < 1 or record > total:
                    raise ValueError(
                        f"Record must be between 1 and {total}."
                    )

                time_suffix = self.format_calendar_time(
                    nc.variables["time"],
                    times[record - 1],
                    filename=True
                )

        except Exception as error:

            messagebox.showerror(
                "Invalid input",
                str(error)
            )
            return

        output = folder / f"{variable}_{time_suffix}.tif"

        self.run_worker(
            self.geotiff_worker,
            source,
            variable,
            record,
            output
        )

    def geotiff_worker(
        self,
        source,
        variable,
        record,
        output
    ):

        try:

            self.queue.put((
                "status",
                "Reading NetCDF coordinates..."
            ))

            with Dataset(source, "r") as nc:

                lon = np.asarray(
                    nc.variables["longitude"][:],
                    dtype=np.float64
                )

                lat = np.asarray(
                    nc.variables["latitude"][:],
                    dtype=np.float64
                )

                if variable not in nc.variables:
                    raise KeyError(
                        f"Variable {variable} not found."
                    )

                total = len(nc.dimensions["time"])

                if record > total:
                    raise ValueError(
                        f"Record must be between 1 and {total}."
                    )

                raw = nc.variables[variable][record - 1, :, :]

                data = np.ma.filled(raw, np.nan)
                data = np.asarray(data, dtype=np.float64)

            self.queue.put((
                "status",
                "Building geographic grid..."
            ))

            geographic_grid = build_geographic_grid(
                lon,
                lat
            )

            self.queue.put((
                "status",
                "Interpolating and exporting..."
            ))

            export_geotiff(
                data=data,
                xp=lon,
                yp=lat,
                geographic_grid=geographic_grid,
                output_path=output
            )

            self.queue.put(("success", str(output)))

        except Exception as error:

            self.queue.put(("error", str(error)))

    # ==================================================
    # EXTRACCIÓN DE SERIES TEMPORALES
    # ==================================================

    def start_timeseries(self):

        if self.running:
            return

        try:

            source = Path(self.ts_input.get())
            folder = Path(self.ts_folder.get())

            lon = float(self.ts_lon.get())
            lat = float(self.ts_lat.get())

            selected_indices = self.ts_variables.curselection()

            variables = [
                self.ts_variables.get(index)
                for index in selected_indices
            ]

            if not source.exists():
                raise FileNotFoundError(
                    "NetCDF file not found."
                )

            if not folder.exists():
                raise FileNotFoundError(
                    "Output folder not found."
                )

            if not variables:
                raise ValueError(
                    "Select at least one variable."
                )

            if not -180 <= lon <= 180:
                raise ValueError(
                    "Longitude must be between -180 and 180."
                )

            if not -90 <= lat <= 90:
                raise ValueError(
                    "Latitude must be between -90 and 90."
                )

        except Exception as error:

            messagebox.showerror(
                "Invalid input",
                str(error)
            )
            return

        with Dataset(source, "r") as nc:
            time_variable = nc.variables["time"]
            times = np.asarray(time_variable[:])

            if len(times) == 0:
                raise ValueError("NetCDF contains no time records.")

            time_start = self.format_calendar_time(
                time_variable, times[0], filename=True
            )
            time_end = self.format_calendar_time(
                time_variable, times[-1], filename=True
            )


        filename = (
            f"timeseries_"
            f"LON{lon:.4f}_LAT{lat:.4f}_"
            f"{time_start}_{time_end}.csv"
        )

        output = folder / filename

        self.run_worker(
            self.timeseries_worker,
            source,
            lon,
            lat,
            variables,
            self.ts_method.get(),
            output
        )

    def timeseries_worker(
        self,
        source,
        target_lon,
        target_lat,
        variables,
        method,
        output
    ):

        try:

            self.queue.put((
                "status",
                "Reading coordinates..."
            ))

            with Dataset(source, "r") as nc:

                lon = np.asarray(
                    nc.variables["longitude"][:],
                    dtype=np.float64
                )

                lat = np.asarray(
                    nc.variables["latitude"][:],
                    dtype=np.float64
                )

                time_variable = nc.variables["time"]
                times = np.asarray(time_variable[:])

                calendar_times = [
                    self.format_calendar_time(time_variable, value)
                    for value in times
                ]

                if lon.shape != lat.shape or lon.ndim != 2:
                    raise ValueError(
                        "Invalid coordinate dimensions."
                    )

                valid_coordinates = (
                    np.isfinite(lon) &
                    np.isfinite(lat)
                )

                if not np.any(valid_coordinates):
                    raise ValueError(
                        "No valid geographic coordinates."
                    )

                dx = (
                    (lon - target_lon) *
                    111320.0 *
                    np.cos(np.deg2rad(target_lat))
                )

                dy = (
                    (lat - target_lat) *
                    110574.0
                )

                distance = np.sqrt(dx**2 + dy**2)
                distance[~valid_coordinates] = np.inf

                nearest_index = np.unravel_index(
                    np.argmin(distance),
                    distance.shape
                )

                nearest_distance = distance[nearest_index]

                self.queue.put((
                    "status",
                    f"Nearest grid point: {nearest_distance:.1f} m away"
                ))

                rows = []
                total_records = len(times)

                for record in range(total_records):

                    row = {
                        "time": calendar_times[record]
                    }

                    for variable in variables:

                        if variable not in nc.variables:
                            raise KeyError(
                                f"Variable {variable} not found."
                            )

                        data = np.ma.filled(
                            nc.variables[variable][record, :, :],
                            np.nan
                        )

                        data = np.asarray(
                            data,
                            dtype=np.float64
                        )

                        if method == "nearest":

                            value = data[nearest_index]

                        else:

                            valid = (
                                valid_coordinates &
                                np.isfinite(data)
                            )

                            if np.count_nonzero(valid) < 3:

                                value = np.nan

                            else:

                                value = griddata(
                                    np.column_stack((
                                        lon[valid],
                                        lat[valid]
                                    )),
                                    data[valid],
                                    (target_lon, target_lat),
                                    method="linear"
                                )

                                if value is None:
                                    value = np.nan
                                else:
                                    value = float(
                                        np.asarray(value).item()
                                    )

                        row[variable] = value

                    rows.append(row)

                    if (
                        (record + 1) % 10 == 0
                        or record + 1 == total_records
                    ):

                        percent = (
                            (record + 1) /
                            total_records *
                            100
                        )

                        self.queue.put((
                            "progress",
                            percent,
                            f"Extracting record {record + 1}/{total_records}"
                        ))

            output.parent.mkdir(
                parents=True,
                exist_ok=True
            )

            with open(
                output,
                "w",
                newline="",
                encoding="utf-8"
            ) as file:

                writer = csv.DictWriter(
                    file,
                    fieldnames=["time"] + variables
                )

                writer.writeheader()
                writer.writerows(rows)

            self.queue.put(("success", str(output)))

        except Exception as error:

            self.queue.put(("error", str(error)))

    # ==================================================
    # WORKERS Y ESTADO
    # ==================================================

    def run_worker(self, function, *args):

        if self.running:
            return

        self.running = True
        self.progress["value"] = 0
        self.status_var.set("Processing...")

        thread = threading.Thread(
            target=function,
            args=args,
            daemon=True
        )

        thread.start()

    def process_queue(self):

        try:

            while True:

                message = self.queue.get_nowait()
                kind = message[0]

                if kind == "progress":

                    _, percent, text = message

                    self.progress["value"] = percent
                    self.status_var.set(text)

                elif kind == "status":

                    self.status_var.set(message[1])

                elif kind == "success":

                    self.running = False
                    self.progress["value"] = 100
                    self.status_var.set(
                        "Completed successfully."
                    )

                    messagebox.showinfo(
                        "Completed",
                        f"Output generated:\n\n{message[1]}"
                    )

                elif kind == "error":

                    self.running = False
                    self.status_var.set("Error.")

                    messagebox.showerror(
                        "Processing error",
                        message[1]
                    )

        except queue.Empty:
            pass

        self.root.after(
            100,
            self.process_queue
        )


def launch_gui():

    root = tk.Tk()
    NEFIS2NetCDFApp(root)
    root.mainloop()


if __name__ == "__main__":
    launch_gui()
