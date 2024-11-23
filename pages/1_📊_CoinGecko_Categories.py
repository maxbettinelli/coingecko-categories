import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# Page config
st.set_page_config(
    page_title="Crypto Category Analysis",
    page_icon="📊",
    layout="wide"
)

# Constants

CMC_API_KEY = st.secrets["CMC_API_KEY"]
COINGECKO_BASE_URL = "https://api.coingecko.com/api/v3"
@st.cache_data(ttl=3600)
def fetch_categories():
    try:
        response = requests.get(f"{COINGECKO_BASE_URL}/coins/categories/list")
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        st.error(f"Error fetching categories: {e}")
        return None

@st.cache_data(ttl=300)
def fetch_category_data(category_id):
    try:
        response = requests.get(f"{COINGECKO_BASE_URL}/coins/markets", params={
            'vs_currency': 'usd',
            'category': category_id,
            'order': 'market_cap_desc',
            'per_page': 250,
            'sparkline': False,
            'price_change_percentage': '1h,24h,7d'
        })
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        st.error(f"Error fetching category data: {e}")
        return None

def safe_treemap(df, selected_category):
    try:
        df_filtered = df[df['market_cap'].notna() & (df['market_cap'] > 0)].copy()
        
        if df_filtered.empty:
            st.warning("No valid market cap data available for treemap visualization.")
            return None
            
        fig_treemap = px.treemap(
            df_filtered,
            path=[px.Constant(selected_category), 'name'],
            values='market_cap',
            custom_data=['symbol', 'total_volume', 'price_change_percentage_24h'],
            color='price_change_percentage_24h',
            color_continuous_scale=[[0, 'red'], [0.5, 'beige'], [1, 'green']],
            color_continuous_midpoint=0,
            title=f"Market Cap Distribution in {selected_category}"
        )
        
        fig_treemap.update_traces(
            hovertemplate="""
            <b>%{label}</b><br>
            Symbol: %{customdata[0]}<br>
            Market Cap: $%{value:,.0f}<br>
            24h Volume: $%{customdata[1]:,.0f}<br>
            24h Change: %{customdata[2]:.2f}%
            <extra></extra>
            """
        )
        
        return fig_treemap
    except Exception as e:
        st.warning(f"Could not create treemap visualization: {e}")
        return None

def safe_metrics(df):
    try:
        metrics = {
            'total_tokens': len(df),
            'total_market_cap': df['market_cap'].sum(),
            'total_volume': df['total_volume'].sum(),
            'avg_24h_change': df['price_change_percentage_24h'].mean()
        }
        metrics = {k: 0 if pd.isna(v) else v for k, v in metrics.items()}
        return metrics
    except Exception as e:
        st.warning(f"Error calculating metrics: {e}")
        return {
            'total_tokens': 0,
            'total_market_cap': 0,
            'total_volume': 0,
            'avg_24h_change': 0
        }

def main():
    st.title("🔍 DTF Scope")
    
    categories = fetch_categories()
    if not categories:
        st.error("Failed to fetch categories. Please try again later.")
        return
    
    categories_df = pd.DataFrame(categories)
    
    with st.sidebar:
        st.header("Category Selection")
        search_term = st.text_input("Search Categories", 
                                  placeholder="e.g., defi, nft, governance").lower()
        
        filtered_categories = categories_df[
            categories_df['name'].str.lower().str.contains(search_term)
        ]
        
        if not filtered_categories.empty:
            selected_category = st.selectbox(
                "Select Category",
                options=filtered_categories['name'].tolist(),
                index=0
            )
            selected_id = filtered_categories[
                filtered_categories['name'] == selected_category
            ]['category_id'].iloc[0]
        else:
            st.warning("No categories found matching your search.")
            return
    
    with st.spinner("Fetching category data..."):
        category_data = fetch_category_data(selected_id)
        
        if category_data:
            df = pd.DataFrame(category_data)
            
            metrics = safe_metrics(df)
            
            st.header(f"📊 {selected_category} Overview")
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Number of Tokens", f"{metrics['total_tokens']:,}")
            with col2:
                st.metric("Total Market Cap", f"${metrics['total_market_cap']:,.0f}")
            with col3:
                st.metric("24h Volume", f"${metrics['total_volume']:,.0f}")
            with col4:
                st.metric("Avg 24h Change", f"{metrics['avg_24h_change']:.2f}%")
            
            fig_treemap = safe_treemap(df, selected_category)
            if fig_treemap:
                st.plotly_chart(fig_treemap, use_container_width=True)
            
            if not df.empty:
                st.subheader("Performance Analysis")
                col1, col2 = st.columns(2)
                
                with col1:
                    try:
                        fig_hist = px.histogram(
                            df[df['price_change_percentage_24h'].notna()],
                            x='price_change_percentage_24h',
                            title='24h Price Change Distribution',
                            nbins=20
                        )
                        st.plotly_chart(fig_hist, use_container_width=True)
                    except Exception as e:
                        st.warning("Could not create price change distribution chart.")
                
                with col2:
                    try:
                        df_filtered = df[
                            df['market_cap'].notna() & 
                            df['total_volume'].notna() & 
                            (df['market_cap'] > 0) & 
                            (df['total_volume'] > 0)
                        ]
                        if not df_filtered.empty:
                            fig_scatter = px.scatter(
                                df_filtered,
                                x='market_cap',
                                y='total_volume',
                                color='price_change_percentage_24h',
                                size='market_cap',
                                hover_name='name',
                                log_x=True,
                                log_y=True,
                                title='Volume vs Market Cap'
                            )
                            st.plotly_chart(fig_scatter, use_container_width=True)
                        else:
                            st.warning("Insufficient data for volume vs market cap visualization.")
                    except Exception as e:
                        st.warning("Could not create volume vs market cap chart.")

if __name__ == "__main__":
    main()