import React, { useState, useEffect } from 'react';
import { useParams, useNavigate, useLocation } from 'react-router-dom';
import api from '../utils/axiosConfig';
import PayrollSummaryTable from '../components/organisms/PayrollSummaryTable';
import PayrollActions from '../components/molecules/PayrollActions';
import { useDateFormatter } from '../hooks/useDateFormatter';

export default function ConfirmPayroll() {
  const { userId, clinic_id } = useParams();
  const navigate = useNavigate();
  const location = useLocation();
  const { formatDateString } = useDateFormatter();

  const [payrollData, setPayrollData] = useState(null);
  const [notes, setNotes] = useState('');
  const [isSending, setIsSending] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (location.state?.payrollData) {
      setPayrollData(location.state.payrollData);
    } else {
      navigate(`/chd-app/${clinic_id}/payroll/${userId}`);
    }
  }, [location.state, navigate, clinic_id, userId]);

  const handleBack = () => {
    navigate(`/chd-app/${clinic_id}/members`);
  };

  const handleSendPayroll = async () => {
    if (!payrollData) {
      setError('No payroll data available');
      return;
    }

    setIsSending(true);
    setError(null);

    try {
      const payrollPayload = {
        ...payrollData,
        notes: notes.trim(),
      };

      const response = await api.post(`/api/payroll/${userId}/send_payroll/`, payrollPayload);

      if (response.status === 200) {
        alert(`Payroll sent successfully! ${payrollData.user_name} will receive an email with their payslip.`);
        navigate(`/chd-app/${clinic_id}/members`);
      }
    } catch (error) {
      console.error('Error sending payroll:', error);
      let errorMessage = 'Failed to send payroll. Please try again.';

      if (error.response?.data?.error) {
        errorMessage = error.response.data.error;
      } else if (error.response?.status === 403) {
        errorMessage = 'You do not have permission to send payroll.';
      } else if (error.response?.status === 400) {
        errorMessage = 'Invalid payroll data. Please check the information and try again.';
      }

      setError(errorMessage);
    } finally {
      setIsSending(false);
    }
  };

  if (!payrollData) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading payroll data...</p>
        </div>
      </div>
    );
  }

  const companyInfo = {
    name: 'Alternative Therapy On the Go Inc.',
    address: '23 - 7330 122nd Street, Surrey, BC V3W 1B4'
  };

  return (
    <div className="space-y-6 max-w-5xl mx-auto">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Confirm Payroll</h1>
          <p className="text-gray-600 mt-2">
            Review and confirm payroll for {payrollData.user_name}
          </p>
        </div>
      </div>

      {/* Error Message */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-md p-4">
          <h3 className="text-red-800 font-medium">Error</h3>
          <p className="text-red-600 mt-1">{error}</p>
          <button
            onClick={() => setError(null)}
            className="mt-2 px-3 py-1 bg-red-100 text-red-800 rounded text-sm hover:bg-red-200"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Payroll Summary */}
      <div className="bg-white shadow-lg rounded-lg overflow-hidden">
        <PayrollSummaryTable
          payrollData={payrollData}
          companyInfo={companyInfo}
        />
      </div>

      {/* Notes Section */}
      <div className="bg-white shadow rounded-lg p-6">
        <h3 className="text-lg font-semibold text-gray-800 mb-4">Additional Notes</h3>
        <textarea
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          placeholder="Add any additional notes for this payroll (optional)..."
          rows={4}
          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 resize-vertical"
          maxLength={500}
          disabled={isSending}
        />
        <div className="text-sm text-gray-500 mt-1">
          {notes.length}/500 characters
        </div>
      </div>

      {/* Summary Info */}
      <div className="bg-blue-50 border border-blue-200 rounded-md p-4">
        <h4 className="font-medium text-blue-900 mb-2">Payroll Summary</h4>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
          <div>
            <span className="font-medium text-blue-800">Employee:</span>
            <p className="text-blue-700">{payrollData.user_name}</p>
          </div>
          <div>
            <span className="font-medium text-blue-800">Pay Period:</span>
            <p className="text-blue-700">
              {formatDateString(payrollData.pay_period_start)} - {formatDateString(payrollData.pay_period_end)}
            </p>
          </div>
          <div>
            <span className="font-medium text-blue-800">Net Payment:</span>
            <p className="text-blue-700 font-bold">
              {new Intl.NumberFormat('en-CA', {
                style: 'currency',
                currency: 'CAD'
              }).format(payrollData.totals?.net_payment || 0)}
            </p>
          </div>
        </div>

        {/* Additional details */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm mt-4 pt-4 border-t border-blue-200">
          <div>
            <span className="font-medium text-blue-800">Role:</span>
            <p className="text-blue-700">{payrollData.role_type}</p>
          </div>
          <div>
            <span className="font-medium text-blue-800">Hours Worked:</span>
            <p className="text-blue-700">{payrollData.total_hours} hours</p>
          </div>
          <div>
            <span className="font-medium text-blue-800">Hourly Rate:</span>
            <p className="text-blue-700">
              {new Intl.NumberFormat('en-CA', {
                style: 'currency',
                currency: 'CAD'
              }).format(payrollData.hourly_wage || 0)}
            </p>
          </div>
        </div>
      </div>

      {/* Actions */}
      <div className="bg-white shadow rounded-lg p-6">
        <PayrollActions
          onBack={handleBack}
          onSendPayroll={handleSendPayroll}
          isSending={isSending}
          canSend={true}
        />

        <div className="mt-4 text-sm text-gray-600">
          <p>
            <strong>Note:</strong> Clicking "Send Payroll" will:
          </p>
          <ul className="list-disc list-inside mt-2 space-y-1">
            <li>Email the payslip to {payrollData.user_name}'s registered email address</li>
            <li>Update the employee's year-to-date (YTD) pay totals</li>
            <li>Mark this payroll as processed in the system</li>
            {notes.trim() && <li>Include your additional notes in the payslip email</li>}
          </ul>
        </div>
      </div>
    </div>
  );
}