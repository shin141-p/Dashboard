import pandas as pd

def calculate_sleep_debt(actual_sleep, target_sleep):
    """
    Calculates sleep debt based on actual sleep duration and a target duration.
    Sleep Debt = max(0, target_sleep - actual_sleep)
    
    Args:
        actual_sleep (float or pd.Series): The actual sleep duration(s) in hours.
        target_sleep (float): The target sleep duration in hours.
        
    Returns:
        float or pd.Series: The calculated sleep debt(s), ensuring no negative values.
    """
    debt = target_sleep - actual_sleep
    
    if isinstance(debt, pd.Series):
        return debt.apply(lambda x: max(0, x))
    else:
        return max(0, debt)
