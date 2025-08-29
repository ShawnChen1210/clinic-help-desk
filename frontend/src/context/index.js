// contexts/index.js - Context composition
import React from 'react';
import { ClinicProvider } from './ClinicContext';


// Compose all providers into one
export const AppProviders = ({ children }) => {
  return (
      <ClinicProvider>
        {children}
      </ClinicProvider>
  );
};

// Export all hooks for easy importing
