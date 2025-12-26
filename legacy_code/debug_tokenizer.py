from transformers import AutoTokenizer, AutoModelForSequenceClassification

try:
    print("Loading tokenizer...")
    tokenizer = AutoTokenizer.from_pretrained("microsoft/mdeberta-v3-base")
    print("Tokenizer loaded.")
    
    print("Loading model...")
    model = AutoModelForSequenceClassification.from_pretrained("microsoft/mdeberta-v3-base")
    print("Model loaded.")
except Exception as e:
    import traceback
    traceback.print_exc()
