import pytest
from market_data_fetcher import MarketDataFetcher
from nifty50_symbols import get_all_symbols

@pytest.fixture
def market_data_fetcher():
    return MarketDataFetcher()

def test_initialization(market_data_fetcher):
    """Test if MarketDataFetcher initializes correctly"""
    assert market_data_fetcher is not None
    assert hasattr(market_data_fetcher, 'market_data')
    assert hasattr(market_data_fetcher, 'ws')

def test_symbol_loading(market_data_fetcher):
    """Test if all symbols are loaded correctly"""
    symbols = get_all_symbols()
    assert len(symbols) > 0
    assert 'NIFTY50-INDEX' in symbols

def test_market_data_structure(market_data_fetcher):
    """Test if market data has the correct structure"""
    market_data = market_data_fetcher.market_data
    assert isinstance(market_data, dict)
    
    # Check if all required fields are present for each symbol
    for symbol, data in market_data.items():
        assert 'symbol' in data
        assert 'ltp' in data
        assert 'open' in data
        assert 'high' in data
        assert 'low' in data
        assert 'close' in data
        assert 'volume' in data
        assert 'timestamp' in data

def test_data_processing(market_data_fetcher):
    """Test if data processing works correctly"""
    test_data = {
        'symbol': 'RELIANCE-EQ',
        'ltp': 2500.0,
        'open': 2480.0,
        'high': 2510.0,
        'low': 2470.0,
        'close': 2490.0,
        'volume': 1000000
    }
    
    processed_data = market_data_fetcher._process_market_data(test_data)
    assert processed_data['symbol'] == 'RELIANCE-EQ'
    assert processed_data['ltp'] == 2500.0
    assert processed_data['change'] == 10.0  # ltp - close
    assert isinstance(processed_data['change_percent'], float)

def test_market_status(market_data_fetcher):
    """Test if market status is correctly determined"""
    status = market_data_fetcher._get_market_status()
    assert status in ['OPEN', 'CLOSED'] 