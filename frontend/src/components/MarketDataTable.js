import React, { useState, useMemo, useEffect, useRef } from 'react';
import DataTable from 'react-data-table-component';
import Tooltip from './Tooltip';
import './MarketDataTable.css';

// Utility function to safely format numeric values
const safeFormatNumber = (value, decimals = 2) => {
  if (value === undefined || value === null || isNaN(value)) {
    return '0.00';
  }
  
  // Convert to number if it's a string
  const num = typeof value === 'string' ? parseFloat(value) : value;
  
  // Check if it's a valid number after conversion
  if (isNaN(num)) {
    return '0.00';
  }
  
  return num.toFixed(decimals);
};

// Value Cell component with change animation
const ValueCell = ({ value, changed, direction, format = 'number', isChangeColumn = false, suffix = '' }) => {
  const formattedValue = format === 'number' ? value.toFixed(2) : value;
  const directionClass = direction ? `change-${direction}` : '';
  const changedClass = changed ? 'value-changed' : '';
  const valueClass = isChangeColumn ? (value > 0 ? 'positive-value' : value < 0 ? 'negative-value' : '') : '';
  
  return (
    <Tooltip content={`${format === 'number' ? 'Value' : 'Volume'}: ${formattedValue}${suffix}`}>
      <div className={`value-cell ${directionClass} ${changedClass} ${valueClass}`}>
        {formattedValue}
        {suffix && <span className="suffix">{suffix}</span>}
        {direction && (
          <span className={`change-indicator ${direction}`}>
            {direction === 'up' ? '↑' : '↓'}
          </span>
        )}
      </div>
    </Tooltip>
  );
};

// Signal Cell component with enhanced visual indicators
const SignalCell = ({ signal, changed }) => {
  const signalClass = signal.toLowerCase();
  const changedClass = changed ? 'changed' : '';
  const signalColorClass = signal === 'BUY' ? 'signal-buy' : signal === 'SELL' ? 'signal-sell' : 'signal-hold';
  
  return (
    <Tooltip content={`Trading Signal: ${signal}`}>
      <div className={`signal-cell ${signalClass} ${changedClass} ${signalColorClass}`}>
        {signal}
      </div>
    </Tooltip>
  );
};

