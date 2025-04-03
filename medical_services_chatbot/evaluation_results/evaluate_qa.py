import json
import os
import pandas as pd
import numpy as np
from sentence_transformers import SentenceTransformer
from transformers import pipeline
from sklearn.metrics import confusion_matrix, precision_score, recall_score, accuracy_score
import seaborn as sns
import matplotlib.pyplot as plt
from typing import List, Dict, Any, Tuple
import torch
from tqdm import tqdm

# Get the base directory (where the script is located)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Set random seed for reproducibility
np.random.seed(42)
torch.manual_seed(42)

class EmbeddingModel:
    def __init__(self, name: str, model_type: str = 'sentence_transformers'):
        """Initialize an embedding model."""
        self.name = name
        self.model_type = model_type
        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        
        if model_type == 'sentence_transformers':
            self.model = SentenceTransformer(name)
            self.model.to(self.device)
        elif model_type == 'transformers':
            self.model = pipeline(
                "feature-extraction",
                model=name,
                device=0 if self.device == 'cuda' else -1  # Use -1 for CPU
            )
    
    def encode(self, text: str) -> np.ndarray:
        """Generate embedding for the given text."""
        if self.model_type == 'sentence_transformers':
            return self.model.encode(text, convert_to_numpy=True)
        else:  # transformers
            # Get the embedding from the last hidden state's [CLS] token
            embedding = self.model(text, return_tensors="pt")[0][0].detach().cpu().numpy()
            return embedding

def load_test_data(test_dir: str) -> List[Dict[str, Any]]:
    """Load all test data from JSON files in the test directory."""
    test_data = []
    test_dir_path = os.path.join(BASE_DIR, test_dir)
    
    if not os.path.exists(test_dir_path):
        raise FileNotFoundError(f"Test data directory not found at: {test_dir_path}")
    
    for file in os.listdir(test_dir_path):
        if file.endswith('_test.json'):
            print(f"Loading {file}...")
            with open(os.path.join(test_dir_path, file), 'r', encoding='utf-8') as f:
                test_data.extend(json.load(f)['test_cases'])
    return test_data

def create_evaluation_df(test_data: List[Dict[str, Any]], qa_service, models: Dict[str, EmbeddingModel]) -> pd.DataFrame:
    """Create a DataFrame with all evaluation data."""
    rows = []
    
    for test_case in tqdm(test_data, desc="Processing test cases"):
        user_info = test_case['user_info']
        for conv in test_case['conversations']:
            # Get generated answer
            generated_answer = qa_service.get_answer(user_info, conv['question'])
            
            # Generate embeddings for each model
            embeddings = {}
            similarities = {}
            is_correct = {}
            
            for model_name, model in models.items():
                # Generate embeddings
                ground_truth_embedding = model.encode(conv['answer'])
                generated_embedding = model.encode(generated_answer)
                
                # Calculate cosine similarity
                cosine_sim = np.dot(ground_truth_embedding, generated_embedding) / (
                    np.linalg.norm(ground_truth_embedding) * np.linalg.norm(generated_embedding)
                )
                
                embeddings[model_name] = {
                    'ground_truth': ground_truth_embedding,
                    'generated': generated_embedding
                }
                similarities[model_name] = cosine_sim
                is_correct[model_name] = cosine_sim >= 0.85  # Threshold for considering answer correct
            
            # Create row
            row = {
                'id_number': user_info['id_number'],
                'gender': user_info['gender'],
                'age': user_info['age'],
                'hmo_name': user_info['hmo_name'],
                'membership_tier': user_info['membership_tier'],
                'question': conv['question'],
                'ground_truth_answer': conv['answer'],
                'generated_answer': generated_answer,
                **{f'embedding_{model_name}': emb for model_name, emb in embeddings.items()},
                **{f'similarity_{model_name}': sim for model_name, sim in similarities.items()},
                **{f'is_correct_{model_name}': corr for model_name, corr in is_correct.items()}
            }
            rows.append(row)
    
    return pd.DataFrame(rows)

