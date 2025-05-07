import os
import datetime
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
import rasterio
from rasterio.warp import transform as rio_transform
import logging

# Configure logging
logger = logging.getLogger(__name__)

# Supported operations
SUPPORTED_OPERATIONS = {
    "mean": "mean",
    "median": "median",
    "variance": "variance",
    "trend": "linearFit",
    "max": "max",
    "min": "min",
    "range": "range",
    "deviation": "deviation"
}

# Dataset path
DATASET_PATHS = "/home/arya/Desktop/datasets"

# Bounding boxes for known locations
LOCATION_COORDS = {
    "indian ocean": {
        "lon_min": 20, "lon_max": 120,
        "lat_min": -60, "lat_max": 30
    },
    "atlantic ocean": {
        "lon_min": -80, "lon_max": 20,
        "lat_min": -60, "lat_max": 70
    },
    "pacific ocean": {
        "lon_min": 180, "lon_max": 300,
        "lat_min": -60, "lat_max": 60
    },
}

# Dataset mapping parameters to their respective units
PARAMETER_UNITS = {
    "ocean currents": "m/s",          # Ocean currents in meters 
    "water vapour": "mm"              # Water vapor in millimeters
}

def get_parameter_dir(parameter):
    parameter = parameter.lower().replace(" ", "_")
    return os.path.join(DATASET_PATHS, parameter)

def get_required_tif_files(parameter, year, start_date, end_date):
    """
    Get TIF files for a parameter within a date range.
    """
    selected_files = []
    year_dir = os.path.join(get_parameter_dir(parameter), str(year))
    if not os.path.exists(year_dir):
        logger.warning(f"Directory does not exist: {year_dir}")
        return []

    all_files = os.listdir(year_dir)
    logger.info(f"Found {len(all_files)} files in {year_dir}")
    
    for filename in all_files:
        if filename.endswith(".tif"):
            date_part = filename.split("_")[-1].replace(".tif", "")
            try:
                file_date = datetime.datetime.strptime(date_part, "%Y%m%d")
                if start_date <= file_date <= end_date:
                    selected_files.append(os.path.join(year_dir, filename))
            except ValueError:
                logger.warning(f"Could not parse date from filename: {filename}")
                continue
    
    logger.info(f"Selected {len(selected_files)} files for time range {start_date} to {end_date}")
    return selected_files

def read_geotiff_files(matching_files, location=None):
    """
    Read and crop GeoTIFF files based on location coordinates.
    Returns cropped data, latitude grid, and longitude grid.
    """
    cropped_data_list = []
    cropped_lat_grid = None
    cropped_lon_grid = None
    location = location.lower() if location else None

    if location and location in LOCATION_COORDS:
        bounds = LOCATION_COORDS[location]
        lon_min, lon_max = bounds["lon_min"], bounds["lon_max"]
        lat_min, lat_max = bounds["lat_min"], bounds["lat_max"]
    else:
        bounds = None

    for file in sorted(matching_files):
        try:
            with rasterio.open(file) as src:
                data = src.read(1)
                transform = src.transform
                rows, cols = data.shape

                # Generate coordinate grids
                col_indices, row_indices = np.meshgrid(np.arange(cols), np.arange(rows))
                lons, lats = transform * (col_indices, row_indices)

                test1 = np.nanmax(lons)
                logger.debug(f"Cropped data shape: {test1}")
                if bounds:
                    # Create mask for the bounding box
                    mask = (lons >= lon_min) & (lons <= lon_max) & (lats >= lat_min) & (lats <= lat_max)
                    if not np.any(mask):
                        logger.warning(f"No data within bounds for {os.path.basename(file)}. Skipping.")
                        continue

                    # Find indices for cropping
                    row_mask = np.any(mask, axis=1)
                    col_mask = np.any(mask, axis=0)
                    row_start = np.argmax(row_mask)
                    row_end = len(row_mask) - np.argmax(row_mask[::-1])
                    col_start = np.argmax(col_mask)
                    col_end = len(col_mask) - np.argmax(col_mask[::-1])

                    # Crop data and grids
                    cropped_data = data[row_start:row_end, col_start:col_end]
                    cropped_lats = lats[row_start:row_end, col_start:col_end]
                    cropped_lons = lons[row_start:row_end, col_start:col_end]
                else:
                    cropped_data = data
                    cropped_lats = lats
                    cropped_lons = lons

                if np.sum(~np.isnan(cropped_data)) == 0:
                    logger.warning(f"Cropped data for {os.path.basename(file)} contains all NaN values. Skipping.")
                    continue

                cropped_data_list.append(cropped_data)
                if cropped_lat_grid is None:
                    cropped_lat_grid = cropped_lats
                    cropped_lon_grid = cropped_lons

                # Verify consistency of grid shapes
                if cropped_data.shape != cropped_data_list[0].shape:
                    logger.error(f"Inconsistent shapes in cropped data for {file}")
                    return None, None, None

        except Exception as e:
            logger.error(f"Failed reading {file}: {e}")
            continue

    if not cropped_data_list:
        logger.warning("No valid cropped data found in any of the files")
        return None, None, None

    return cropped_data_list, cropped_lat_grid, cropped_lon_grid

