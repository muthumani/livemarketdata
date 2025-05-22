import React, { useState, useEffect } from 'react';
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

  // Initialize Socket.io connection
  useEffect(() => {
    // Backend URL (using proxy in package.json for development)
    const socketUrl = process.env.NODE_ENV === 'production' 
      ? window.location.origin
      : 'http://localhost:5000';
    
    console.log('Connecting to socket server at:', socketUrl);
    
    socket = io(socketUrl, {
      reconnectionAttempts: 5,
      reconnectionDelay: 1000,
      timeout: 10000,
      transports: ['websocket', 'polling'],
      secure: false,
      rejectUnauthorized: false,
      path: '/socket.io/',
      forceNew: true,
      autoConnect: true,
      upgrade: true
    });

    // Socket event handlers
    socket.on('connect', () => {
      console.log('Socket connected successfully');
      setIsConnected(true);
      setShowConnectionModal(false);
    });

    socket.on('disconnect', () => {
      console.log('Socket disconnected');
      setIsConnected(false);
      setShowConnectionModal(true);
    });

    socket.on('connect_error', (error) => {
      console.error('Socket connection error:', error);
      setIsConnected(false);
      setShowConnectionModal(true);
    });

    socket.on('market_data', (data) => {
      console.log('Received market data update:', data);
      if (data && data.data) {
        setMarketData(data.data);
        setLastUpdate(new Date());
        setIsConnected(true);
        setShowConnectionModal(false);
      } else {
        console.warn('Received invalid market data format:', data);
      }
    });

    // Cleanup on unmount
    return () => {
      if (socket) {
        socket.disconnect();
        socket.off();
      }
    };
  }, []);

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