import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import json
import io # To handle in-memory CSV data for insights

# --- Configuration ---
# Set your Gemini API Key here. Get one from https://makersuite.google.com/
# For security, consider using Streamlit Secrets for deployment:
# st.secrets["GEMINI_API_KEY"]
GEMINI_API_KEY = "YOUR_GEMINI_API_KEY" # Replace with your actual key

# --- Page Configuration ---
st.set_page_config(
    page_title="Interactive Media Intelligence Dashboard",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Custom Functions ---

def normalize_column_name(name):
    """Normalizes column names by converting to lowercase and removing non-alphanumeric characters."""
    return name.lower().replace(' ', '').replace('-', '').replace('_', '')

def clean_data(df):
    """
    Cleans the input DataFrame:
    - Converts 'date' column to datetime.
    - Fills missing 'engagements' with 0.
    - Normalizes all column names.
    - Filters out rows with invalid dates.
    """
    st.subheader("2. Data Cleaning Summary")
    st.markdown("""
    - 'Date' column converted to datetime objects. Invalid dates were filtered out.
    - Missing 'Engagements' values filled with 0.
    - Column names normalized (e.g., 'Media Type' became 'mediatype').
    """)

    original_rows = len(df)
    st.info(f"Original number of rows: {original_rows}")

    # Normalize column names
    df.columns = [normalize_column_name(col) for col in df.columns]

    # Ensure all required columns are present
    expected_columns = ['date', 'platform', 'sentiment', 'location', 'engagements', 'mediatype']
    missing_columns = [col for col in expected_columns if col not in df.columns]
    if missing_columns:
        st.error(f"Error: Missing required columns in CSV: {', '.join(missing_columns)}. Please ensure your CSV has 'Date', 'Platform', 'Sentiment', 'Location', 'Engagements', 'Media Type' columns.")
        st.stop() # Stop execution if critical columns are missing

    # Convert 'date' to datetime, handling errors
    df['date'] = pd.to_datetime(df['date'], errors='coerce')
    df.dropna(subset=['date'], inplace=True) # Drop rows where date conversion failed
    rows_after_date_clean = len(df)
    if rows_after_date_clean < original_rows:
        st.warning(f"Removed {original_rows - rows_after_date_clean} rows due to invalid 'Date' formats.")

    # Fill missing 'engagements' with 0 and convert to integer
    df['engagements'] = pd.to_numeric(df['engagements'], errors='coerce').fillna(0).astype(int)

    st.success(f"Successfully processed {len(df)} rows of data after cleaning.")
    return df

def get_gemini_insight(prompt_text):
    """Fetches insights from the Gemini API."""
    if not GEMINI_API_KEY or GEMINI_API_KEY == "YOUR_GEMINI_API_KEY":
        return "Gemini API key is not configured. Please set your API key to generate insights."

    headers = {
        'Content-Type': 'application/json'
    }
    payload = {
        "contents": [
            {
                "role": "user",
                "parts": [
                    {"text": prompt_text}
                ]
            }
        ]
    }
    api_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}"

    try:
        response = requests.post(api_url, headers=headers, data=json.dumps(payload))
        response.raise_for_status() # Raise an exception for HTTP errors
        result = response.json()

        if result and result.get('candidates'):
            first_candidate = result['candidates'][0]
            if first_candidate.get('content') and first_candidate['content'].get('parts'):
                return first_candidate['content']['parts'][0]['text']
        return "Could not generate insights for this chart."
    except requests.exceptions.RequestException as e:
        return f"Error calling Gemini API: {e}. Check your API key and network."
    except Exception as e:
        return f"An unexpected error occurred: {e}"

# --- Streamlit App ---

st.title("Interactive Media Intelligence Dashboard")
st.markdown("Gain insights from your media data with interactive charts.")

st.markdown("""
<style>
    .stApp {
        background-color: #e0f2fe; /* light blue-50 */
        font-family: 'Inter', sans-serif;
        color: #333;
    }
    .stFileUploader label {
        color: #4338ca; /* indigo-700 */
    }
    .stButton>button {
        background-color: #4f46e5; /* indigo-600 */
        color: white;
        font-weight: bold;
        border-radius: 0.5rem; /* rounded-lg */
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06); /* shadow-lg */
        transition: all 0.3s ease;
    }
    .stButton>button:hover {
        background-color: #4338ca; /* indigo-700 */
        transform: scale(1.05);
    }
    .stAlert {
        border-radius: 0.5rem;
    }
    .stExpander {
        border-radius: 0.5rem;
        border: 1px solid #bfdbfe; /* blue-200 */
        background-color: #eff6ff; /* blue-50 */
        padding: 1rem;
    }
</style>
""", unsafe_allow_html=True)

