from typing import List, Dict
import logging
import json
import os
import convertor


logger = logging.getLogger(__name__)

# List of fields to exclude
exclude_fields = {"address.entrance", "address.poBox","landlinePhone","natureOfAccident","medicalDiagnoses"}
def eval_average_filling_accuracy(json_results: List[str]) -> float:
    """
    Returns percentage of non-empty fields across all documents.
    Excludes specified unimportant fields.
    """
    if not json_results:
        return 0.0
    total_fields = 0
    filled_fields = 0

    for json_str in json_results:
        try:
            data = json.loads(json_str)

            # Flatten nested dictionaries to count all fields
            def count_fields(d, prefix=""):
                nonlocal total_fields, filled_fields
                for key, value in d.items():
                    field_path = f"{prefix}{key}" if not prefix else f"{prefix}.{key}"
                    if field_path in exclude_fields:
                        continue
                    if isinstance(value, dict):
                        count_fields(value, field_path)
                    else:
                        total_fields += 1
                        if value is not None and value != "":
                            filled_fields += 1

            count_fields(data)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON: {str(e)}")
            continue

    return (filled_fields / total_fields * 100) if total_fields > 0 else 0.0


def calculate_field_completion_rates(json_results: List[str]) -> Dict[str, float]:
    """
    Calculate completion rate for each field across all documents.
    Returns dictionary with field paths and their completion percentages.
    Excludes specified unimportant fields.
    """
    if not json_results:
        return {}

    field_counts = {}
    field_filled = {}
    total_docs = 0

    for json_str in json_results:
        try:
            data = json.loads(json_str)
            total_docs += 1

            def track_fields(d, prefix=""):
                for key, value in d.items():
                    field_path = f"{prefix}{key}" if not prefix else f"{prefix}.{key}"
                    # Skip if field is in exclude list
                    if field_path in exclude_fields:
                        continue
                    if isinstance(value, dict):
                        track_fields(value, field_path)
                    else:
                        field_counts[field_path] = field_counts.get(field_path, 0) + 1
                        if value is not None and value != "":
                            field_filled[field_path] = field_filled.get(field_path, 0) + 1

            track_fields(data)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON: {str(e)}")
            continue

    return {
        field: (field_filled.get(field, 0) / total_docs * 100)
        for field in field_counts.keys()
    } if total_docs > 0 else {}


def eval_overall_accuracy(json_results: List[str]) -> float:
    """
    Calculate percentage of fully complete documents.
    Excludes specified unimportant fields from completion check.
    """
    if not json_results:
        return 0.0

    fully_complete = 0
    total_docs = 0

    for json_str in json_results:
        try:
            data = json.loads(json_str)
            total_docs += 1

            def is_complete(d, prefix=""):
                for key, value in d.items():
                    field_path = f"{prefix}{key}" if not prefix else f"{prefix}.{key}"
                    if field_path in exclude_fields:
                        continue
                    if isinstance(value, dict):
                        if not is_complete(value, field_path):
                            return False
                    elif value is None or value == "":
                        return False
                return True

            if is_complete(data):
                fully_complete += 1
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON: {str(e)}")
            continue

    return (fully_complete / total_docs * 100) if total_docs > 0 else 0.0


def eval_extraction_results(json_results: List[str]) -> Dict[str, float]:
    """Calculate all evaluation metrics and return them in a dictionary"""
    try:
        metrics = {
            "average_fill_accuracy": eval_average_filling_accuracy(json_results),
            "field_completion_rates": calculate_field_completion_rates(json_results),
            "overall_accuracy": eval_overall_accuracy(json_results)
        }
        logger.info("Evaluation metrics calculated successfully")
        return metrics
    except Exception as e:
        logger.error(f"Failed to evaluate extraction results: {str(e)}")
        raise

def generate_jsons():
    directory = "test_files\\"
    md_paths = [os.path.join(directory, f) for f in os.listdir(directory) if f.endswith('.md')]
    print(f"Found {len(md_paths)} Markdown files")
    jsons = []
    for md_path in md_paths:
        with open(md_path, 'r', encoding="utf-8") as md_file:
            json = convertor.text_to_json(md_file.read())
            jsons.append(json)
            json_path = md_path.replace(".md", ".json")
            with open(json_path, 'w', encoding='utf-8') as file:
                file.write(json)
    return jsons

if __name__ == "__main__":
    # Define the directory path
    jsons = generate_jsons()
    metrics = eval_extraction_results(jsons)
    with open('completion_report.json', 'w', encoding='utf-8') as file:
        file.write(json.dumps(metrics, indent=2))


