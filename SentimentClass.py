"""
OHLCSentimentAnalyzer: Sentiment Analysis for OHLC (Open, High, Low, Close) Data

This class provides functionality to analyze sentiment in financial market data,
particularly for cryptocurrency trading. It uses various technical indicators
and price action patterns to determine market sentiment.

Key Features:
1. Sentiment classification into categories like Bull, Bear, Sideways, etc.
2. Utilizes PyTorch for efficient tensor computations
3. Analyzes trends, volatility, and price patterns
4. Customizable output formats for API integration

Main Methods:
- __init__(self, apiout=False): Initializes the analyzer with sentiment definitions
- calculate_trend(self, x, y): Calculates the trend slope using linear regression
- analyze_torch(self, data_tensor): Performs sentiment analysis on PyTorch tensors

Attributes:
- apiout: Boolean flag for API output format
- sentiments: Dictionary containing sentiment definitions and associated symbols

Usage:
Instantiate the OHLCSentimentAnalyzer class and use the analyze_torch method
with OHLCV (Open, High, Low, Close, Volume) data to get sentiment analysis results.

Dependencies:
- PyTorch: For tensor computations
- Colorama: For colored console output
- NumPy: For numerical operations

Note: Ensure all dependencies are installed before using this class.
"""

from colorama import Fore as fg
import numpy as np
import torch

