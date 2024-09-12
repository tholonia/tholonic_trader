from colorama import Fore as fg
import numpy as np
import torch

class OHLCSentimentAnalyzer:
    def __init__(self, apiout=False):
        self.apiout = apiout
        self.sentiments = {
            "Strong_Bear": ["Strong Bear", "🡳", fg.LIGHTRED_EX,2],
            "Bear": ["Bear", "🡦", fg.RED,3],
            "Sideways": ["Sideways", "🡒", fg.WHITE,1],
            "Bull": ["Bull", "🡥", fg.GREEN,5],
            "Strong_Bull": ["Strong Bull", "🡹", fg.LIGHTGREEN_EX,4],
            "Strong_Resistance": ["Strong Resistance", "⊢", fg.LIGHTCYAN_EX,6],
            "Strong_Support": ["Strong Support", "⊥", fg.LIGHTYELLOW_EX,7],
            "High_Volatility": ["High Volatility", "≋", fg.LIGHTMAGENTA_EX,8],
            "Neutral": ["Neutral", "⥯", fg.LIGHTYELLOW_EX,9],
            "Mixed": ["Mixed", "⥯", fg.LIGHTYELLOW_EX,10]
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
        opens = data['open']
        closes = data['close']
        highs = data['high']
        lows = data['low']
        volume = data['volume']

        price_change = (closes.iloc[-1] - opens.iloc[0]) / opens.iloc[0]
        volatility = (highs.max() - lows.min()) / opens.iloc[0]
        trend = np.polyfit(range(len(closes)), closes, 1)[0]

        # Calculate additional metrics
        body_sizes = abs(closes - opens) / opens
        average_body_size = body_sizes.mean()
        upper_wicks = (highs - np.maximum(opens, closes)) / opens
        lower_wicks = (np.minimum(opens, closes) - lows) / opens
        average_upper_wick = upper_wicks.mean()
        average_lower_wick = lower_wicks.mean()

        if   price_change      < -0.05 and trend      < 0:    vals= self.sentiments["Strong_Bear"]
        elif price_change      < -0.02 and trend      < 0:    vals= self.sentiments["Bear"]

        #! I THINK this is the correct one as it in the class that was used vs the standalone setiment script :/
        elif abs(price_change) < +0.01 and volatility < 0.02: vals= self.sentiments["Sideways"]
        #! this was the original one that was used in the standalone sentiment script
        # elif abs(price_change) < +0.02 and volatility < 0.03: vals= self.sentiments["Sideways"]
        elif price_change      > +0.02 and trend      > 0:    vals= self.sentiments["Bull"]
        elif price_change      > +0.05 and trend      > 0:    vals= self.sentiments["Strong_Bull"]

        elif average_upper_wick > 2 * average_body_size:   vals= self.sentiments["Strong_Resistance"]
        elif average_lower_wick > 2 * average_body_size:   vals= self.sentiments["Strong_Support"]
        elif volatility > 0.04:                            vals= self.sentiments["High_Volatility"]
        else:                                              vals= self.sentiments["Mixed"]

        if self.apiout:
            return(vals[3])
        else:
            return vals


# Usage example:
# analyzer = OHLCSentimentAnalyzer()
# sentiment = analyzer.analyze(df_window)