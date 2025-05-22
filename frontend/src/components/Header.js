import React from 'react';
import './Header.css';

function Header({ isConnected, marketData, lastUpdate, onRefresh }) {
  // Get NIFTY50 index value
  const niftyIndex = Object.values(marketData).find(item => 
    item.symbol === 'NIFTY50-INDEX'
  );
  
  // Format the last update time
  const formatTime = (date) => {
    if (!date) return '-';
    return date.toLocaleTimeString();
  };

  // Get connection status text
  const connectionStatus = isConnected ? 'Connected' : 'Disconnected';

  // Calculate NIFTY50 change and direction
  const niftyChange = niftyIndex ? niftyIndex.change : 0;
  const niftyChangePercent = niftyIndex ? niftyIndex.change_percent : 0;
  const niftyDirection = niftyIndex ? (niftyChange > 0 ? 'up' : niftyChange < 0 ? 'down' : null) : null;
  const niftyColorClass = niftyChange > 0 ? 'positive-value' : niftyChange < 0 ? 'negative-value' : '';

  return (
    <header className="header">
      <div className="container">
        <div className="header-content">
          <div className="logo">
            <h1>NIFTY50 Trading Dashboard</h1>
          </div>
          
          <div className="market-status">
            <div className="market-indicator">
              <span className="indicator-label">Market Status:</span>
              <span className={`indicator-value ${isConnected ? 'connected' : 'disconnected'}`}>
                {connectionStatus}
              </span>
            </div>
            
            <div className="market-indicator nifty-index">
              <span className="indicator-label">NIFTY50:</span>
              <span className={`indicator-value ${niftyColorClass}`}>
                {niftyIndex ? niftyIndex.ltp.toFixed(2) : '-'}
                {niftyDirection && (
                  <span className={`change-indicator ${niftyDirection}`}>
                    {niftyDirection === 'up' ? '↑' : '↓'}
                  </span>
                )}
                <span className="change-value">
                  ({niftyChange.toFixed(2)} | {niftyChangePercent.toFixed(2)}%)
                </span>
              </span>
            </div>
            
            <div className="market-indicator">
              <span className="indicator-label">Last Update:</span>
              <span className="indicator-value">
                {formatTime(lastUpdate)}
              </span>
            </div>

            <button 
              className="refresh-button"
              onClick={onRefresh}
              title="Refresh Data"
            >
              ↻
            </button>
          </div>
        </div>
      </div>
    </header>
  );
}

export default Header; 