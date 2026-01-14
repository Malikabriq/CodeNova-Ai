import React from 'react';
import { createRoot } from 'react-dom/client';
import NavigationBar from './NavigationBar';

// Create a simple test wrapper
const TestApp = () => {
  return (
    <div>
      <NavigationBar />
    </div>
  );
};

// This would normally be where we render the component
// For testing purposes, we're just verifying the import works
console.log('NavigationBar component imported successfully');

export default TestApp;