def calculate_metrics(df: pd.DataFrame, models: Dict[str, EmbeddingModel]) -> Dict[str, Dict[str, float]]:
    """Calculate various metrics for each model."""
    metrics = {}
    
    for model_name in models.keys():
        model_metrics = {
            'overall_accuracy': accuracy_score(df[f'is_correct_{model_name}'], [True] * len(df)),
            'precision': precision_score(df[f'is_correct_{model_name}'], [True] * len(df)),
            'recall': recall_score(df[f'is_correct_{model_name}'], [True] * len(df))
        }
        
        # Per service metrics
        for service in df['question'].unique():
            service_df = df[df['question'] == service]
            model_metrics[f'accuracy_{service}'] = accuracy_score(
                service_df[f'is_correct_{model_name}'], [True] * len(service_df)
            )
        
        # Per HMO metrics
        for hmo in df['hmo_name'].unique():
            hmo_df = df[df['hmo_name'] == hmo]
            model_metrics[f'accuracy_{hmo}'] = accuracy_score(
                hmo_df[f'is_correct_{model_name}'], [True] * len(hmo_df)
            )
        
        # Per tier metrics
        for tier in df['membership_tier'].unique():
            tier_df = df[df['membership_tier'] == tier]
            model_metrics[f'accuracy_{tier}'] = accuracy_score(
                tier_df[f'is_correct_{model_name}'], [True] * len(tier_df)
            )
        
        metrics[model_name] = model_metrics
    
    return metrics

def create_visualizations(df: pd.DataFrame, models: Dict[str, EmbeddingModel], output_dir: str):
    """Create and save various visualizations for each model."""
    output_dir_path = os.path.join(BASE_DIR, output_dir)
    os.makedirs(output_dir_path, exist_ok=True)
    
    for model_name in models.keys():
        model_dir = os.path.join(output_dir_path, model_name)
        os.makedirs(model_dir, exist_ok=True)
        
        # 1. Overall accuracy by service
        plt.figure(figsize=(12, 6))
        service_acc = df.groupby('question')[f'is_correct_{model_name}'].mean()
        sns.barplot(x=service_acc.index, y=service_acc.values)
        plt.xticks(rotation=45)
        plt.title(f'Accuracy by Service - {model_name}')
        plt.tight_layout()
        plt.savefig(os.path.join(model_dir, 'accuracy_by_service.png'))
        plt.close()
        
        # 2. Accuracy by HMO
        plt.figure(figsize=(10, 6))
        hmo_acc = df.groupby('hmo_name')[f'is_correct_{model_name}'].mean()
        sns.barplot(x=hmo_acc.index, y=hmo_acc.values)
        plt.title(f'Accuracy by HMO - {model_name}')
        plt.tight_layout()
        plt.savefig(os.path.join(model_dir, 'accuracy_by_hmo.png'))
        plt.close()
        
        # 3. Accuracy by tier
        plt.figure(figsize=(10, 6))
        tier_acc = df.groupby('membership_tier')[f'is_correct_{model_name}'].mean()
        sns.barplot(x=tier_acc.index, y=tier_acc.values)
        plt.title(f'Accuracy by Membership Tier - {model_name}')
        plt.tight_layout()
        plt.savefig(os.path.join(model_dir, 'accuracy_by_tier.png'))
        plt.close()
        
        # 4. Confusion matrix
        plt.figure(figsize=(8, 6))
        cm = confusion_matrix(df[f'is_correct_{model_name}'], [True] * len(df))
        sns.heatmap(cm, annot=True, fmt='d', cmap='Blues')
        plt.title(f'Confusion Matrix - {model_name}')
        plt.xlabel('Predicted')
        plt.ylabel('Actual')
        plt.tight_layout()
        plt.savefig(os.path.join(model_dir, 'confusion_matrix.png'))
        plt.close()
    
    # 5. Model comparison plot
    plt.figure(figsize=(12, 6))
    model_accuracies = [
        df[f'is_correct_{model_name}'].mean()
        for model_name in models.keys()
    ]
    sns.barplot(x=list(models.keys()), y=model_accuracies)
    plt.xticks(rotation=45)
    plt.title('Overall Accuracy by Model')
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir_path, 'model_comparison.png'))
    plt.close()

