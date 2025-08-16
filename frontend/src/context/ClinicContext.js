import React, { createContext, useContext, useState } from 'react';
import api from '../utils/axiosConfig';

const ClinicContext = createContext();

export const useClinic = () => {
  const context = useContext(ClinicContext);
  if (!context) {
    throw new Error('useClinic must be used within a ClinicProvider');
  }
  return context;
};

export const ClinicProvider = ({ children }) => {
  const [clinicName, setClinicName] = useState('');
  const [sheets, setSheets] = useState({
    compensation_sales_sheet_id: null,
    daily_transaction_sheet_id: null,
    transaction_report_sheet_id: null,
    payment_transaction_sheet_id: null
  });
  const [loading, setLoading] = useState(false);

  const loadClinicData = async (clinicId) => {
    setLoading(true);
    try {
      const response = await api.get(`/api/clinics/${clinicId}/`);
      const data = response.data;

      setClinicName(data.name);
      setSheets({
        compensation_sales_sheet_id: data.compensation_sales_sheet_id,
        daily_transaction_sheet_id: data.daily_transaction_sheet_id,
        transaction_report_sheet_id: data.transaction_report_sheet_id,
        payment_transaction_sheet_id: data.payment_transaction_sheet_id
      });
    } catch (error) {
      console.error('Failed to load clinic data:', error);
    } finally {
      setLoading(false);
    }
  };

  // Helper to get sheet info by Google Sheets ID
  const getSheetInfo = (sheetId) => {
    const sheetTypes = {
      [sheets.compensation_sales_sheet_id]: { type: 'compensation_sales', label: 'Compensation + Sales Report' },
      [sheets.daily_transaction_sheet_id]: { type: 'daily_transaction', label: 'Daily Transaction Report' },
      [sheets.transaction_report_sheet_id]: { type: 'transaction_report', label: 'Transaction Report' },
      [sheets.payment_transaction_sheet_id]: { type: 'payment_transaction', label: 'Payment Transaction Report' }
    };

    return sheetTypes[sheetId] || null;
  };

  // Helper to get all available sheets
  const getAvailableSheets = () => {
    return Object.entries(sheets)
      .filter(([_, sheetId]) => sheetId)
      .map(([key, sheetId]) => ({
        googleSheetId: sheetId,
        type: key.replace('_sheet_id', ''),
        label: getSheetInfo(sheetId)?.label || key
      }));
  };

  return (
    <ClinicContext.Provider value={{
      clinicName,
      sheets,
      loading,
      loadClinicData,
      setSheets,
      getSheetInfo,
      getAvailableSheets
    }}>
      {children}
    </ClinicContext.Provider>
  );
};