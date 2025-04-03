import json
import os
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)

exclude_fields = {"address.entrance", "address.poBox"}

def compare_json_fields(extracted: Dict, ground_truth: Dict, prefix: str = "") -> Dict[str, bool]:
    comparison_results = {}

    def compare_fields(extracted_dict, gt_dict, current_prefix=""):
        for key, gt_value in gt_dict.items():
            field_path = f"{current_prefix}{key}" if not current_prefix else f"{current_prefix}.{key}"
            if field_path in exclude_fields:
                continue
            if key not in extracted_dict:
                comparison_results[field_path] = False
                continue
            extracted_value = extracted_dict[key]
            if isinstance(gt_value, dict):
                compare_fields(extracted_value, gt_value, field_path)
            else:
                if (extracted_value is None or extracted_value == "") and (gt_value is None or gt_value == ""):
                    comparison_results[field_path] = True
                else:
                    comparison_results[field_path] = extracted_value == gt_value

    compare_fields(extracted, ground_truth)
    return comparison_results

def calculate_field_correctness(extracted_jsons: List[Dict], ground_truth_jsons: List[Dict]) -> Dict[str, float]:
    if not extracted_jsons or not ground_truth_jsons or len(extracted_jsons) != len(ground_truth_jsons):
        return {}

    field_correct = {}
    field_counts = {}
    total_docs = 0

    for extracted_data, gt_data in zip(extracted_jsons, ground_truth_jsons):  # No json.loads() needed
        total_docs += 1
        comparison = compare_json_fields(extracted_data, gt_data)
        for field_path, is_correct in comparison.items():
            field_counts[field_path] = field_counts.get(field_path, 0) + 1
            if is_correct:
                field_correct[field_path] = field_correct.get(field_path, 0) + 1

    return {
        field: (field_correct.get(field, 0) / field_counts[field] * 100)
        for field in field_counts.keys()
    } if total_docs > 0 else {}

def calculate_document_correctness(extracted_jsons: List[Dict], ground_truth_jsons: List[Dict]) -> float:
    if not extracted_jsons or not ground_truth_jsons or len(extracted_jsons) != len(ground_truth_jsons):
        return 0.0

    fully_correct = 0
    total_docs = 0

    for extracted_data, gt_data in zip(extracted_jsons, ground_truth_jsons):  # No json.loads() needed
        total_docs += 1
        comparison = compare_json_fields(extracted_data, gt_data)
        if all(comparison.values()):
            fully_correct += 1

    return (fully_correct / total_docs * 100) if total_docs > 0 else 0.0

def calculate_average_accuracy_per_document(extracted_jsons: List[Dict], ground_truth_jsons: List[Dict]) -> float:
    if not extracted_jsons or not ground_truth_jsons or len(extracted_jsons) != len(ground_truth_jsons):
        return 0.0

    accuracies = []
    total_docs = 0

    for extracted_data, gt_data in zip(extracted_jsons, ground_truth_jsons):  # No json.loads() needed
        total_docs += 1
        comparison = compare_json_fields(extracted_data, gt_data)
        total_fields = len(comparison)
        correct_fields = sum(1 for result in comparison.values() if result)
        accuracy = (correct_fields / total_fields * 100) if total_fields > 0 else 0.0
        accuracies.append(accuracy)

    return sum(accuracies) / len(accuracies) if accuracies else 0.0

def evaluate_with_ground_truth(extracted_jsons: List[Dict], ground_truth_jsons: List[Dict]) -> Dict:
    try:
        metrics = {
            "field_correctness_rates": calculate_field_correctness(extracted_jsons, ground_truth_jsons),
            "document_correctness": calculate_document_correctness(extracted_jsons, ground_truth_jsons),
            "average_accuracy_per_document": calculate_average_accuracy_per_document(extracted_jsons, ground_truth_jsons)
        }
        logger.info("Ground truth evaluation metrics calculated successfully")
        return metrics
    except Exception as e:
        logger.error(f"Failed to evaluate with ground truth: {str(e)}")
        raise

if __name__ == "__main__":
    results_str = ["283_ex1.json", "283_ex2.json", "283_ex3.json"]
    gt_paths = ["283_gt1.json", "283_gt2.json", "283_gt3.json"]

    # Load JSON files safely
    results_jsons = []
    for s in results_str:
        with open(s, "r", encoding="utf-8") as f:
            results_jsons.append(json.load(f))  # json.load() returns a dict

    gt_jsons = []
    for s in gt_paths:
        with open(s, "r", encoding="utf-8") as f:
            gt_jsons.append(json.load(f))  # json.load() returns a dict

    # Ensure evaluate_with_ground_truth handles dicts correctly
    metrics = evaluate_with_ground_truth(results_jsons, gt_jsons)
    with open('correctness_report.json', 'w', encoding='utf-8') as file:
        file.write(json.dumps(metrics, indent=2))
