from crewai import Task
from textwrap import dedent

class FinancialTasks:
    def collect_data_task(self, agent, tickers):
        return Task(
            description=dedent(f"""\
                Collect comprehensive financial data for the following tickers: {tickers}.
                For each ticker:
                1. Get the current stock price.
                2. Get the company information (industry, sector, etc.).
                3. Get technical indicators (RSI, SMA_50, SMA_200).
                4. Get the latest news.
                
                Compile all this raw data into a structured summary.
            """),
            expected_output="A comprehensive data report containing price, info, technicals, and news for each ticker.",
            agent=agent
        )

    def analyze_data_task(self, agent):
        return Task(
            description=dedent("""\
                Analyze the provided financial data.
                1. Fundamental: Evaluate P/E ratio, Market Cap, and sector position.
                2. Technical: Analyze RSI (Overbought/Oversold) and SMA trends (Bullish/Bearish).
                3. Sentiment: Analyze the sentiment of the latest news.
                4. Synthesis: Combine these factors to identify risks and opportunities.
            """),
            expected_output="A detailed analysis report merging fundamental and technical insights.",
            agent=agent
        )

    def write_report_task(self, agent, output_path):
        return Task(
            description=dedent("""\
                Write a final investment report based on the analysis provided by the analyst.
                
                IMPORTANT:
                - You MUST generate the full markdown report.
                - Do NOT say "I can do this" or "Here is the report".
                - Start directly with the title.
                
                Structure:
                - **Executive Summary**: Brief overview.
                - **Stock-by-Stock Analysis**: 
                  - Ticker & Price
                  - Company Overview
                  - Technical Analysis (RSI, SMA trends)
                  - Fundamental Analysis
                  - News Sentiment
                  - Recommendation
                - **Conclusion**: Final thoughts.
            """),
            expected_output="A professional Markdown financial report containing the full analysis.",
            agent=agent,
            output_file=output_path
        )
