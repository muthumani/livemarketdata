import React, { useState, useEffect, useCallback } from 'react';
import { io } from 'socket.io-client';
import Header from './components/Header';
import MarketDataTable from './components/MarketDataTable';
import Footer from './components/Footer';
import ConnectionStatus from './components/ConnectionStatus';
import './App.css';

// Socket.io connection
let socket;

function App() {
  const [marketData, setMarketData] = useState({});
  const [isConnected, setIsConnected] = useState(false);
  const [lastUpdate, setLastUpdate] = useState(null);
  const [showConnectionModal, setShowConnectionModal] = useState(true);
  const [isAttemptingReconnect, setIsAttemptingReconnect] = useState(false);
  const [serverIssueDetected, setServerIssueDetected] = useState(false); // New state for server issues

  const connectSocket = useCallback(() => {
    // Ensure previous socket is cleaned up if re-initializing
    if (socket && socket.connected) {
      socket.disconnect();
    }
    if (socket) {
        socket.off(); // Remove all listeners before re-assigning
    }

    const socketUrl = process.env.NODE_ENV === 'production'
      ? window.location.origin
      : 'http://localhost:5000';
    
    console.log('Attempting to connect to socket server at:', socketUrl);
    setShowConnectionModal(true); // Show modal when attempting to connect
    setIsAttemptingReconnect(true); // Indicate an attempt is in progress

    socket = io(socketUrl, {
      reconnection: true,
      reconnectionAttempts: 5,
      reconnectionDelay: 1000,
      reconnectionDelayMax: 5000,
      timeout: 10000,
      transports: ['websocket', 'polling'],
      secure: false,
      rejectUnauthorized: false,
      path: '/socket.io/',
      autoConnect: false,
    });

    socket.on('connect', () => {
      console.log('Socket connected successfully');
      setIsConnected(true);
      setShowConnectionModal(false);
      setIsAttemptingReconnect(false);
      setServerIssueDetected(false); // Reset server issue flag on successful connect
    });

    socket.on('disconnect', (reason) => {
      console.log('Socket disconnected:', reason);
      setIsConnected(false);
      setShowConnectionModal(true);
      if (reason === 'io client disconnect') {
        setIsAttemptingReconnect(false);
        setServerIssueDetected(false); // Client initiated, not a server issue
      } else {
        setIsAttemptingReconnect(true);
        // Reasons like 'transport error' or 'ping timeout' strongly suggest server-side issues
        if (reason === 'transport error' || reason === 'ping timeout') {
          console.warn('Disconnect reason suggests server issue:', reason);
          setServerIssueDetected(true);
        }
        // For other reasons, we might not immediately flag serverIssueDetected,
        // connect_error or reconnect_failed will be more definitive.
      }
    });

    socket.on('connect_error', (error) => {
      console.error('Socket connection error:', error);
      setIsConnected(false);
      setShowConnectionModal(true);
      setIsAttemptingReconnect(true);
      setServerIssueDetected(true); // Connection error strongly implies server issue
    });

    socket.on('reconnect_attempt', (attemptNumber) => {
      console.log(`Socket reconnect attempt ${attemptNumber}`);
      setIsAttemptingReconnect(true);
      setShowConnectionModal(true);
      // Potentially reset serverIssueDetected here if we want to give server a chance with each attempt
      // For now, let's keep it true if a connect_error previously set it.
    });
    
    socket.on('reconnect_failed', () => {
      console.error('Socket reconnection failed after all attempts.');
      setIsAttemptingReconnect(false);
      setServerIssueDetected(true); // All attempts failed, likely a persistent server issue
    });

    socket.on('market_data', (data) => {
      console.log('Received market data update:', data);
      if (data && data.data) {
        setMarketData(data.data);
        setLastUpdate(new Date());
        setIsConnected(true);
        setShowConnectionModal(false);
        setIsAttemptingReconnect(false);
      } else {
        console.warn('Received invalid market data format:', data);
      }
    });
    
    socket.connect(); // Manually connect

  }, []);

  useEffect(() => {
    connectSocket(); // Initial connection attempt

    return () => {
      if (socket) {
        socket.disconnect();
        socket.off();
      }
    };
  }, [connectSocket]);

  const handleManualReconnect = () => {
    console.log('Manual reconnect triggered.');
    setServerIssueDetected(false); // Reset server issue flag on manual reconnect attempt
    if (socket && !socket.connected) {
      setShowConnectionModal(true);
      setIsAttemptingReconnect(true);
      socket.connect();
    } else if (!socket) {
      connectSocket(); // This will also set isAttemptingReconnect and show modal
    }
  };

  // Refresh market data
  const handleRefresh = () => {
    const apiUrl = process.env.NODE_ENV === 'production' 
      ? '/api/market-data'
      : 'http://localhost:5000/api/market-data';

    console.log('Fetching market data from:', apiUrl);
    
    fetch(apiUrl)
      .then(response => {
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        return response.json();
      })
      .then(data => {
        // console.log('Received market data from API:', data);
        if (data && data.status === 'success' && data.data) {
          setMarketData(data.data);
          setLastUpdate(new Date());
          setIsConnected(true);
          setShowConnectionModal(false);
        } else {
          console.warn('Invalid data format received:', data);
          setIsConnected(false);
          setShowConnectionModal(true);
        }
      })
      .catch(error => {
        console.error('Error fetching market data:', error);
        setIsConnected(false);
        setShowConnectionModal(true);
      });
  };

  return (
    <div className="app">
      {/* Connection status modal */}
      <ConnectionStatus
        show={showConnectionModal}
        isConnected={isConnected}
        isAttemptingReconnect={isAttemptingReconnect}
        serverIssueDetected={serverIssueDetected} // Pass new state
        onRetry={handleManualReconnect}
      />

      {/* Header */}
      <Header 
        isConnected={isConnected} 
        marketData={marketData} 
        lastUpdate={lastUpdate}
        onRefresh={handleRefresh}
      />

      {/* Main content */}
      <main>
        <div className="container">
          {/* Market data table */}
          <MarketDataTable marketData={marketData} />
        </div>
      </main>

      {/* Footer */}
      <Footer />
    </div>
  );
}

export default App; 