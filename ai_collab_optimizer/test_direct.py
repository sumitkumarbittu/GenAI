import os
import google.generativeai as genai
from dotenv import load_dotenv

def test_direct():
    print("=== Testing Google Gemini API Connection ===")
    
    # Load .env file
    env_path = os.path.join(os.path.dirname(__file__), '.env')
    print(f"Looking for .env file at: {env_path}")
    
    if not os.path.exists(env_path):
        print("❌ .env file not found")
        return False
        
    print("✅ Found .env file")
    
    # Load environment variables
    load_dotenv(env_path)
    
    # Get API key
    api_key = os.getenv("GEMINI_API_KEY")
    
    if not api_key:
        print("❌ GEMINI_API_KEY not found in .env file")
        print("Please add your Gemini API key to the .env file:")
        print("GEMINI_API_KEY=your-api-key-here")
        print("You can get an API key from: https://aistudio.google.com/app/apikey")
        return False
        
    print(f"✅ Found GEMINI_API_KEY (first 8 chars: {api_key[:8]}...)")
    
    # Test API call
    try:
        # Configure the API key
        genai.configure(api_key=api_key)
        
        # Initialize the model
        model = genai.GenerativeModel('gemini-2.0-flash')
        
        print("\nSending test request to Google Gemini API...")
        response = model.generate_content(
            "You are a helpful assistant. Say 'API test successful' and nothing else."
        )
        
        if not response.text:
            raise Exception("No response text received from Gemini API")
            
        print(f"✅ API Response: {response.text.strip()}")
        print("\n🎉 Google Gemini API connection successful!")
        return True
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        print("\nTroubleshooting steps:")
        print("1. Check your internet connection")
        print("2. Verify your API key is correct")
        print("3. Make sure your Google AI Studio account has access")
        print("4. Check if the Gemini API is available in your region")
        print("5. Ensure you have sufficient quota in Google AI Studio")
        
        return False

if __name__ == "__main__":
    test_direct()