def calculate_daily_statistic(data, operation):
    if np.all(np.isnan(data)):
        logger.warning("All values are NaN, cannot calculate statistic")
        return np.nan
        
    valid_count = np.sum(~np.isnan(data))
    if valid_count == 0:
        logger.warning("No valid data points for calculation")
        return np.nan
        
    logger.debug(f"Calculating {operation} on {valid_count} valid data points")
    
    try:
        if operation == "mean":
            return np.nanmean(data)
        elif operation == "median":
            return np.nanmedian(data)
        elif operation == "max":
            return np.nanmax(data)
        elif operation == "min":
            return np.nanmin(data)
        elif operation == "variance":
            return np.nanvar(data)
        elif operation == "range":
            return np.nanmax(data) - np.nanmin(data)
        elif operation == "deviation":
            return np.nanstd(data)
        else:
            logger.error(f"Unknown operation: {operation}")
            return np.nan
    except Exception as e:
        logger.error(f"Error calculating {operation}: {e}")
        return np.nan

def calculate_spatial_statistic(stacked_data, operation):
    if stacked_data.size == 0 or np.all(np.isnan(stacked_data)):
        logger.warning("All values in stacked data are NaN")
        return None
        
    try:
        if operation == "mean":
            result = np.nanmean(stacked_data, axis=0)
        elif operation == "median":
            result = np.nanmedian(stacked_data, axis=0)
        elif operation == "max":
            result = np.nanmax(stacked_data, axis=0)
        elif operation == "min":
            result = np.nanmin(stacked_data, axis=0)
        elif operation == "variance":
            result = np.nanvar(stacked_data, axis=0)
        elif operation == "range":
            result = np.nanmax(stacked_data, axis=0) - np.nanmin(stacked_data, axis=0)
        elif operation == "deviation":
            result = np.nanstd(stacked_data, axis=0)
        else:
            logger.error(f"Unknown operation: {operation}")
            return None
            
        logger.debug(f"Spatial {operation} result shape: {result.shape}")
        logger.debug(f"Result contains {np.sum(~np.isnan(result))}/{result.size} valid pixels")
        return result
    except Exception as e:
        logger.error(f"Error calculating spatial {operation}: {e}")
        return None

