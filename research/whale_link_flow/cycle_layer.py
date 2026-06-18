import datetime
import pandas as pd
from typing import Tuple, Union

# BTC Halving Dates in UTC
HALVING_DATES = [
    datetime.datetime(2012, 11, 28, 0, 0, tzinfo=datetime.timezone.utc),
    datetime.datetime(2016, 7, 9, 0, 0, tzinfo=datetime.timezone.utc),
    datetime.datetime(2020, 5, 11, 0, 0, tzinfo=datetime.timezone.utc),
    datetime.datetime(2024, 4, 19, 0, 0, tzinfo=datetime.timezone.utc),
    datetime.datetime(2028, 4, 17, 0, 0, tzinfo=datetime.timezone.utc), # Estimated H5
]

def to_utc_datetime(val: Union[int, float, str, datetime.datetime, pd.Timestamp]) -> datetime.datetime:
    """
    Converts various timestamp formats to a timezone-aware UTC datetime.
    """
    if isinstance(val, (int, float)):
        # Check if ms
        if val > 5e11:
            val = val / 1000.0
        return datetime.datetime.fromtimestamp(val, tz=datetime.timezone.utc)
    elif isinstance(val, str):
        dt = pd.to_datetime(val)
        if dt.tzinfo is None:
            dt = dt.tz_localize('UTC')
        else:
            dt = dt.tz_convert('UTC')
        return dt.to_pydatetime()
    elif isinstance(val, pd.Timestamp):
        if val.tzinfo is None:
            val = val.tz_localize('UTC')
        else:
            val = val.tz_convert('UTC')
        return val.to_pydatetime()
    elif isinstance(val, datetime.datetime):
        if val.tzinfo is None:
            return val.replace(tzinfo=datetime.timezone.utc)
        return val.astimezone(datetime.timezone.utc)
    else:
        raise TypeError(f"Unsupported timestamp type: {type(val)}")

class CycleLayer:
    @staticmethod
    def get_cycle_info(timestamp: Union[int, float, str, datetime.datetime, pd.Timestamp]) -> Tuple[int, str]:
        """
        Given a timestamp, returns:
        - cycle_day: days elapsed since the most recent halving
        - cycle_phase: the classified phase of the halving cycle
        """
        dt = to_utc_datetime(timestamp)
        
        # Find the most recent halving date
        prev_halving = None
        for h_date in HALVING_DATES:
            if h_date <= dt:
                prev_halving = h_date
            else:
                break
                
        if prev_halving is None:
            # Default to the first halving if timestamp is very old
            prev_halving = HALVING_DATES[0]
            
        delta = dt - prev_halving
        cycle_day = int(delta.total_seconds() / 86400.0)
        
        # Classify phase based on cycle_day
        if cycle_day <= 180:
            phase = 'post_halving_0_180'
        elif cycle_day <= 360:
            phase = 'post_halving_180_360'
        elif cycle_day <= 750:
            phase = 'late_cycle'
        elif cycle_day <= 1050:
            phase = 'bear_reset'
        else:
            phase = 'pre_halving'
            
        return cycle_day, phase
