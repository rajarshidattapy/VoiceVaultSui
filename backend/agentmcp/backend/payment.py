"""Payment breakdown calculation for Monad (MON units)."""
import math


PLATFORM_FEE_BPS = 250   # 2.5%
ROYALTY_BPS = 1000        # 10%


def calculate_breakdown(total_wei: int) -> dict:
    platform_fee = math.floor(total_wei * PLATFORM_FEE_BPS / 10_000)
    remaining = total_wei - platform_fee
    royalty = math.floor(remaining * ROYALTY_BPS / 10_000)
    creator = remaining - royalty
    return {
        "totalAmount": total_wei,
        "platformFee": platform_fee,
        "royaltyAmount": royalty,
        "creatorAmount": creator,
    }