class OHLCSentimentAnalyzer:
    def __init__(self, apiout=False):
        self.apiout = apiout
        # names for the sentiment dictionary
        self.NAME = 0
        self.ICON = 1
        self.COLOR = 2
        self.SID = 3

        self.sentiments = {
            "Strong_Bear":       ["Strong Bear",      "🡳", fg.LIGHTRED_EX,2],
            "Bear":              ["Bear",             "🡦", fg.RED,3],
            "Sideways":          ["Sideways",         "🡒", fg.WHITE,1],
            "Bull":              ["Bull",             "🡥", fg.GREEN,5],
            "Strong_Bull":       ["Strong Bull",      "🡹", fg.LIGHTGREEN_EX,4],
            "Strong_Resistance": ["Strong Resistance","⊢", fg.LIGHTCYAN_EX,6],
            "Strong_Support":    ["Strong Support",   "⊥", fg.LIGHTYELLOW_EX,7],
            "High_Volatility":   ["High Volatility",  "≋", fg.LIGHTMAGENTA_EX,8],
            "Neutral":           ["Neutral",          "⥯", fg.LIGHTYELLOW_EX,9],
            "Mixed":             ["Mixed",            "⥯", fg.LIGHTYELLOW_EX,10]
        }


    def calculate_trend(self, x, y):
        n = x.shape[0]
        sum_x = torch.sum(x)
        sum_y = torch.sum(y)
        sum_xy = torch.sum(x * y)
        sum_xx = torch.sum(x * x)
        slope = (n * sum_xy - sum_x * sum_y) / (n * sum_xx - sum_x * sum_x)
        return slope

    def analyze_torch(self, data_tensor):
        opens, highs, lows, closes, volumes = data_tensor[:, :5].unbind(1)

        price_change = (closes[-1] - opens[0]) / opens[0]
        volatility = (highs.max() - lows.min()) / opens[0]

        x = torch.arange(len(closes), dtype=torch.float32, device=data_tensor.device)
        trend = self.calculate_trend(x, closes)

        body_sizes = torch.abs(closes - opens) / opens
        average_body_size = body_sizes.mean()
        upper_wicks = (highs - torch.maximum(opens, closes)) / opens
        lower_wicks = (torch.minimum(opens, closes) - lows) / opens
        average_upper_wick = upper_wicks.mean()
        average_lower_wick = lower_wicks.mean()

        sentiment = \
            torch.where((price_change       < -0.05) & (trend      < 0)   , torch.tensor(self.sentiments["Strong_Bear"][3]      , device=data_tensor.device),
            torch.where((price_change       < -0.02) & (trend      < 0)   , torch.tensor(self.sentiments["Bear"][3]             , device=data_tensor.device),
            torch.where((price_change.abs() < 0.02)  & (volatility < 0.03), torch.tensor(self.sentiments["Sideways"][3]         , device=data_tensor.device),
            torch.where((price_change       > 0.02)  & (trend      > 0)   , torch.tensor(self.sentiments["Bull"][3]             , device=data_tensor.device),
            torch.where((price_change       > 0.05)  & (trend      > 0)   , torch.tensor(self.sentiments["Strong_Bull"][3]      , device=data_tensor.device),

            torch.where(average_upper_wick  > 2 * average_body_size       , torch.tensor(self.sentiments["Strong_Resistance"][3], device=data_tensor.device),
            torch.where(average_lower_wick  > 2 * average_body_size       , torch.tensor(self.sentiments["Strong_Support"][3]   , device=data_tensor.device),
            torch.where(volatility          > 0.04                        , torch.tensor(self.sentiments["High_Volatility"][3]  , device=data_tensor.device),

            torch.tensor(self.sentiments["Mixed"][3], device=data_tensor.device)))))))))

        return sentiment

    def analyze(self, data):
        """
        Analyze sentiment of OHLC data for a given window.

        :param data: pandas DataFrame with 'open', 'high', 'low', 'close', 'volume' columns
        :return: sentiment label for the given window
        """
        try:
            opens   = data['open']
            closes  = data['close']
            highs   = data['high']
            lows    = data['low']
            volume  = data['volume']

            price_change = (closes.iloc[-1] - opens.iloc[0]) / opens.iloc[0]    # percentage decimal
            volatility   = (highs.max() - lows.min()) / opens.iloc[0]           # percentage decimal
            trend        = np.polyfit(range(len(closes)), closes, 1)[0]         # percentage decimal

            # Calculate additional metrics
            body_sizes          = abs(closes - opens) / opens
            average_body_size   = body_sizes.mean()
            upper_wicks         = (highs - np.maximum(opens, closes)) / opens
            lower_wicks         = (np.minimum(opens, closes) - lows) / opens
            average_upper_wick  = upper_wicks.mean()
            average_lower_wick  = lower_wicks.mean()

            lm0 = { # original settings
               'fast_market': 0.05,
               'slow_market': 0.02,
               'slow_trend': 0,
               'fast_trend': 0,
               'calm_market': 0.01,
               'low_volatility': 0.02,
            }

            # lm1 = { #
            #    'slow_market': 0.035, # narrower range
            #    'fast_market': 0.0175, # narrower range
            #    'slow_trend': 0,
            #    'fast_trend': 50, # less sensitive to trend
            #    'calm_market': 0.01,
            #    'low_volatility': 0.02,
            # }

            # lm2 = {
            #    'slow_market': 0.05,
            #    'fast_market': 0.02,
            #    'slow_trend': 0,
            #    'fast_trend': 0,
            #    'calm_market': 0.02,    # more sensitive to market conditions
            #    'low_volatility': 0.03, # more sensitive to market conditions
            # }

            # lm3 = {
            #    'slow_market': 0.05,# wider range
            #    'fast_market': 0.02,# wider range
            #    'slow_trend': 0,
            #    'fast_trend': 0,
            #    'calm_market': 0.02,    # more sensitive to market conditions
            #    'low_volatility': 0.03, # more sensitive to market conditions
            # }

            lm = lm0  # this is the best so far, by a long shot

            if   price_change      < -(lm['fast_market']) and trend      < lm['fast_trend']:    vals= self.sentiments["Strong_Bear"]
            elif price_change      < -(lm['slow_market']) and trend      < lm['slow_trend']:    vals= self.sentiments["Bear"]

            elif abs(price_change) < +(lm['calm_market']) and volatility < lm['low_volatility']: vals= self.sentiments["Sideways"]

            elif price_change      > +(lm['slow_market']) and trend      > lm['slow_trend']:    vals= self.sentiments["Bull"]
            elif price_change      > +(lm['fast_market']) and trend      > lm['fast_trend']:    vals= self.sentiments["Strong_Bull"]

            elif average_upper_wick > 2 * average_body_size:   vals= self.sentiments["Strong_Resistance"]
            elif average_lower_wick > 2 * average_body_size:   vals= self.sentiments["Strong_Support"]
            elif volatility > 0.04:                            vals= self.sentiments["High_Volatility"]
            else:                                              vals= self.sentiments["Mixed"]

            if self.apiout:
                rs = vals[self.SID]
            else:
                rs = vals

            metsdata = {
                        'price_change':price_change,
                        'trend':trend,
                        'average_body_size':average_body_size,
                        'average_upper_wick':average_upper_wick,
                        'average_lower_wick':average_lower_wick,
                        'volatility':volatility
                       }

            return rs, metsdata


        except Exception as e:
            print("No more data (or data is corrupt)")
            print('Last Data:', data.iloc[-1])
            return


# Usage example:
# analyzer = OHLCSentimentAnalyzer()
# sentiment = analyzer.analyze(df_window)