"""Tests for money handling."""

import pytest
from decimal import Decimal

from src.core.money import Money, parse_money, zero_money


class TestMoney:
    """Test Money class."""
    
    def test_create_from_string(self):
        """Test creating Money from string."""
        money = Money("100.50", "USD")
        assert money.amount == Decimal("100.50")
        assert money.currency == "USD"
    
    def test_create_from_decimal(self):
        """Test creating Money from Decimal."""
        money = Money(Decimal("100.50"), "USD")
        assert money.amount == Decimal("100.50")
    
    def test_addition(self):
        """Test adding Money objects."""
        m1 = Money("10.50", "USD")
        m2 = Money("20.75", "USD")
        result = m1 + m2
        assert result.amount == Decimal("31.25")
        assert result.currency == "USD"
    
    def test_subtraction(self):
        """Test subtracting Money objects."""
        m1 = Money("100.00", "USD")
        m2 = Money("30.50", "USD")
        result = m1 - m2
        assert result.amount == Decimal("69.50")
    
    def test_subtraction_insufficient_funds(self):
        """Test subtraction with insufficient funds."""
        m1 = Money("10.00", "USD")
        m2 = Money("20.00", "USD")
        with pytest.raises(ValueError):
            _ = m1 - m2
    
    def test_currency_mismatch(self):
        """Test currency mismatch raises error."""
        m1 = Money("100.00", "USD")
        m2 = Money("100.00", "EUR")
        with pytest.raises(ValueError):
            _ = m1 + m2
    
    def test_comparison(self):
        """Test Money comparison."""
        m1 = Money("100.00", "USD")
        m2 = Money("50.00", "USD")
        assert m1 > m2
        assert m2 < m1
        assert m1 >= m2
        assert m2 <= m1
    
    def test_parse_money(self):
        """Test parse_money utility."""
        money = parse_money("100.50", "USD")
        assert isinstance(money, Money)
        assert money.amount == Decimal("100.50")
    
    def test_zero_money(self):
        """Test zero_money utility."""
        money = zero_money("USD")
        assert money.amount == Decimal("0")
        assert money.is_zero()
    
    def test_quantize(self):
        """Test quantizing to decimal places."""
        money = Money("100.555", "USD")
        quantized = money.quantize(2)
        assert quantized.amount == Decimal("100.56")  # Rounded up
    
    def test_no_float_precision_errors(self):
        """Test that we don't have float precision errors."""
        # This would fail with floats: 0.1 + 0.2 = 0.30000000000000004
        m1 = Money("0.1", "USD")
        m2 = Money("0.2", "USD")
        result = m1 + m2
        assert result.amount == Decimal("0.3")

