

# Import all necessary functions from your modules
from .main import get_user_input, extract_info_from_ollama, generate_response_from_ollama
from .compute import perform_operation, perform_all_operations, SUPPORTED_OPERATIONS, DATASET_PATHS, LOCATION_COORDS, compute_statistic  # Import compute_statistic

# Import other utilities defined in __init__.py
import re
import os
import datetime
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
import rarfile
import rasterio
from io import BytesIO

# Re-export the functions we want to make directly available from the package
__all__ = [
    'perform_operation',
    'perform_all_operations',
    'get_user_input',
    'extract_info_from_ollama',
    'generate_response_from_ollama'
]