st.header("1. Upload Your CSV File")
st.markdown("""
Please upload a CSV file with the following columns:
`<code style="background-color:#e2e8f0; padding: 0.25rem 0.5rem; border-radius: 0.25rem; font-family: monospace;">Date</code>`,
`<code style="background-color:#e2e8f0; padding: 0.25rem 0.5rem; border-radius: 0.25rem; font-family: monospace;">Platform</code>`,
`<code style="background-color:#e2e8f0; padding: 0.25rem 0.5rem; border-radius: 0.25rem; font-family: monospace;">Sentiment</code>`,
`<code style="background-color:#e2e8f0; padding: 0.25rem 0.5rem; border-radius: 0.25rem; font-family: monospace;">Location</code>`,
`<code style="background-color:#e2e8f0; padding: 0.25rem 0.5rem; border-radius: 0.25rem; font-family: monospace;">Engagements</code>`,
`<code style="background-color:#e2e8f0; padding: 0.25rem 0.5rem; border-radius: 0.25rem; font-family: monospace;">Media Type</code>`.
""", unsafe_allow_html=True)


uploaded_file = st.file_uploader("", type=["csv"], key="csv_uploader")

df = None
if uploaded_file is not None:
    with st.spinner("Processing data..."):
        try:
            # Read CSV directly from uploaded file buffer
            df = pd.read_csv(uploaded_file)
            df = clean_data(df.copy()) # Pass a copy to avoid modifying original
            st.success("CSV file uploaded and data cleaned successfully!")

        except Exception as e:
            st.error(f"Error reading or cleaning CSV: {e}")
            df = None # Reset df to None on error