def calculate_scalar_statistic(stacked_data, operation):
    if stacked_data.size == 0 or np.all(np.isnan(stacked_data)):
        logger.warning("All values in stacked data are NaN")
        return np.nan
        
    try:
        if operation == "mean":
            result = float(np.nanmean(stacked_data))
        elif operation == "median":
            result = float(np.nanmedian(stacked_data))
        elif operation == "max":
            result = float(np.nanmax(stacked_data))
        elif operation == "min":
            result = float(np.nanmin(stacked_data))
        elif operation == "variance":
            result = float(np.nanvar(stacked_data))
        elif operation == "range":
            result = float(np.nanmax(stacked_data) - np.nanmin(stacked_data))
        elif operation == "deviation":
            result = float(np.nanstd(stacked_data))
        else:
            logger.error(f"Unknown operation: {operation}")
            return np.nan
            
        logger.debug(f"Scalar {operation} result: {result}")
        return result
    except Exception as e:
        logger.error(f"Error calculating scalar {operation}: {e}")
        return np.nan

def compute_statistic(cropped_data, operation, return_daily=False, return_spatial=False):
    """
    Compute statistic from cropped data.
    """
    all_data = []
    daily_values = []
    dates = []
    logger.info(f"Processing {len(cropped_data)} cropped data arrays for {operation} calculation")
    
    for i, data in enumerate(cropped_data):
        if np.sum(~np.isnan(data)) == 0:
            logger.warning(f"Cropped data index {i} contains all NaN values. Skipping.")
            continue
        
        all_data.append(data)
        if return_daily:
            daily_value = calculate_daily_statistic(data, operation)
            logger.debug(f"Daily {operation}: {daily_value}")
            daily_values.append(daily_value)
            # Placeholder for date; adjust as needed
            date = datetime.datetime.now()
            dates.append(date)

    if not all_data:
        logger.warning("No valid data found in cropped arrays")
        return "No valid data found."

    logger.debug(f"Stacking {len(all_data)} valid data arrays")
    stacked = np.stack(all_data)
    logger.debug(f"Stacked shape: {stacked.shape}")
    logger.debug(f"Contains NaN: {np.isnan(stacked).any()}")
    logger.debug(f"NaN percentage: {np.isnan(stacked).sum() / stacked.size * 100:.2f}%")
    
    spatial_result = None
    if return_spatial:
        spatial_result = calculate_spatial_statistic(stacked, operation)
        if spatial_result is not None:
            logger.debug(f"Spatial result shape: {spatial_result.shape}")
            logger.debug(f"Spatial result NaN percentage: {np.isnan(spatial_result).sum() / spatial_result.size * 100:.2f}%")
    
    scalar_result = calculate_scalar_statistic(stacked, operation)
    logger.info(f"Final scalar {operation} result: {scalar_result}")

    return {
        "scalar": scalar_result,
        "trend": (dates, daily_values) if return_daily else None,
        "spatial": spatial_result
    }

def plot_trend(dates, values, operation, title=None):
    if not dates or not values or len(dates) != len(values):
        logger.warning(f"Invalid data for trend plot. Dates: {len(dates)}, Values: {len(values)}")
        return None
        
    valid_indices = [i for i, v in enumerate(values) if not np.isnan(v)]
    if not valid_indices:
        logger.warning("No valid values for trend plot")
        return None
        
    valid_dates = [dates[i] for i in valid_indices]
    valid_values = [values[i] for i in valid_indices]
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=valid_dates, y=valid_values, mode='lines+markers', name=operation))
    if title is None:
        title = f"Daily {operation.capitalize()} Trend"
    fig.update_layout(
        title=title,
        xaxis_title="Date",
        yaxis_title=operation.capitalize(),
        template="plotly_white"
    )
    return fig.to_html(full_html=False)

def plot_spatial_raster(raster_data, lat_grid, lon_grid, title="Spatial Plot"):
    """
    Plot spatial raster with coordinate grids.
    """
    if raster_data is None or np.all(np.isnan(raster_data)):
        logger.warning("No valid data for spatial plot")
        return None
        
    fig = px.imshow(raster_data, 
                    x=lon_grid[0, :], 
                    y=lat_grid[:, 0], 
                    origin="lower",  # Changed from "upper" to "lower"
                    color_continuous_scale="Viridis",
                    labels={"color": "Value"}, 
                    title=title, 
                    aspect="1.5")
    fig.update_layout(
        xaxis_title="Longitude",
        yaxis_title="Latitude",
        coloraxis_colorbar=dict(title="Value")
    )
    return fig.to_html(full_html=False)

