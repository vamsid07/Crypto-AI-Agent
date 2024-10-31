import os
from typing import Dict, List
from dotenv import load_dotenv
import requests
from requests.exceptions import RequestException
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
from together import Together
import logging
from language_handler import LanguageHandler  # Ensure this module is available

# Setup environment and logging
load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize global components
together_client = Together(api_key=os.getenv("TOGETHER_API_KEY"))
embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
language_handler = LanguageHandler()  # Ensure no api_key is needed here
crypto_metadata = []
index = None

def validate_env_vars() -> None:
    """Validate that required environment variables are set."""
    required_vars = ["TOGETHER_API_KEY", "COINGECKO_API_KEY", "SARVAM_API_KEY"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    if missing_vars:
        raise EnvironmentError(f"Missing required environment variables: {', '.join(missing_vars)}")

def fetch_crypto_data() -> List[Dict]:
    """Fetch cryptocurrency data from CoinGecko API."""
    url = "https://api.coingecko.com/api/v3/coins/markets"
    params = {
        "vs_currency": "usd",
        "order": "market_cap_desc",
        "per_page": 100,
        "page": 1,
        "sparkline": False,
        "price_change_percentage": "24h"
    }
    headers = {"accept": "application/json", "x-cg-demo-api-key": os.getenv("COINGECKO_API_KEY")}
    
    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        return response.json()
    except RequestException as e:
        logger.error(f"Error fetching crypto data: {str(e)}")
        raise

def refresh_crypto_data() -> None:
    """Refresh cryptocurrency data and update the FAISS index."""
    global crypto_metadata, index
    try:
        crypto_data = fetch_crypto_data()
        crypto_texts = []
        crypto_metadata = []
        
        for crypto in crypto_data:
            text_representation = (
                f"{crypto['name']} ({crypto['symbol'].upper()}) "
                f"is a cryptocurrency with current price ${crypto['current_price']:.2f} USD. "
                f"Market cap rank: {crypto['market_cap_rank']}"
            )
            crypto_texts.append(text_representation)
            crypto_metadata.append({
                "id": crypto["id"],
                "name": crypto["name"],
                "symbol": crypto["symbol"].upper(),
                "current_price": crypto["current_price"],
                "market_cap_rank": crypto["market_cap_rank"],
                "price_change_24h": crypto.get("price_change_24h", 0),
                "market_cap": crypto.get("market_cap", 0),
                "total_volume": crypto.get("total_volume", 0),
                "high_24h": crypto.get("high_24h", 0),
                "low_24h": crypto.get("low_24h", 0),
                "price_change_percentage_24h": crypto.get("price_change_percentage_24h", 0)
            })
        
        embeddings = embedding_model.encode(crypto_texts)
        embeddings = np.array(embeddings).astype('float32')
        dimension = embeddings.shape[1]
        index = faiss.IndexFlatL2(dimension)
        index.add(embeddings)
        
        logger.info(f"Successfully refreshed data for {len(crypto_data)} cryptocurrencies")
    except Exception as e:
        logger.error(f"Error refreshing crypto data: {str(e)}")
        raise

def format_response(original_query: str, translated_query: str, crypto_data: Dict, source_lang: str) -> str:
    """Format the cryptocurrency data into a natural language response."""
    context = f"""
    Cryptocurrency Information:
    - Name: {crypto_data['name']} ({crypto_data['symbol']})
    - Current Price: ${crypto_data['current_price']:,.2f}
    - 24h Price Change: ${crypto_data['price_change_24h']:,.2f} ({crypto_data['price_change_percentage_24h']:.2f}%)
    - 24h High: ${crypto_data['high_24h']:,.2f}
    - 24h Low: ${crypto_data['low_24h']:,.2f}
    - Market Cap Rank: #{crypto_data['market_cap_rank']}
    - Market Cap: ${crypto_data['market_cap']:,.2f}
    - 24h Trading Volume: ${crypto_data['total_volume']:,.2f}
    """

    prompt = f"""A user asked about cryptocurrency in {language_handler.supported_languages[source_lang]}: 
    Translated question: "{translated_query}"
    
    Using the following cryptocurrency data, provide a natural, informative response in English that directly 
    answers their question and includes relevant context. Keep the response concise but informative.
    Include the price change percentage if it's significant.

    {context}

    Generate a response in a conversational tone in English:"""
    try:
        response = together_client.chat.completions.create(
            model="meta-llama/Meta-Llama-3.1-8B-Instruct-lora",
            messages=[
                {"role": "system", "content": "You are a helpful cryptocurrency information assistant. Provide clear, concise answers about cryptocurrency prices and market data in English, regardless of the input language."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=150,
            temperature=0.7,
            top_p=0.9,
            repetition_penalty=1.1
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"Error formatting response: {str(e)}")
        return f"{crypto_data['name']} ({crypto_data['symbol']}) is currently trading at ${crypto_data['current_price']:,.2f} USD."

async def query_crypto_price(user_query: str, source_lang: str) -> str:
    """Query cryptocurrency prices based on user input and return a natural language response."""
    try:
        # Translate the query to English if it's in another language
        translated_query = await language_handler.translate_to_english(user_query, source_lang)
        
        # Process translated query with LLM for entity extraction
        response = together_client.chat.completions.create(
            model="meta-llama/Meta-Llama-3.1-8B-Instruct-lora",
            messages=[
                {"role": "system", "content": "Extract the cryptocurrency name or symbol from the user's query."},
                {"role": "user", "content": translated_query}
            ],
            max_tokens=50,
            temperature=0.3,
            top_p=0.9,
            repetition_penalty=1.1
        )
        
        processed_query = response.choices[0].message.content
        
        # Embed the query and search in FAISS index
        query_embedding = embedding_model.encode([processed_query])
        query_embedding = np.array(query_embedding).astype('float32')
        
        if index is None:
            raise ValueError("FAISS index not initialized")
            
        distances, indices = index.search(query_embedding, k=1)
        matched_index = indices[0][0]
        crypto_data = crypto_metadata[matched_index]
        
        formatted_response = format_response(
            original_query=user_query,
            translated_query=translated_query,
            crypto_data=crypto_data,
            source_lang=source_lang
        )
        
        return formatted_response
        
    except Exception as e:
        logger.error(f"Error processing query '{user_query}': {str(e)}")
        raise

# Initial setup and data refresh
validate_env_vars()
refresh_crypto_data()