function MarketDataTable({ marketData }) {
  const [filterSignal, setFilterSignal] = useState('all');
  const [searchTerm, setSearchTerm] = useState('');
  const [dataWithDefaults, setDataWithDefaults] = useState({});
  const prevDataRef = useRef({});
  
  // Add default values and handle changes
  useEffect(() => {
    if (!marketData || Object.keys(marketData).length === 0) return;

    const processedData = {};
    Object.entries(marketData).forEach(([key, item]) => {
      const prevItem = prevDataRef.current[key] || {};
      
      // Calculate changes and directions
      const changes = {
        ltp: { value: item.ltp, prev: prevItem.ltp },
        open: { value: item.open, prev: prevItem.open },
        high: { value: item.high, prev: prevItem.high },
        low: { value: item.low, prev: prevItem.low },
        close: { value: item.close, prev: prevItem.close },
        volume: { value: item.volume, prev: prevItem.volume }
      };

      // Process changes and directions
      const processedChanges = {};
      Object.entries(changes).forEach(([field, { value, prev }]) => {
        const changed = value !== prev;
        const direction = changed ? (value > prev ? 'up' : 'down') : null;
        processedChanges[field] = { changed, direction };
      });

      // Calculate real-time change and change percentage using LTP
      const change = item.ltp - item.close;
      const change_percent = (change / item.close) * 100;

      // Calculate trading signal
      const shortTermTrend = item.ltp > item.close ? 'up' : 'down';
      const volatility = ((item.high - item.low) / item.close) * 100;
      
      let trading_signal = 'HOLD';
      if (shortTermTrend === 'up' && change_percent > 1 && volatility < 5) {
        trading_signal = 'BUY';
      } else if (shortTermTrend === 'down' && change_percent < -1 && volatility < 5) {
        trading_signal = 'SELL';
      }
      
      const signal_changed = prevItem.trading_signal !== trading_signal;
      
      processedData[key] = {
        symbol: item.symbol || 'UNKNOWN',
        ltp: typeof item.ltp === 'number' ? item.ltp : 0,
        open: typeof item.open === 'number' ? item.open : 0,
        high: typeof item.high === 'number' ? item.high : 0,
        low: typeof item.low === 'number' ? item.low : 0,
        close: typeof item.close === 'number' ? item.close : 0,
        volume: typeof item.volume === 'number' ? item.volume : 0,
        change,
        change_percent,
        trading_signal,
        timestamp: item.timestamp || new Date().toISOString(),
        
        // Change indicators
        ltp_changed: processedChanges.ltp.changed,
        open_changed: processedChanges.open.changed,
        high_changed: processedChanges.high.changed,
        low_changed: processedChanges.low.changed,
        close_changed: processedChanges.close.changed,
        volume_changed: processedChanges.volume.changed,
        signal_changed,
        
        // Change directions
        ltp_direction: processedChanges.ltp.direction,
        open_direction: processedChanges.open.direction,
        high_direction: processedChanges.high.direction,
        low_direction: processedChanges.low.direction,
        close_direction: processedChanges.close.direction,
        volume_direction: processedChanges.volume.direction,
        
        // Previous values
        prev_ltp: prevItem.ltp || 0,
        prev_open: prevItem.open || 0,
        prev_high: prevItem.high || 0,
        prev_low: prevItem.low || 0,
        prev_close: prevItem.close || 0,
        prev_volume: prevItem.volume || 0,
      };
    });
    
    setDataWithDefaults(processedData);
    prevDataRef.current = processedData;
  }, [marketData]);
  
  // Filter data based on selected trading signal and search term
  const filteredData = useMemo(() => {
    if (!dataWithDefaults || Object.keys(dataWithDefaults).length === 0) {
      return [];
    }
    
    return Object.values(dataWithDefaults)
      .filter(item => {
        // Skip NIFTY50 index in the table
        if (item.symbol === 'NIFTY50-INDEX') {
          return false;
        }
        
        // Apply signal filter
        const matchesSignal = filterSignal === 'all' || item.trading_signal === filterSignal;
        
        // Apply search filter
        const matchesSearch = searchTerm === '' || 
          item.symbol.toLowerCase().includes(searchTerm.toLowerCase());
        
        return matchesSignal && matchesSearch;
      })
      .sort((a, b) => a.symbol.localeCompare(b.symbol));
  }, [dataWithDefaults, filterSignal, searchTerm]);

  // Define columns for DataTable
  const columns = [
    {
      name: 'Symbol',
      selector: row => row.symbol,
      sortable: true,
      width: '120px',
      cell: row => (
        <Tooltip content={`Symbol: ${row.symbol}`}>
          <div className="symbol-cell">
            {row.symbol}
          </div>
        </Tooltip>
      ),
    },
    {
      name: 'LTP',
      selector: row => row.ltp,
      sortable: true,
      right: true,
      cell: row => (
        <ValueCell
          value={row.ltp}
          changed={row.ltp_changed}
          direction={row.ltp_direction}
        />
      ),
    },
    {
      name: 'Open',
      selector: row => row.open,
      sortable: true,
      right: true,
      cell: row => (
        <ValueCell
          value={row.open}
          changed={row.open_changed}
          direction={row.open_direction}
        />
      ),
    },
    {
      name: 'High',
      selector: row => row.high,
      sortable: true,
      right: true,
      cell: row => (
        <ValueCell
          value={row.high}
          changed={row.high_changed}
          direction={row.high_direction}
        />
      ),
    },
    {
      name: 'Low',
      selector: row => row.low,
      sortable: true,
      right: true,
      cell: row => (
        <ValueCell
          value={row.low}
          changed={row.low_changed}
          direction={row.low_direction}
        />
      ),
    },
    {
      name: 'Close',
      selector: row => row.close,
      sortable: true,
      right: true,
      cell: row => (
        <ValueCell
          value={row.close}
          changed={row.close_changed}
          direction={row.close_direction}
        />
      ),
    },
    {
      name: 'Volume',
      selector: row => row.volume,
      sortable: true,
      right: true,
      cell: row => (
        <ValueCell
          value={row.volume}
          changed={row.volume_changed}
          direction={row.volume_direction}
          format="integer"
        />
      ),
    },
    {
      name: 'Change',
      selector: row => row.change,
      sortable: true,
      right: true,
      cell: row => (
        <ValueCell
          value={row.change}
          changed={row.change_changed}
          direction={row.change_direction}
          isChangeColumn={true}
        />
      ),
    },
    {
      name: 'Change%',
      selector: row => row.change_percent,
      sortable: true,
      right: true,
      cell: row => (
        <ValueCell
          value={row.change_percent} 
          changed={row.change_percent_changed}
          direction={row.change_percent_direction}
          isChangeColumn={true}
          suffix="%"
        />
      ),
    },
    {
      name: 'Signal',
      selector: row => row.trading_signal,
      sortable: true,
      right: true,
      cell: row => (
        <SignalCell
          signal={row.trading_signal}
          changed={row.signal_changed}
        />
      ),
    }
  ];

  // Add filter controls for trading signals and search
  const handleSignalFilterChange = (e) => {
    setFilterSignal(e.target.value);
  };

  const handleSearchChange = (e) => {
    setSearchTerm(e.target.value);
  };

  // Custom styles for DataTable
  const customStyles = {
    headRow: {
      style: {
        backgroundColor: 'var(--card-background)',
        borderBottom: '2px solid var(--border-color)',
      },
    },
    headCells: {
      style: {
        fontSize: '0.875rem',
        fontWeight: '600',
        color: 'var(--text-primary)',
        paddingLeft: '1rem',
        paddingRight: '1rem',
      },
    },
    rows: {
      style: {
        fontSize: '0.875rem',
        fontWeight: '400',
        color: 'var(--text-primary)',
        backgroundColor: 'var(--card-background)',
        minHeight: '48px',
        '&:not(:last-of-type)': {
          borderBottomStyle: 'solid',
          borderBottomWidth: '1px',
          borderBottomColor: 'var(--border-color)',
        },
      },
      highlightOnHoverStyle: {
        backgroundColor: 'var(--hover-background)',
        borderBottomColor: 'var(--border-color)',
        outline: '0px solid var(--border-color)',
        transition: 'all 0.2s ease-in-out',
        color: 'var(--text-hover)', // Brighter text color on hover
      },
    },
    cells: {
      style: {
        paddingLeft: '1rem',
        paddingRight: '1rem',
      },
    },
  };

  // Render filter controls
  const renderFilterControls = () => (
    <div className="filter-controls">
      <div className="search-box">
        <input
          type="text"
          placeholder="Search symbols..."
          value={searchTerm}
          onChange={handleSearchChange}
          className="search-input"
        />
      </div>
      <div className="signal-filter">
        <label>
          <span>Filter by Signal:</span>
          <select value={filterSignal} onChange={handleSignalFilterChange}>
            <option value="all">All Signals</option>
            <option value="BUY">Buy</option>
            <option value="SELL">Sell</option>
            <option value="HOLD">Hold</option>
          </select>
        </label>
      </div>
    </div>
  );

  return (
    <div className="market-data-container">
      {renderFilterControls()}
      <DataTable
        columns={columns}
        data={filteredData}
        customStyles={customStyles}
        pagination
        paginationPerPage={50}
        paginationRowsPerPageOptions={[25, 50, 100]}
        highlightOnHover
        noDataComponent={<div className="no-data">No market data available</div>}
        fixedHeader
        fixedHeaderScrollHeight="60vh"
      />
    </div>
  );
}

export default MarketDataTable; 