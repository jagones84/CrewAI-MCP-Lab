from mcp.server.fastmcp import FastMCP
import yfinance as yf
import pandas as pd
import json

# Initialize FastMCP server
mcp = FastMCP("YFinance")

@mcp.tool()
def get_stock_price(ticker: str) -> str:
    """
    Get the current price of a stock.
    Args:
        ticker: The stock ticker symbol (e.g., 'AAPL', 'MSFT').
    Returns:
        JSON string with current price and currency.
    """
    try:
        stock = yf.Ticker(ticker)
        # Fast retrieval
        price = stock.fast_info.last_price
        currency = stock.fast_info.currency
        return json.dumps({"ticker": ticker, "price": price, "currency": currency})
    except Exception as e:
        return json.dumps({"error": str(e)})

@mcp.tool()
def get_stock_info(ticker: str) -> str:
    """
    Get detailed information about a company/stock.
    Args:
        ticker: The stock ticker symbol.
    Returns:
        JSON string with company info (sector, industry, summary, etc.).
    """
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        # Filter some heavy keys if needed, but returning all is fine for now
        # We might want to limit the size of the return for LLM context
        keys_to_keep = ['longName', 'industry', 'sector', 'longBusinessSummary', 'marketCap', 'trailingPE', 'forwardPE', 'fiftyTwoWeekHigh', 'fiftyTwoWeekLow']
        filtered_info = {k: info.get(k) for k in keys_to_keep if k in info}
        return json.dumps(filtered_info)
    except Exception as e:
        return json.dumps({"error": str(e)})

@mcp.tool()
def get_stock_history(ticker: str, period: str = "1mo") -> str:
    """
    Get historical stock data.
    Args:
        ticker: The stock ticker symbol.
        period: The data period to download (e.g., '1d', '5d', '1mo', '3mo', '6mo', '1y', 'ytd', 'max').
    Returns:
        JSON string with historical data (Date, Open, High, Low, Close, Volume).
    """
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period=period)
        if hist.empty:
            return json.dumps({"error": "No data found"})
        
        # Reset index to get Date as a column
        hist.reset_index(inplace=True)
        # Convert Timestamp to string
        hist['Date'] = hist['Date'].astype(str)
        # Select important columns
        data = hist[['Date', 'Open', 'High', 'Low', 'Close', 'Volume']].to_dict(orient='records')
        return json.dumps(data)
    except Exception as e:
        return json.dumps({"error": str(e)})

@mcp.tool()
def get_stock_news(ticker: str) -> str:
    """
    Get recent news for a stock.
    Args:
        ticker: The stock ticker symbol.
    Returns:
        JSON string with list of news items (title, link, publisher, relatedTickers).
    """
    try:
        stock = yf.Ticker(ticker)
        news = stock.news
        return json.dumps(news)
    except Exception as e:
        return json.dumps({"error": str(e)})

@mcp.tool()
def get_technical_indicators(ticker: str, period: str = "3mo") -> str:
    """
    Calculate technical indicators (SMA_50, SMA_200, RSI_14) for a stock.
    Args:
        ticker: The stock ticker symbol.
        period: Data period to fetch for calculation (default '3mo').
    Returns:
        JSON string with latest indicators and signal interpretation.
    """
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period=period)
        if hist.empty or len(hist) < 50:
            return json.dumps({"error": "Not enough data for indicators"})
        
        # Calculate SMA
        hist['SMA_50'] = hist['Close'].rolling(window=50).mean()
        hist['SMA_200'] = hist['Close'].rolling(window=200).mean()
        
        # Calculate RSI
        delta = hist['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        hist['RSI_14'] = 100 - (100 / (1 + rs))
        
        # Get latest values
        latest = hist.iloc[-1]
        result = {
            "ticker": ticker,
            "current_price": latest['Close'],
            "SMA_50": latest['SMA_50'] if not pd.isna(latest['SMA_50']) else None,
            "SMA_200": latest['SMA_200'] if not pd.isna(latest['SMA_200']) else None,
            "RSI_14": latest['RSI_14'] if not pd.isna(latest['RSI_14']) else None,
            "interpretation": {
                "trend": "Bullish" if (latest['SMA_50'] and latest['SMA_200'] and latest['SMA_50'] > latest['SMA_200']) else "Bearish",
                "rsi_signal": "Overbought" if latest['RSI_14'] > 70 else "Oversold" if latest['RSI_14'] < 30 else "Neutral"
            }
        }
        return json.dumps(result)
    except Exception as e:
        return json.dumps({"error": str(e)})

if __name__ == "__main__":
    mcp.run()
