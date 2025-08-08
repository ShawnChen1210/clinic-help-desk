import { createContext, useContext } from 'react';

// Create a context with a default value of null
export const SpreadsheetContext = createContext(null);

// Create a custom hook for easy access
export function useSpreadsheet() {
  return useContext(SpreadsheetContext);
}