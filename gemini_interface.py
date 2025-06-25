import google.generativeai as genai
from gemini_graph_context import get_graph_context_for_gemini
from config import DATABASE_PATH  # Ensure live DB path is available

def setup_gemini(api_key):
    """
    Set up Gemini with the provided API key
    """
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-pro')
    return model

def get_inventory_insights(question, api_key):
    """
    Get insights about inventory data using Gemini
    """
    try:
        # Get the graph context
        context = get_graph_context_for_gemini()
        
        # Set up Gemini
        model = setup_gemini(api_key)
        
        # Create the prompt
        prompt = f"""
        Here is the context about our inventory data:

        {context}

        Based on this data, please answer the following question:
        {question}

        Please provide a clear and concise answer, focusing on the most relevant insights from the data.
        """
        
        # Generate response
        response = model.generate_content(prompt)
        
        return response.text
        
    except Exception as e:
        return f"Error getting insights: {str(e)}"

def main():
    """
    Example usage of the Gemini interface
    """
    # Replace with your actual API key
    API_KEY = "YOUR_GEMINI_API_KEY"
    
    # Example questions
    questions = [
        "What were the busiest days for inventory movement?",
        "Which category had the highest total quantity of movements?",
        "What is the overall trend in inventory changes?",
        "What are the peak hours for inventory movements?"
    ]
    
    for question in questions:
        print(f"\nQuestion: {question}")
        answer = get_inventory_insights(question, API_KEY)
        print(f"Answer: {answer}")

if __name__ == "__main__":
    main() 