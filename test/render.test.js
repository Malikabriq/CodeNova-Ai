import React from 'react';
import ReactDOM from 'react-dom/client';
import NavigationBar from './NavigationBar';

// Mock DOM environment for testing
global.document = {
  createElement: () => ({ appendChild: () => {} }),
  createTextNode: () => ({}),
  querySelector: () => ({ appendChild: () => {} })
};

global.window = {
  location: { href: '' }
};

// Test rendering
try {
  const container = document.createElement('div');
  const root = ReactDOM.createRoot(container);
  
  // This should render without throwing errors
  root.render(React.createElement(NavigationBar));
  
  console.log('SUCCESS: NavigationBar rendered without errors');
} catch (error) {
  console.error('ERROR:', error.message);
}