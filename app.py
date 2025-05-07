from flask import Flask, render_template, request, jsonify
import pandas as pd
import requests
import numpy as np
import sys
import os
import logging
import re

# Add the project root to the Python path
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

# Import functions from src package
try:
    from src import perform_operation, perform_all_operations, get_user_input, extract_info_from_ollama, generate_response_from_ollama
except ImportError as e:
    print(f"ImportError: {e}")
    IMPORT_ERROR_OCCURRED = True
    perform_operation = None
    perform_all_operations = None
    get_user_input = None
    extract_info_from_ollama = None
    generate_response_from_ollama = None

app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')

@app.route('/predict', methods=['POST'])
def predict():
    query = request.form.get('query')
    logger.info(f"Received query: {query}")

    analysis_result = None
    trend_visualization_html = None
    spatial_visualization_html = None
    error_message = None
    explanation = None

    if query:
        try:
            if extract_info_from_ollama:
                extracted_info = extract_info_from_ollama(query)
                logger.info(f"Extracted info: {extracted_info}")

                if "error" in extracted_info:
                    error_message = extracted_info["error"]
                    return render_template('output.html', analysis_result=None, trend_graph=None, spatial_graph=None, error=error_message, original_query=query, explanation=None)

                operation = extracted_info.get("operation")
                parameter = extracted_info.get("parameter")
                location = extracted_info.get("location")
                time_range = extracted_info.get("time_range")

                # Fallback: If operation is empty, attempt to extract it from the query
                if not operation:
                    logger.warning("Operation not extracted by extract_info_from_ollama. Attempting fallback extraction.")
                    query_lower = query.lower()
                    valid_operations = ["mean", "median", "variance", "max", "min", "range", "deviation", "all"]
                    for op in valid_operations:
                        if op in query_lower:
                            operation = op
                            logger.info(f"Fallback operation extracted: {operation}")
                            break
                    if not operation:
                        error_message = "Could not determine the operation from the query. Please specify an operation like mean, median, variance, max, min, range, deviation, or all."
                        logger.error(f"Operation extraction failed: {error_message}")
                        return render_template('output.html', analysis_result=None, trend_graph=None, spatial_graph=None, error=error_message, original_query=query, explanation=None)

                logger.info(f"Operation: {operation}, Parameter: {parameter}, Location: {location}, Time Range: {time_range}")
            else:
                error_message = "Import error occurred. Cannot perform operation."
                return render_template('output.html', analysis_result=None, trend_graph=None, spatial_graph=None, error=error_message, original_query=query, explanation=None)

            if perform_operation:
                if operation in ["mean", "median", "variance", "max", "min", "range", "deviation"]:
                    try:
                        computation_result = perform_operation(operation, parameter, time_range, location)
                        logger.info(f"Operation result: {computation_result}")

                        if isinstance(computation_result, dict) and 'value' in computation_result:
                            analysis_result_value = computation_result['value']
                            unit = computation_result.get('unit', '')  # Get the unit, default to empty string
                            # Format the value to 6 decimal places and append the unit
                            display_value = "NaN" if np.isnan(analysis_result_value) else f"{analysis_result_value:.6f}"
                            analysis_result = (
                                f"The {operation} {parameter.replace('_', ' ')} over the {location} "
                                f"from {time_range[0]} to {time_range[1]} is: {display_value} {unit}".strip()
                            )
                            trend_visualization_html = computation_result.get('trend_graph')
                            spatial_visualization_html = computation_result.get('spatial_graph')

                            if generate_response_from_ollama:
                                try:
                                    explanation_response = generate_response_from_ollama(analysis_result_value, operation, parameter, time_range, location)
                                    logger.info(f"Raw Ollama Explanation Response: {explanation_response}")
                                    
                                    # Normalize newlines: replace multiple consecutive newlines with a single space
                                    if explanation_response:
                                        cleaned_explanation = re.sub(r'\n+', ' ', str(explanation_response)).strip()
                                        explanation = cleaned_explanation
                                        logger.info(f"Formatted Ollama Explanation: {explanation}")
                                except Exception as exp_error:
                                    logger.error(f"Failed to get explanation: {str(exp_error)}")
                                    explanation = None
                            else:
                                logger.warning("generate_response_from_ollama not available.")

                        else:
                            analysis_result = str(computation_result)

                        logger.info(f"Analysis result: {analysis_result}")
                    except Exception as e:
                        error_message = f"Error during computation: {str(e)}"
                        logger.error(f"Computation error: {error_message}")
                elif operation == "all":
                    all_computation_results = perform_all_operations(parameter, time_range, location)
                    logger.info(f"All operations result: {all_computation_results}")

                    if all_computation_results:
                        analysis_result_parts = []
                        all_trend_graphs = {}
                        all_spatial_graphs = {}
                        individual_explanations = []

                        for op, res_data in all_computation_results.items():
                            if "value" in res_data:
                                value = res_data['value']
                                unit = res_data.get('unit', '')  # Get the unit, default to empty string
                                display_value = "NaN" if np.isnan(value) else f"{value:.2f}"
                                analysis_result_parts.append(f"{op.capitalize()}: {display_value} {unit}".strip())
                                if res_data.get('trend_graph'):
                                    all_trend_graphs[f'{op}_trend'] = res_data['trend_graph']
                                if res_data.get('spatial_graph'):
                                    all_spatial_graphs[f'{op}_spatial'] = res_data['spatial_graph']

                                if generate_response_from_ollama:
                                    try:
                                        explanation_response = generate_response_from_ollama(res_data['value'], op, parameter, time_range, location)
                                        logger.info(f"Raw Ollama Explanation Response for {op}: {explanation_response}")
                                        
                                        # Normalize newlines: replace multiple consecutive newlines with a single space
                                        if explanation_response:
                                            cleaned_explanation = re.sub(r'\n+', ' ', str(explanation_response)).strip()
                                            individual_explanations.append(f"<strong>{op.capitalize()} Explanation:</strong> {cleaned_explanation}")
                                    except Exception as exp_error:
                                        logger.error(f"Failed to get explanation for {op}: {str(exp_error)}")
                                else:
                                    logger.warning("generate_response_from_ollama not available.")

                            elif "error" in res_data:
                                analysis_result_parts.append(f"{op.capitalize()}: Error - {res_data['error']}")

                        analysis_result = "<br>".join(analysis_result_parts)
                        # For simplicity, let's just pass the first trend and spatial graph if available
                        if all_trend_graphs:
                            trend_visualization_html = list(all_trend_graphs.values())[0]
                        if all_spatial_graphs:
                            spatial_visualization_html = list(all_spatial_graphs.values())[0]

                        if individual_explanations:
                            explanation = " ".join(individual_explanations)  # Join with a space instead of <br><br>
                            logger.info(f"Combined explanations: {explanation}")

                    else:
                        analysis_result = "All operations failed."
                else:
                    error_message = "Unsupported operation. Please choose mean, median, variance, max, min, range, deviation, or all."
            else:
                error_message = "Import error occurred. Cannot perform operation."

        except Exception as e:
            error_message = f"An error occurred during processing: {str(e)}"
            logger.error(f"Processing error: {error_message}")

    # Debug logging for template variables
    logger.info(f"Analysis result: {analysis_result}")
    logger.info(f"Error message: {error_message}")
    logger.info(f"Has trend graph: {'Yes' if trend_visualization_html else 'No'}")
    logger.info(f"Has spatial graph: {'Yes' if spatial_visualization_html else 'No'}")
    logger.info(f"Has explanation: {'Yes' if explanation else 'No'}")
    if explanation:
        logger.info(f"Explanation length: {len(explanation)}")
    
    # Ensure explanation is safe for HTML rendering
    if explanation:
        logger.info("Explanation is present and will be passed to template")
    
    return render_template('output.html',
                           analysis_result=analysis_result,
                           trend_graph=trend_visualization_html,
                           spatial_graph=spatial_visualization_html,
                           error=error_message,
                           original_query=query,
                           explanation=explanation)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)


