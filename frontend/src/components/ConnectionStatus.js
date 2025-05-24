import React from 'react';
import './ConnectionStatus.css';

function ConnectionStatus({ show, isConnected, isAttemptingReconnect, serverIssueDetected, onRetry }) {
  if (!show) return null;
  
  let message = 'Connecting to server...'; // Default initial message
  if (isConnected) {
    message = 'Connected to server successfully!';
  } else if (serverIssueDetected) {
    message = 'Unable to connect to the server. It might be offline or experiencing issues. Retrying...';
    if (!isAttemptingReconnect) { // If all retries failed
        message = 'Failed to connect to the server. It appears to be offline or experiencing issues. Please try again later.';
    }
  } else if (isAttemptingReconnect) {
    message = 'Attempting to reconnect to server...';
  } else { // Not connected, not attempting, and no specific server issue detected (yet)
    message = 'Disconnected from server. Please check your connection or retry.';
  }

  return (
    <div className="modal">
      <div className="modal-content">
        <div className="modal-header">
          <h3>Connection Status</h3>
        </div>
        <div className="modal-body">
          <p className="connection-status-message">
            {message}
          </p>
          
          {(!isConnected || isAttemptingReconnect) && (
            <div className="loader"></div>
          )}

          {!isConnected && (
            <button onClick={onRetry} className="retry-button">
              Retry Connection
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

export default ConnectionStatus;