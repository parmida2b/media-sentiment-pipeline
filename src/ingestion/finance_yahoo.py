import yfinance as yf
import pandas as pd
from dataclasses import dataclass
from typing import List

@dataclass
class Config:
    products: List[str]
    start_date: str
    end_date: str
    analysis: bool = False


class FinanceData:
    """Download, process, and enrich multi-asset financial data."""

    # Static mapping for asset display names
    ASSET_NAMES = {
        "GC=F": "Gold Futures",
        "CL=F": "WTI Crude Oil",
        "BZ=F": "Brent Crude Oil",
        "DX-Y.NYB": "US Dollar Index",
        "^GSPC": "S&P 500",
        "^IXIC": "NASDAQ Composite",
        "^VIX": "Volatility Index (VIX)",
        "BTC-USD": "Bitcoin",
        "ETH-USD": "Ethereum"
    }

    def __init__(self, config: Config):
        self.products = config.products
        self.start_date = config.start_date
        self.end_date = config.end_date
        self.analysis = config.analysis
        self.raw_data = None
        self.df = None

    def download_data(self):
        """Fetch all tickers as a multi-level DataFrame (grouped by ticker)."""
        self.raw_data = yf.download(
            tickers=self.products,
            start=self.start_date,
            end=self.end_date,
            group_by="ticker",
            auto_adjust=True,
            progress=False        
        )

    def process_data(self):
        """Convert the multi-level DataFrame into a long-format table."""
        frames = []
        for ticker in self.products:

            temp = self.raw_data[ticker].copy().reset_index()
            temp["Asset"] = ticker
            temp["Asset_Name"] = self.ASSET_NAMES.get(ticker, ticker)
            frames.append(temp)

        self.df = pd.concat(frames, ignore_index=True)


        columns = ["Date", "Asset", "Asset_Name", "Open", "High", "Low", "Close", "Volume"]
        self.df = self.df[columns]


        self.df.sort_values(["Date", "Asset"], inplace=True)
        self.df.reset_index(drop=True, inplace=True)

    def add_calculated_columns(self):
        """Add daily returns and price changes, correctly grouped by asset."""
        # Daily return (close-to-close), per asset
        self.df["Daily_Return"] = self.df.groupby("Asset")["Close"].pct_change()

        self.df["Price_Change"] = self.df["Close"] - self.df["Open"]
        self.df["Price_Change_Percent"] = (
            (self.df["Close"] - self.df["Open"]) / self.df["Open"] * 100
        )

    def run(self):
        """Execute the full download → process → enrich pipeline."""
        self.download_data()
        self.process_data()
        self.add_calculated_columns()
        return self.df


if __name__ == "__main__":
    cfg = Config(
        products=[
            "GC=F", "CL=F", "BZ=F", "DX-Y.NYB",
            "^GSPC", "^IXIC", "^VIX",
            "BTC-USD", "ETH-USD"
        ],
        start_date="2025-01-01",
        end_date="2025-07-01",
        analysis=True
    )

    finance = FinanceData(cfg)
    result = finance.run()

    result.to_csv("primary_data.csv", index=False)
    print(result.head())