def perform_operation(operation, parameter, time_range, location=None, with_trend=True, with_spatial=True):
    logger.info(f"===== PERFORMING {operation.upper()} ON {parameter.upper()} =====")
    logger.info(f"Time range: {time_range[0]} to {time_range[1]}")
    logger.info(f"Location: {location or 'global'}")
    
    def is_valid_date(date_str):
        try:
            datetime.datetime.strptime(date_str, "%Y-%m-%d")
            return True
        except ValueError:
            return False

    if not (is_valid_date(time_range[0]) and is_valid_date(time_range[1])):
        logger.error("Invalid date format")
        return "Invalid date format."

    start_date = datetime.datetime.strptime(time_range[0], "%Y-%m-%d")
    end_date = datetime.datetime.strptime(time_range[1], "%Y-%m-%d")

    if start_date > end_date:
        logger.error("Start date is after end date")
        return "Invalid date range: Start date is after end date."

    location = location.lower() if location else location

    if location and location not in LOCATION_COORDS:
        logger.error(f"Invalid location: '{location}'")
        return f"Invalid location: '{location}'"

    param_dir = get_parameter_dir(parameter)
    logger.debug(f"Parameter directory: {param_dir}")
    if not os.path.exists(param_dir):
        logger.error(f"Parameter directory not found")
        return f"Parameter '{parameter}' not found."

    start_year = start_date.year
    end_year = end_date.year

    matching_files = []
    for year in range(start_year, end_year + 1):
        year_files = get_required_tif_files(parameter, year, start_date, end_date)
        matching_files.extend(year_files)

    if not matching_files:
        logger.error("No matching data files found")
        return "No matching data files found."

    # Crop the data and get coordinate grids
    cropped_data, cropped_lat_grid, cropped_lon_grid = read_geotiff_files(matching_files, location)
    if cropped_data is None:
        return "No valid cropped data found."

    # Compute statistics on cropped data
    result = compute_statistic(cropped_data, operation, return_daily=with_trend, return_spatial=with_spatial)

    if isinstance(result, str):
        logger.error(f"Computation failed: {result}")
        return result

    scalar_result = result["scalar"]
    # Get the unit for the parameter (default to empty string if not found)
    unit = PARAMETER_UNITS.get(parameter.lower(), "")
    # Keep the numeric value separate and provide the unit separately
    logger.info(f"{operation.capitalize()} value over the selected region and time: {scalar_result} {unit}")

    trend_plot_html = None
    spatial_plot_html = None

    if result["trend"]:
        dates, values = result["trend"]
        trend_plot_html = plot_trend(dates, values, operation)

    if result["spatial"] is not None:
        title = f"Spatial {operation.capitalize()} Plot - {location.title() if location else 'Global'}"
        spatial_plot_html = plot_spatial_raster(result["spatial"], cropped_lat_grid, cropped_lon_grid, title=title)

    return {
        "operation": operation,
        "value": scalar_result,  # Numeric value (float)
        "unit": unit,            # Unit as a separate field
        "parameter": parameter,
        "time_range": time_range,
        "location": location,
        "trend_graph": trend_plot_html,
        "spatial_graph": spatial_plot_html
    }

def perform_all_operations(parameter, time_range, location=None):
    results = {}
    operations = [op for op in SUPPORTED_OPERATIONS if op != "trend"]

    for operation in operations:
        logger.info(f"--- {operation.upper()} ---")
        result = perform_operation(operation, parameter, time_range, location)
        if isinstance(result, dict) and "value" in result:
            results[operation] = {
                "value": result["value"],
                "unit": result["unit"],  # Pass the unit to the results
                "trend_graph": result.get("trend_graph"),
                "spatial_graph": result.get("spatial_graph")
            }
        else:
            results[operation] = {"error": result}

    return results