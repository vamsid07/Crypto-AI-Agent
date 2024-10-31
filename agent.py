# app.py

import streamlit as st
import asyncio
from crypto_price_query import (
    validate_env_vars,
    refresh_crypto_data,
    query_crypto_price,
    crypto_metadata,
    language_handler
)
import plotly.graph_objects as go
from datetime import datetime

# Custom CSS for better styling
st.set_page_config(
    page_title="Crypto Price Assistant",
    page_icon="💰",
    layout="wide"
)

# Add custom CSS
st.markdown("""
    <style>
    .main {
        padding: 2rem;
    }
    .stApp {
        background-color: #f5f7f9;
    }
    .css-1d391kg {
        padding: 1rem;
    }
    .stButton>button {
        width: 100%;
        border-radius: 5px;
        height: 3em;
    }
    .stTextInput>div>div>input {
        border-radius: 5px;
    }
    .st-emotion-cache-1v0mbdj {
        margin-top: 1em;
    }
    .market-card {
        background-color: white;
        padding: 1.5rem;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        margin-bottom: 1rem;
    }
    </style>
""", unsafe_allow_html=True)

# Initialize session state
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []

if 'crypto_metadata' not in st.session_state:
    validate_env_vars()
    refresh_crypto_data()
    st.session_state.crypto_metadata = crypto_metadata

def format_large_number(num):
    if num >= 1e9:
        return f"${num/1e9:.2f}B"
    elif num >= 1e6:
        return f"${num/1e6:.2f}M"
    elif num >= 1e3:
        return f"${num/1e3:.2f}K"
    return f"${num:.2f}"

async def handle_query():
    query = st.session_state.query_input
    if query:
        selected_lang = st.session_state.selected_language
        st.session_state.chat_history.append({
            "role": "user",
            "content": query,
            "language": selected_lang
        })

        try:
            response = await query_crypto_price(query, selected_lang)
            crypto_data = next((crypto for crypto in st.session_state.crypto_metadata 
                                if crypto['name'].lower() in response.lower() 
                                or crypto['symbol'].lower() in response.lower()), None)

            st.session_state.chat_history.append({
                "role": "assistant",
                "content": response,
                "data": crypto_data
            })
            st.session_state.query_input = ""

        except Exception as e:
            st.error(f"Error: {str(e)}")

def main():
    # Header section with gradient background
    st.markdown("""
        <div style='background: linear-gradient(90deg, #1e3c72 0%, #2a5298 100%); padding: 2rem; border-radius: 10px; margin-bottom: 2rem;'>
            <h1 style='color: white; text-align: center;'>🤖 Multilingual Crypto Price Assistant</h1>
            <p style='color: white; text-align: center; font-size: 1.2em;'>Ask me anything about cryptocurrency prices in your preferred language!</p>
        </div>
    """, unsafe_allow_html=True)

    # Sidebar with improved styling
    with st.sidebar:
        st.markdown("""
            <div style='background: white; padding: 1rem; border-radius: 10px; margin-bottom: 1rem;'>
                <h3 style='color: #1e3c72;'>⚙️ Settings</h3>
            </div>
        """, unsafe_allow_html=True)
        
        languages = language_handler.supported_languages
        selected_lang = st.selectbox(
            "Select Input Language",
            options=list(languages.keys()),
            format_func=lambda x: languages[x],
            key="selected_language"
        )
        
        st.markdown("---")
        
        st.markdown("""
            <div style='background: white; padding: 1rem; border-radius: 10px; margin-bottom: 1rem;'>
                <h3 style='color: #1e3c72;'>ℹ️ About</h3>
            </div>
        """, unsafe_allow_html=True)
        
        st.markdown("""
        This assistant provides:
        - 📈 Current cryptocurrency prices
        - 📊 24-hour price changes
        - 💰 Market capitalization
        - 📉 Trading volume
        - 🏆 Price rankings
        
        🌍 Supports multiple languages, including Indian languages!
        """)
        
        if st.button("🔄 Refresh Data", key="refresh_button"):
            with st.spinner("Refreshing cryptocurrency data..."):
                refresh_crypto_data()
                st.session_state.crypto_metadata = crypto_metadata
                st.success("✅ Data refreshed successfully!")

        st.markdown("---")
        st.markdown(f"🕒 Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Chat container with improved message styling
    chat_container = st.container()
    
    for message in st.session_state.chat_history:
        if message["role"] == "user":
            lang_name = languages.get(message.get("language", "en-IN"), "English")
            st.markdown(f"""
                <div style='background: #e6f3ff; padding: 1rem; border-radius: 10px; margin-bottom: 1rem;'>
                    <p><strong>You</strong> ({lang_name}): {message['content']}</p>
                </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
                <div style='background: white; padding: 1rem; border-radius: 10px; margin-bottom: 1rem;'>
                    <p><strong>Assistant</strong>: {message['content']}</p>
                </div>
            """, unsafe_allow_html=True)
            
            # Inside your main() function, where you create the price range chart:

            if "data" in message and message["data"]:
                with st.expander("📊 View Market Details"):
                    data = message["data"]
                    st.markdown("<div class='market-card'>", unsafe_allow_html=True)
                    
                    col1, col2, col3 = st.columns(3)
                    
                    col1.metric(
                        "💵 Current Price",
                        f"${data['current_price']:,.2f}", 
                        delta=f"{data['price_change_percentage_24h']:.2f}%"
                    )
                    col2.metric(
                        "📊 24h Volume",
                        format_large_number(data['total_volume'])
                    )
                    col3.metric(
                        "🏆 Market Cap",
                        format_large_number(data['market_cap']), 
                        f"Rank #{data['market_cap_rank']}"
                    )
                    
                    # Generate a unique key for each chart based on timestamp and crypto data
                    chart_key = f"price_chart_{data['symbol']}_{datetime.now().timestamp()}"
                    
                    # Enhanced price range chart with unique key
                    price_range_chart = go.Figure(go.Indicator(
                        mode="number+gauge+delta",
                        value=data['current_price'],
                        delta={'reference': data['current_price'] - data['price_change_24h']},
                        domain={'x': [0, 1], 'y': [0, 1]},
                        title={'text': "📈 24h Price Range", 'font': {'size': 20}},
                        gauge={
                            'axis': {'range': [data['low_24h'], data['high_24h']]},
                            'bar': {'color': "#1e3c72"},
                            'steps': [
                                {'range': [data['low_24h'], data['high_24h']], 'color': "#e6f3ff"}
                            ],
                            'threshold': {
                                'line': {'color': "#2a5298", 'width': 4},
                                'thickness': 0.75,
                                'value': data['current_price']
                            }
                        }
                    ))
                    
                    price_range_chart.update_layout(
                        height=250,
                        margin=dict(l=30, r=30, t=50, b=30),
                        paper_bgcolor='white',
                        plot_bgcolor='white'
                    )
                    
                    # Add the unique key to the plotly_chart
                    st.plotly_chart(price_range_chart, use_container_width=True, key=chart_key)
                    st.markdown("</div>", unsafe_allow_html=True)
    # Enhanced input area
    st.markdown("<div style='background: white; padding: 1.5rem; border-radius: 10px; margin-top: 2rem;'>", unsafe_allow_html=True)
    st.text_input(
        "💬 Ask a question:",
        key="query_input",
        on_change=lambda: asyncio.run(handle_query()),
        placeholder=f"Example: What is the current price of Bitcoin? (in {languages[selected_lang]})"
    )
    st.markdown("</div>", unsafe_allow_html=True)

if __name__ == "__main__":
    main()