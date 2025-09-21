import os
import google.generativeai as genai
from dotenv import load_dotenv

def test_gemini_connection():
    # Load environment variables from .env file
    load_dotenv()
    
    # Get API key from environment
    api_key = os.getenv("GEMINI_API_KEY")
    
    if not api_key:
        print("❌ Error: GEMINI_API_KEY not found in environment variables")
        print("Please set your API key in the .env file:")
        print("GEMINI_API_KEY=your-api-key-here")
        print("You can get an API key from: https://aistudio.google.com/app/apikey")
        return False
    
    print(f"✅ Found GEMINI_API_KEY (first 8 chars: {api_key[:8]}...)")
    
    try:
        # Configure the API key
        genai.configure(api_key=api_key)
        
        # Initialize the model
        model = genai.GenerativeModel('gemini-2.0-flash')
        
        # Make a test API call
        response = model.generate_content("Say 'API test successful'")
        
        if not response.text:
            raise Exception("No response text received from Gemini API")
            
        print(f"✅ API Response: {response.text.strip()}")
        print("\n🎉 Google Gemini API connection successful!")
        return True
        
    except Exception as e:
        print(f"❌ Error connecting to Google Gemini API: {str(e)}")
        print("\nTroubleshooting tips:")
        print("1. Make sure your API key is valid and has sufficient credits")
        print("2. Check if there are any typos in your API key")
        print("3. Ensure your internet connection is working")
        print("4. Try using a different network (some networks block API calls)")
        print("5. Check if the Gemini API is available in your region")
        return False

if __name__ == "__main__":
    test_gemini_connection()
