import React from 'react';
import './ConnectionStatus.css';

function ConnectionStatus({ show, isConnected }) {
  if (!show) return null;
  
  return (
    <div className="modal">
      <div className="modal-content">
        <div className="modal-header">
          <h3>Connection Status</h3>
        </div>
        <div className="modal-body">
          <p className="connection-status-message">
            {isConnected 
              ? 'Connected to server successfully!'
              : 'Connecting to server...'}
          </p>
          
          {!isConnected && (
            <div className="loader"></div>
          )}
        </div>
      </div>
    </div>
  );
}

export default ConnectionStatus; 