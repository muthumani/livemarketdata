import React from 'react';
import './Footer.css';

function Footer() {
  const currentYear = new Date().getFullYear();
  
  return (
    <footer className="footer">
      <div className="container">
        <div className="footer-content">
          <p>&copy; {currentYear} NIFTY50 Trading Dashboard</p>
          <p>Powered by Fyers API</p>
        </div>
      </div>
    </footer>
  );
}

export default Footer; 