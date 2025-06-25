# Art Deco Inventory Dashboard

A comprehensive inventory management dashboard with real-time data visualization and AI-powered insights.

## Features

- Real-time inventory tracking
- Interactive data visualizations
- Product performance analysis
- Time-based trend analysis
- AI-powered insights using Google's Gemini

## Setup

1. Install the required dependencies:
```bash
pip install -r requirements.txt
```

2. Set up your Gemini API key:
   - Get your API key from [Google AI Studio](https://makersuite.google.com/app/apikey)
   - Create a `.env` file in the project root
   - Add your API key to the `.env` file:
   ```
   GEMINI_API_KEY=your_gemini_api_key_here
   ```

3. Initialize the database:
```bash
python realtime_data_gen.py --create
```

4. Start the real-time data generator:
```bash
python start_realtime_dashboard.py
```

5. Access the dashboard at `http://localhost:8050`

## Using AI Insights

The dashboard includes an AI-powered insights feature that allows you to ask questions about your inventory data. To use this feature:

1. Navigate to the "AI Insights" tab
2. Enter your question in the text area
3. Click "Get Insights" to receive an AI-generated response

Example questions you can ask:
- What were the busiest days for inventory movement?
- Which category had the highest total quantity of movements?
- What is the overall trend in inventory changes?
- What are the peak hours for inventory movements?
- Which products show the most consistent movement patterns?
- What is the average daily inventory change?
- Which categories show the most growth in recent days?

## Data Privacy

- All data is stored locally in the SQLite database
- The Gemini API key is stored securely in your local `.env` file
- No data is sent to external servers except for the specific questions you ask through the AI Insights feature

## Contributing

Feel free to submit issues and enhancement requests! 