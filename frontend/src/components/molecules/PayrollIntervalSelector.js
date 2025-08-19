import React, { useState, useEffect } from 'react';

export default function PayrollIntervalSelector({
  payrollDates,
  onIntervalSelect,
  selectedInterval,
  className = ""
}) {
  const [intervals, setIntervals] = useState([]);

  useEffect(() => {
    if (payrollDates && payrollDates.length > 0) {
      generatePayrollIntervals();
    }
  }, [payrollDates]);

  const generatePayrollIntervals = () => {
    const today = new Date();
    const intervals = [];

    // Get payroll dates and sort them
    const sortedPayrollDates = [...payrollDates].sort((a, b) => {
      if (a === 'end of month') return 1;
      if (b === 'end of month') return -1;
      return parseInt(a) - parseInt(b);
    });

    // Generate intervals for the past 12 months
    for (let monthsBack = 0; monthsBack < 12; monthsBack++) {
      const currentDate = new Date(today.getFullYear(), today.getMonth() - monthsBack, 1);

      // Generate intervals for this month
      for (let i = 0; i < sortedPayrollDates.length; i++) {
        const currentPayrollDate = sortedPayrollDates[i];

        let startDate, endDate;

        if (i === 0) {
          // First interval of the month starts on the 1st
          startDate = new Date(currentDate.getFullYear(), currentDate.getMonth(), 1);
        } else {
          // Subsequent intervals start the day after the previous payroll date
          const prevDate = sortedPayrollDates[i - 1];
          if (prevDate === 'end of month') {
            // If previous was end of month, start from 1st of current month
            startDate = new Date(currentDate.getFullYear(), currentDate.getMonth(), 1);
          } else {
            startDate = new Date(currentDate.getFullYear(), currentDate.getMonth(), parseInt(prevDate) + 1);
          }
        }

        // Set end date
        if (currentPayrollDate === 'end of month') {
          // End of month - get last day of the month
          endDate = new Date(currentDate.getFullYear(), currentDate.getMonth() + 1, 0);
        } else {
          endDate = new Date(currentDate.getFullYear(), currentDate.getMonth(), parseInt(currentPayrollDate));
        }

        // Only add if the interval is valid and in the past or current
        if (startDate <= endDate && endDate <= today) {
          intervals.push({
            id: `${currentDate.getFullYear()}-${currentDate.getMonth()}-${i}`,
            startDate: startDate,
            endDate: endDate,
            label: `${startDate.toLocaleDateString('en-US', { month: 'long', day: 'numeric' })} - ${endDate.toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' })}`,
            monthYear: `${currentDate.toLocaleDateString('en-US', { month: 'long', year: 'numeric' })}`
          });
        }
      }
    }

    setIntervals(intervals);
  };

  const handleIntervalChange = (e) => {
    const intervalId = e.target.value;
    const interval = intervals.find(i => i.id === intervalId);
    onIntervalSelect(interval || null);
  };

  if (!payrollDates || payrollDates.length === 0) {
    return (
      <div className={`bg-yellow-50 border border-yellow-200 rounded-md p-4 ${className}`}>
        <p className="text-yellow-800">
          No payroll dates configured for this user.
        </p>
      </div>
    );
  }

  if (intervals.length === 0) {
    return (
      <div className={`bg-yellow-50 border border-yellow-200 rounded-md p-4 ${className}`}>
        <p className="text-yellow-800">
          No payroll intervals available. This may occur if all intervals are in the future.
        </p>
      </div>
    );
  }

  return (
    <div className={`space-y-4 ${className}`}>
      {/* Payroll Dates Display */}
      <div className="bg-gray-50 border border-gray-200 rounded-md p-3">
        <p className="text-sm font-medium text-gray-700 mb-1">
          Configured Payroll Dates:
        </p>
        <p className="text-sm text-gray-600">
          {payrollDates.join(', ')}
        </p>
      </div>

      {/* Interval Selector */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Select Payroll Interval
        </label>
        <select
          value={selectedInterval?.id || ''}
          onChange={handleIntervalChange}
          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
        >
          <option value="">Select an interval...</option>
          {intervals.map((interval) => (
            <option key={interval.id} value={interval.id}>
              {interval.label}
            </option>
          ))}
        </select>
      </div>

      {/* Selected Interval Details */}
      {selectedInterval && (
        <div className="bg-blue-50 border border-blue-200 rounded-md p-4">
          <h4 className="font-medium text-blue-900 mb-2">Selected Interval</h4>
          <div className="space-y-1 text-sm">
            <p className="text-blue-800">
              <span className="font-medium">Period:</span> {selectedInterval.label}
            </p>
            <p className="text-blue-800">
              <span className="font-medium">Start Date:</span> {selectedInterval.startDate.toLocaleDateString()}
            </p>
            <p className="text-blue-800">
              <span className="font-medium">End Date:</span> {selectedInterval.endDate.toLocaleDateString()}
            </p>
            <p className="text-blue-800">
              <span className="font-medium">Duration:</span> {Math.ceil((selectedInterval.endDate - selectedInterval.startDate) / (1000 * 60 * 60 * 24)) + 1} days
            </p>
          </div>
        </div>
      )}

      {/* Quick Stats */}
      <div className="text-xs text-gray-500">
        Showing {intervals.length} available payroll intervals from the past 12 months
      </div>
    </div>
  );
}