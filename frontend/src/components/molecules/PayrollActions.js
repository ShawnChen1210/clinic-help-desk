import React from 'react';

export default function PayrollActions({
  onBack,
  onSendPayroll,
  isSending = false,
  canSend = true,
  className = ""
}) {
  return (
    <div className={`flex items-center justify-between space-x-4 ${className}`}>
      <button
        onClick={onBack}
        disabled={isSending}
        className="px-6 py-2 bg-gray-600 text-white rounded-md hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-gray-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
      >
        Back to Members
      </button>

      <div className="flex space-x-3">
        <button
          onClick={onSendPayroll}
          disabled={!canSend || isSending}
          className={`px-6 py-2 rounded-md font-medium focus:outline-none focus:ring-2 focus:ring-offset-2 transition-colors ${
            !canSend || isSending
              ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
              : 'bg-green-600 text-white hover:bg-green-700 focus:ring-green-500'
          }`}
        >
          {isSending ? (
            <div className="flex items-center">
              <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
              Sending...
            </div>
          ) : (
            'Send Payroll'
          )}
        </button>
      </div>
    </div>
  );
}