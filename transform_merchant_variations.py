import json
from pathlib import Path
import logging

# Configure basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def transform_merchant_variations():
    """
    Reads the merchant_variations.json file, transforms its structure,
    and writes the new structure back to the same file.
    Expected input format: [{"base_name": "X", "variations": ["Y", "Z"], "count": N}, ...]
    Expected output format: {"Y": "X", "Z": "X", ...}
    """
    file_path_str = "transaction_analysis_results/merchant_variations.json"
    file_path = Path(file_path_str)

    if not file_path.exists():
        logging.error(f"File not found: {file_path}")
        return

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            current_data = json.load(f)
        logging.info(f"Successfully read {file_path}")
    except json.JSONDecodeError as e:
        logging.error(f"Error decoding JSON from {file_path}: {e}")
        return
    except Exception as e:
        logging.error(f"Error reading {file_path}: {e}")
        return

    if not isinstance(current_data, list):
        logging.error(f"Expected a list in {file_path}, but got {type(current_data)}. Transformation aborted.")
        return

    transformed_data = {}
    items_processed = 0
    variations_mapped = 0

    for item in current_data:
        if isinstance(item, dict) and "base_name" in item and "variations" in item:
            base_name = item["base_name"]
            variations = item["variations"]
            if isinstance(variations, list):
                for variation in variations:
                    if isinstance(variation, str):
                        transformed_data[variation] = base_name
                        variations_mapped += 1
                    else:
                        logging.warning(f"Skipping non-string variation: {variation} under base_name: {base_name}")
            else:
                logging.warning(f"Skipping item with non-list variations for base_name: {base_name}")
            items_processed +=1
        else:
            logging.warning(f"Skipping malformed item: {item}")

    logging.info(f"Processed {items_processed} items from the input array.")
    logging.info(f"Mapped {variations_mapped} variations to the new dictionary format.")

    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(transformed_data, f, indent=2) # Using indent=2 for readability
        logging.info(f"Successfully transformed and wrote back to {file_path}")
    except Exception as e:
        logging.error(f"Error writing transformed data to {file_path}: {e}")

if __name__ == "__main__":
    transform_merchant_variations()
