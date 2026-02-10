from crewai import Agent
from langchain_core.language_models import BaseChatModel

class FinancialAgents:
    def __init__(self, llm: BaseChatModel):
        self.llm = llm

    def data_collector(self) -> Agent:
        return Agent(
            role='Financial Data Collector',
            goal='Gather accurate and up-to-date financial data, including technical indicators',
            backstory=(
                "You are an expert financial data collector with access to real-time market data. "
                "Your job is to fetch stock prices, company info, historical data, and technical indicators (RSI, SMA). "
                "You are precise and never invent numbers."
            ),
            llm=self.llm,
            verbose=True,
            allow_delegation=False
        )

    def financial_analyst(self) -> Agent:
        return Agent(
            role='Senior Financial Analyst',
            goal='Analyze financial data to identify trends, technical signals, and risks',
            backstory=(
                "You are a seasoned Wall Street analyst. You combine fundamental analysis (P/E, Market Cap) "
                "with technical analysis (RSI, Moving Averages) to form a comprehensive view. "
                "You identify bullish/bearish trends and overbought/oversold conditions."
            ),
            llm=self.llm,
            verbose=True,
            allow_delegation=False
        )

    def reporter(self) -> Agent:
        return Agent(
            role='Financial Journalist',
            goal='Create compelling and easy-to-understand financial reports',
            backstory=(
                "You are a journalist for a top financial publication. "
                "You take complex analysis and turn it into a readable, engaging report "
                "for investors. You use markdown formatting effectively."
            ),
            llm=self.llm,
            verbose=True,
            allow_delegation=False
        )