if df is not None and not df.empty:
    st.header("3. Interactive Charts")

    # Chart 1: Sentiment Breakdown (Pie Chart)
    st.subheader("Sentiment Breakdown")
    sentiment_counts = df['sentiment'].value_counts().reset_index()
    sentiment_counts.columns = ['Sentiment', 'Count']
    fig_sentiment = px.pie(
        sentiment_counts,
        values='Count',
        names='Sentiment',
        title='Sentiment Breakdown',
        hole=0.4,
        color_discrete_sequence=px.colors.qualitative.Pastel
    )
    fig_sentiment.update_layout(
        title_font_size=24,
        legend_orientation="h",
        legend_yanchor="bottom",
        legend_y=-0.1,
        legend_xanchor="center",
        legend_x=0.5,
        height=400
    )
    st.plotly_chart(fig_sentiment, use_container_width=True)

    with st.spinner("Generating insights for Sentiment Breakdown..."):
        prompt_sentiment = f"Given the following sentiment distribution from a media dataset: {sentiment_counts.to_dict('records')}. Provide 3 key insights about the overall sentiment. Focus on the most prevalent sentiments and any notable imbalances. Present insights as plain text, without any markdown formatting like bolding or bullet points. Use bullet points for readability. Also mention the dominant sentiment and why it is important"
        insights_sentiment = get_gemini_insight(prompt_sentiment)
        st.markdown(f"**Top 3 Insights (Sentiment Breakdown):**\n\n{insights_sentiment}")
        st.markdown("---")

    # Chart 2: Engagement Trend over time (Line Chart)
    st.subheader("Engagement Trend Over Time")
    engagement_trend = df.groupby(df['date'].dt.to_period('D'))['engagements'].sum().reset_index()
    engagement_trend['date'] = engagement_trend['date'].astype(str) # Convert Period to string for Plotly
    fig_engagement = px.line(
        engagement_trend,
        x='date',
        y='engagements',
        title='Engagement Trend Over Time',
        markers=True
    )
    fig_engagement.update_layout(
        title_font_size=24,
        xaxis_title="Date",
        yaxis_title="Total Engagements",
        xaxis_rangeslider_visible=True, # Add range slider
        height=400
    )
    st.plotly_chart(fig_engagement, use_container_width=True)

    with st.spinner("Generating insights for Engagement Trend..."):
        prompt_engagement = f"Analyze the following engagement data over time: {engagement_trend.to_dict('records')}. Describe the trend of engagements over the period. Are there any peaks, troughs, or consistent patterns? Give 3 key insights. Present insights as plain text, without any markdown formatting like bolding or bullet points. Use bullet points for readability. Highlight any significant spikes or drops in engagement"
        insights_engagement = get_gemini_insight(prompt_engagement)
        st.markdown(f"**Top 3 Insights (Engagement Trend):**\n\n{insights_engagement}")
        st.markdown("---")

    # Chart 3: Platform Engagements (Bar Chart)
    st.subheader("Platform Engagements")
    platform_engagements = df.groupby('platform')['engagements'].sum().reset_index()
    platform_engagements = platform_engagements.sort_values('engagements', ascending=False)
    fig_platform = px.bar(
        platform_engagements,
        x='platform',
        y='engagements',
        title='Platform Engagements',
        color='platform'
    )
    fig_platform.update_layout(
        title_font_size=24,
        xaxis_title="Platform",
        yaxis_title="Total Engagements",
        height=400
    )
    st.plotly_chart(fig_platform, use_container_width=True)

    with st.spinner("Generating insights for Platform Engagements..."):
        prompt_platform = f"Based on the total engagements per platform: {platform_engagements.to_dict('records')}. What are the top platforms driving engagements? Are there any platforms significantly underperforming? Provide 3 key insights. Present insights as plain text, without any markdown formatting like bolding or bullet points. Use bullet points for readability. Identify top performing platforms"
        insights_platform = get_gemini_insight(prompt_platform)
        st.markdown(f"**Top 3 Insights (Platform Engagements):**\n\n{insights_platform}")
        st.markdown("---")

    # Chart 4: Media Type Mix (Pie Chart)
    st.subheader("Media Type Mix")
    mediatype_counts = df['mediatype'].value_counts().reset_index()
    mediatype_counts.columns = ['MediaType', 'Count']
    fig_mediatype = px.pie(
        mediatype_counts,
        values='Count',
        names='MediaType',
        title='Media Type Mix',
        hole=0.4,
        color_discrete_sequence=px.colors.qualitative.Set2
    )
    fig_mediatype.update_layout(
        title_font_size=24,
        legend_orientation="h",
        legend_yanchor="bottom",
        legend_y=-0.1,
        legend_xanchor="center",
        legend_x=0.5,
        height=400
    )
    st.plotly_chart(fig_mediatype, use_container_width=True)

    with st.spinner("Generating insights for Media Type Mix..."):
        prompt_mediatype = f"Given the distribution of media types: {mediatype_counts.to_dict('records')}. What are the most common media types used? Is there a significant preference for certain types? Give 3 key insights. Present insights as plain text, without any markdown formatting like bolding or bullet points. Use bullet points for readability. Discuss the most prevalent media type"
        insights_mediatype = get_gemini_insight(prompt_mediatype)
        st.markdown(f"**Top 3 Insights (Media Type Mix):**\n\n{insights_mediatype}")
        st.markdown("---")

    # Chart 5: Top 5 Locations (Bar Chart)
    st.subheader("Top 5 Locations by Engagements")
    location_engagements = df.groupby('location')['engagements'].sum().reset_index()
    location_engagements = location_engagements.sort_values('engagements', ascending=False).head(5)
    fig_location = px.bar(
        location_engagements,
        x='location',
        y='engagements',
        title='Top 5 Locations by Engagements',
        color='location'
    )
    fig_location.update_layout(
        title_font_size=24,
        xaxis_title="Location",
        yaxis_title="Total Engagements",
        height=400
    )
    st.plotly_chart(fig_location, use_container_width=True)

    with st.spinner("Generating insights for Top 5 Locations..."):
        prompt_location = f"Here are the top 5 locations by engagements: {location_engagements.to_dict('records')}. What does this data tell us about geographical engagement? Are there specific regions that are highly active? Provide 3 key insights. Present insights as plain text, without any markdown formatting like bolding or bullet points. Use bullet points for readability. Point out the most engaged locations"
        insights_location = get_gemini_insight(prompt_location)
        st.markdown(f"**Top 3 Insights (Top 5 Locations):**\n\n{insights_location}")
        st.markdown("---")

st.markdown("""
<div style="background-color: #bfdbfe; padding: 1.5rem; border-radius: 0.75rem; text-align: center; margin-top: 2rem;">
    <h3 style="color: #1e3a8a; font-size: 1.5rem; font-weight: bold; margin-bottom: 0.5rem;">Exporting to PDF</h3>
    <p style="color: #1e3a8a;">
        For a complete PDF export of this dashboard, please use your browser's native "Print to PDF" functionality (usually found in your browser's menu or by pressing <kbd>Ctrl + P</kbd> / <kbd>Cmd + P</kbd>).
    </p>
</div>
""", unsafe_allow_html=True)
