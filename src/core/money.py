"""Money handling utilities - Never use floats!"""

from decimal import Decimal, ROUND_HALF_UP, getcontext
from typing import Union


# Configure decimal context
getcontext().prec = 28
getcontext().rounding = ROUND_HALF_UP


class Money:
    """Money type that uses Decimal for exact precision."""
    
    def __init__(self, amount: Union[str, Decimal, int, float], currency: str = "USD"):
        """
        Initialize Money object.
        
        Args:
            amount: Amount as string, Decimal, int, or float
            currency: ISO 4217 currency code (default: USD)
        
        Note: Always prefer string or Decimal to avoid float precision issues.
        """
        if isinstance(amount, str):
            self.amount = Decimal(amount)
        elif isinstance(amount, Decimal):
            self.amount = amount
        elif isinstance(amount, (int, float)):
            # Convert to string first to avoid float precision issues
            self.amount = Decimal(str(amount))
        else:
            raise ValueError(f"Invalid amount type: {type(amount)}")
        
        self.currency = currency.upper()
        
        # Validate amount is non-negative
        if self.amount < 0:
            raise ValueError("Amount cannot be negative")
    
    def __add__(self, other: "Money") -> "Money":
        """Add two Money objects."""
        if self.currency != other.currency:
            raise ValueError(f"Cannot add {self.currency} and {other.currency}")
        return Money(self.amount + other.amount, self.currency)
    
    def __sub__(self, other: "Money") -> "Money":
        """Subtract two Money objects."""
        if self.currency != other.currency:
            raise ValueError(f"Cannot subtract {self.currency} and {other.currency}")
        result = self.amount - other.amount
        if result < 0:
            raise ValueError("Result cannot be negative")
        return Money(result, self.currency)
    
    def __mul__(self, multiplier: Union[int, float, Decimal]) -> "Money":
        """Multiply Money by a number."""
        if isinstance(multiplier, (int, float)):
            multiplier = Decimal(str(multiplier))
        return Money(self.amount * multiplier, self.currency)
    
    def __truediv__(self, divisor: Union[int, float, Decimal]) -> "Money":
        """Divide Money by a number."""
        if isinstance(divisor, (int, float)):
            divisor = Decimal(str(divisor))
        return Money(self.amount / divisor, self.currency)
    
    def __eq__(self, other: "Money") -> bool:
        """Check equality."""
        return self.amount == other.amount and self.currency == other.currency
    
    def __lt__(self, other: "Money") -> bool:
        """Less than comparison."""
        if self.currency != other.currency:
            raise ValueError(f"Cannot compare {self.currency} and {other.currency}")
        return self.amount < other.amount
    
    def __le__(self, other: "Money") -> bool:
        """Less than or equal comparison."""
        if self.currency != other.currency:
            raise ValueError(f"Cannot compare {self.currency} and {other.currency}")
        return self.amount <= other.amount
    
    def __gt__(self, other: "Money") -> bool:
        """Greater than comparison."""
        if self.currency != other.currency:
            raise ValueError(f"Cannot compare {self.currency} and {other.currency}")
        return self.amount > other.amount
    
    def __ge__(self, other: "Money") -> bool:
        """Greater than or equal comparison."""
        if self.currency != other.currency:
            raise ValueError(f"Cannot compare {self.currency} and {other.currency}")
        return self.amount >= other.amount
    
    def __repr__(self) -> str:
        """String representation."""
        return f"Money({self.amount}, {self.currency})"
    
    def __str__(self) -> str:
        """String representation."""
        return f"{self.amount} {self.currency}"
    
    def to_decimal(self) -> Decimal:
        """Convert to Decimal."""
        return self.amount
    
    def quantize(self, decimal_places: int = 2) -> "Money":
        """Round to specified decimal places."""
        quantized = self.amount.quantize(Decimal('0.1') ** decimal_places, rounding=ROUND_HALF_UP)
        return Money(quantized, self.currency)
    
    def is_zero(self) -> bool:
        """Check if amount is zero."""
        return self.amount == Decimal('0')
    
    def is_positive(self) -> bool:
        """Check if amount is positive."""
        return self.amount > Decimal('0')


def parse_money(amount: Union[str, Decimal, int, float], currency: str = "USD") -> Money:
    """Parse amount into Money object."""
    return Money(amount, currency)


def zero_money(currency: str = "USD") -> Money:
    """Create zero Money object."""
    return Money(Decimal('0'), currency)