def generate_report(metrics: Dict[str, Dict[str, float]], output_dir: str):
    """Generate a comprehensive report comparing all models."""
    output_dir_path = os.path.join(BASE_DIR, output_dir)
    report = "QA Service Evaluation Report - Model Comparison\n==========================================\n\n"
    
    # Overall metrics comparison
    report += "Overall Metrics by Model:\n----------------------\n"
    for model_name, model_metrics in metrics.items():
        report += f"\n{model_name}:\n"
        report += f"Accuracy: {model_metrics['overall_accuracy']:.2%}\n"
        report += f"Precision: {model_metrics['precision']:.2%}\n"
        report += f"Recall: {model_metrics['recall']:.2%}\n"
    
    # Per service comparison
    report += "\nAccuracy by Service:\n------------------\n"
    services = set()
    for model_metrics in metrics.values():
        services.update(key.replace('accuracy_', '') for key in model_metrics.keys()
                      if key.startswith('accuracy_') and not any(x in key for x in ['hmo', 'tier']))
    
    for service in services:
        report += f"\n{service}:\n"
        for model_name, model_metrics in metrics.items():
            report += f"{model_name}: {model_metrics.get(f'accuracy_{service}', 'N/A'):.2%}\n"
    
    # Per HMO comparison
    report += "\nAccuracy by HMO:\n--------------\n"
    hmos = set()
    for model_metrics in metrics.values():
        hmos.update(key.replace('accuracy_', '') for key in model_metrics.keys()
                   if key.startswith('accuracy_') and 'hmo' in key)
    
    for hmo in hmos:
        report += f"\n{hmo}:\n"
        for model_name, model_metrics in metrics.items():
            report += f"{model_name}: {model_metrics.get(f'accuracy_{hmo}', 'N/A'):.2%}\n"
    
    # Per tier comparison
    report += "\nAccuracy by Tier:\n---------------\n"
    tiers = set()
    for model_metrics in metrics.values():
        tiers.update(key.replace('accuracy_', '') for key in model_metrics.keys()
                    if key.startswith('accuracy_') and 'tier' in key)
    
    for tier in tiers:
        report += f"\n{tier}:\n"
        for model_name, model_metrics in metrics.items():
            report += f"{model_name}: {model_metrics.get(f'accuracy_{tier}', 'N/A'):.2%}\n"
    
    with open(os.path.join(output_dir_path, 'evaluation_report.txt'), 'w', encoding='utf-8') as f:
        f.write(report)

def main():
    # Define models to test
    models = [
        ('all-MiniLM-L6-v2', 'sentence_transformers'),
        # ('all-mpnet-base-v2', 'sentence_transformers'),
        # ('ncbi/MedCPT-Query-Encoder', 'transformers'),
        # ('microsoft/BiomedNLP-PubMedBERT-base-uncased-abstract', 'transformers'),
        # ('emilyalsentzer/Bio_ClinicalBERT', 'transformers')
    ]
    
    # Initialize models
    embedding_models = {
        name: EmbeddingModel(name, model_type)
        for name, model_type in models
    }
    
    # Load test data
    test_data = load_test_data('../test_data')[:2]
    print(f"Loaded {len(test_data)} test cases")
    
    # Initialize QA service
    from qa_service import QAService
    qa_service = QAService()
    
    # Create evaluation DataFrame
    df = create_evaluation_df(test_data, qa_service, embedding_models)
    print(f"Created DataFrame with {len(df)} rows")
    
    # Calculate metrics
    metrics = calculate_metrics(df, embedding_models)
    
    # Display overall metrics for each model
    for model_name, model_metrics in metrics.items():
        print(f"\n{model_name}:")
        print(f"Accuracy: {model_metrics['overall_accuracy']:.2%}")
        print(f"Precision: {model_metrics['precision']:.2%}")
        print(f"Recall: {model_metrics['recall']:.2%}")
    
    # Create visualizations
    create_visualizations(df, embedding_models, '')
    
    # Generate report
    generate_report(metrics, '')
    
    # Save DataFrame
    df.to_pickle(os.path.join(BASE_DIR, 'evaluation_results.pkl'))
    print("Results saved to evaluation_results.pkl")

if __name__ == "__main__":
    main() 