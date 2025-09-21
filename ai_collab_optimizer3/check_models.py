import os
import google.generativeai as genai
from dotenv import load_dotenv

def list_available_models():
    # Load environment variables
    load_dotenv()
    
    # Get API key
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("❌ GEMINI_API_KEY not found in environment variables")
        return
    
    try:
        # Configure the API key
        genai.configure(api_key=api_key)
        
        # List available models
        print("\nFetching available models...")
        models = genai.list_models()
        
        if not models:
            print("❌ No models found. Check your API key and permissions.")
            return
            
        print("\nAvailable models:")
        for model in models:
            print(f"- {model.name} (Supports: {', '.join(method for method in model.supported_generation_methods)})")
            
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        print("\nTroubleshooting tips:")
        print("1. Check your internet connection")
        print("2. Verify your API key is correct")
        print("3. Make sure your Google AI Studio account has access to the Gemini API")
        print("4. Check if the Gemini API is available in your region")

if __name__ == "__main__":
    list_available_models()
