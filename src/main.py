import speech_recognition as sr
import requests
import json
from src.compute import perform_operation  # Import the updated computation function
import calendar
import logging

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "mistral"


# Create a logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Create a file handler and a stream handler
file_handler = logging.FileHandler('app.log')
stream_handler = logging.StreamHandler()

# Create a formatter and add it to the handlers
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
stream_handler.setFormatter(formatter)

# Add the handlers to the logger
logger.addHandler(file_handler)
logger.addHandler(stream_handler)

def get_user_input():
    """Captures user input via speech or text."""
    recognizer = sr.Recognizer()
    
    with sr.Microphone() as source:
        print("Choose input method: 1 for Text, 2 for Voice")
        method = input("Enter 1 or 2: ")
        
        if method == "1":
            return input("Enter your query: ")
        else:
            print("Start speaking...")
            recognizer.adjust_for_ambient_noise(source, duration=0.5)
            try:
                audio = recognizer.listen(source, timeout=5, phrase_time_limit=40)
                print("Processing...")
                return recognizer.recognize_google(audio, language="en-US")
            except sr.UnknownValueError:
                logger.error("Could not understand the audio.")
            except sr.RequestError:
                logger.error("Network error.")
            except Exception as e:
                logger.error(f"Error: {e}")
    return None

def extract_info_from_ollama(query):
    """Sends the user query to Ollama for processing and extracts parameters."""

    prompt = f"""
Extract key details from the following query: 
"{query}"

Identify and extract:
- "location": The place mentioned in the query.
- "time_range": A list of two dates in the format ["YYYY-MM-DD", "YYYY-MM-DD"]. 
  - If only a year is mentioned, return ["YYYY-01-01", "YYYY-12-31"].
  - If a month and year are mentioned, return ["YYYY-MM-01", "YYYY-MM-DD"] where DD is the last day of the month.
  - If a full date range is given, return it as-is.
- "parameter": The environmental parameter requested (e.g., temperature, ocean currents, wind speed).
- "operation": The computation required (e.g., mean, max, min, variance, range, variability).

Return the output as valid JSON only.
- Use double quotes `"` around all keys and values.
- Do not include any markdown, code block syntax, or explanation.
- The response must be a plain, raw JSON object only.

Example Input: "Find the maximum rainfall in Hyderabad between June 2018 and August 2018."
Example Output:
{{
  "location": "Hyderabad",
  "time_range": ["2018-06-01", "2018-08-31"],
  "parameter": "rainfall",
  "operation": "max"
}}
"""

    data = {"model": MODEL, "prompt": prompt, "stream": False}

    try:
        response = requests.post(OLLAMA_URL, json=data)
        if response.status_code == 200:
            return json.loads(response.json().get("response", "{}"))
        else:
            logger.error(f"Ollama request failed: {response.text}")
            return {"error": f"Ollama request failed: {response.text}"}
    except Exception as e:
        logger.error(f"Request error: {e}")
        return {"error": f"Request error: {e}"}


def generate_response_from_ollama(result, operation, parameter, time_range, location):
    """Sends the computed result to Ollama for generating a natural language response."""
    
    prompt = f"""
    Summarize the following result in plain English.

    - Operation: {operation.capitalize()}
    - Parameter: {parameter.replace('_', ' ').capitalize()}
    - Time Range: From {time_range[0]} to {time_range[1]}
    - Location: {location}
    - Result: {result}

    Provide a friendly and concise explanation of what this number means in the context of the query. 
    Predict and include the most appropriate SI unit for the parameter based on its name and context.
    """

    data = {"model": MODEL, "prompt": prompt, "stream": False}

    try:
        response = requests.post(OLLAMA_URL, json=data)
        if response.status_code == 200:
            return response.json().get("response", "No response generated.")
        else:
            logger.error(f"Error in Ollama response: {response.text}")
            return f"Error in Ollama response: {response.text}"
    except Exception as e:
        logger.error(f"Request error: {e}")
        return f"Request error: {e}"


def main():
    query = get_user_input()
    if not query:
        return
    
    logger.info(f"Processing query: '{query}'")
    extracted_info = extract_info_from_ollama(query)
    logger.info("Extracted Info: %s", extracted_info)
    
    if "error" in extracted_info:
        logger.error(extracted_info["error"])
        return
    
    location = extracted_info.get("location", "Unknown Location")
    parameter = extracted_info.get("parameter", "Unknown Parameter")
    operation = extracted_info.get("operation", "Unknown Operation")
    time_range = extracted_info.get("time_range", [])

    if len(time_range) < 2:
        logger.error("Invalid time range. Please specify both start and end dates.")
        return
    
    # Perform computation using the extracted info
    result = perform_operation(operation, parameter, time_range[:2], location)
    print(result.get("graph1"))
    logger.info("\nComputed Result: %s", result)

    # Call with all required arguments
    response = generate_response_from_ollama(result, operation, parameter, time_range, location)
    logger.info("\nOllama Response: %s", response)

if __name__ == "__main__":
    main()

