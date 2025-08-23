import React, { useState, useEffect } from 'react';

export default function PayrollIntervalSelector({
  paymentFrequency,
  onIntervalSelect,
  selectedInterval,
  className = ""
}) {
  const [intervals, setIntervals] = useState([]);

  useEffect(() => {
    if (paymentFrequency) {
      generatePayrollIntervals();
    }
  }, [paymentFrequency]);

  const generatePayrollIntervals = () => {
    const today = new Date();
    const intervals = [];

    switch (paymentFrequency) {
      case 'weekly':
        intervals.push(...generateWeeklyIntervals(today));
        break;
      case 'bi-weekly':
        intervals.push(...generateBiWeeklyIntervals(today));
        break;
      case 'semi-monthly':
        intervals.push(...generateSemiMonthlyIntervals(today));
        break;
      case 'monthly':
        intervals.push(...generateMonthlyIntervals(today));
        break;
      default:
        intervals.push(...generateSemiMonthlyIntervals(today)); // fallback
    }

    setIntervals(intervals);
  };

  const generateWeeklyIntervals = (today) => {
    const intervals = [];
    const currentDate = new Date(today);

    // Go back 12 weeks to get enough intervals
    for (let weeksBack = 0; weeksBack < 12; weeksBack++) {
      const targetDate = new Date(currentDate);
      targetDate.setDate(currentDate.getDate() - (weeksBack * 7));

      // Find Monday of the target week
      const monday = new Date(targetDate);
      const dayOfWeek = targetDate.getDay();
      const daysToMonday = dayOfWeek === 0 ? 6 : dayOfWeek - 1; // Sunday is 0
      monday.setDate(targetDate.getDate() - daysToMonday);

      // Find Sunday of the same week
      const sunday = new Date(monday);
      sunday.setDate(monday.getDate() + 6);

      // Only include if the week has ended (Sunday is in the past)
      if (sunday <= today) {
        intervals.push({
          id: `weekly-${monday.toISOString().split('T')[0]}`,
          startDate: monday,
          endDate: sunday,
          label: `Week of ${monday.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })} - ${sunday.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}`,
          frequencyType: 'weekly'
        });
      }
    }

    return intervals;
  };

  const generateBiWeeklyIntervals = (today) => {
    const intervals = [];
    const currentDate = new Date(today);

    // Go back 24 weeks (12 bi-weekly periods)
    for (let biWeeksBack = 0; biWeeksBack < 12; biWeeksBack++) {
      const targetDate = new Date(currentDate);
      targetDate.setDate(currentDate.getDate() - (biWeeksBack * 14));

      // Find Monday of the target bi-week period
      const monday = new Date(targetDate);
      const dayOfWeek = targetDate.getDay();
      const daysToMonday = dayOfWeek === 0 ? 6 : dayOfWeek - 1;
      monday.setDate(targetDate.getDate() - daysToMonday);

      // Find Sunday 2 weeks later
      const sunday = new Date(monday);
      sunday.setDate(monday.getDate() + 13); // 13 days later = 2 weeks

      // Only include if the period has ended
      if (sunday <= today) {
        intervals.push({
          id: `bi-weekly-${monday.toISOString().split('T')[0]}`,
          startDate: monday,
          endDate: sunday,
          label: `${monday.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })} - ${sunday.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })} (Bi-weekly)`,
          frequencyType: 'bi-weekly'
        });
      }
    }

    return intervals;
  };

  const generateSemiMonthlyIntervals = (today) => {
    const intervals = [];
    const currentDate = new Date(today);

    // Go back 12 months to get 24 semi-monthly periods
    for (let monthsBack = 0; monthsBack < 12; monthsBack++) {
      const targetMonth = new Date(currentDate.getFullYear(), currentDate.getMonth() - monthsBack, 1);

      // First half: 1st to 15th
      const firstHalfStart = new Date(targetMonth.getFullYear(), targetMonth.getMonth(), 1);
      const firstHalfEnd = new Date(targetMonth.getFullYear(), targetMonth.getMonth(), 15);

      // Second half: 16th to end of month
      const secondHalfStart = new Date(targetMonth.getFullYear(), targetMonth.getMonth(), 16);
      const secondHalfEnd = new Date(targetMonth.getFullYear(), targetMonth.getMonth() + 1, 0); // Last day of month

      // Add second half first (more recent)
      if (secondHalfEnd <= today) {
        intervals.push({
          id: `semi-monthly-2-${targetMonth.getFullYear()}-${targetMonth.getMonth()}`,
          startDate: secondHalfStart,
          endDate: secondHalfEnd,
          label: `${secondHalfStart.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })} - ${secondHalfEnd.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })} (Semi-monthly)`,
          frequencyType: 'semi-monthly'
        });
      }

      // Add first half
      if (firstHalfEnd <= today) {
        intervals.push({
          id: `semi-monthly-1-${targetMonth.getFullYear()}-${targetMonth.getMonth()}`,
          startDate: firstHalfStart,
          endDate: firstHalfEnd,
          label: `${firstHalfStart.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })} - ${firstHalfEnd.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })} (Semi-monthly)`,
          frequencyType: 'semi-monthly'
        });
      }
    }

    return intervals;
  };

  const generateMonthlyIntervals = (today) => {
    const intervals = [];
    const currentDate = new Date(today);

    // Go back 12 months
    for (let monthsBack = 1; monthsBack <= 12; monthsBack++) {
      const targetMonth = new Date(currentDate.getFullYear(), currentDate.getMonth() - monthsBack, 1);
      const monthStart = new Date(targetMonth.getFullYear(), targetMonth.getMonth(), 1);
      const monthEnd = new Date(targetMonth.getFullYear(), targetMonth.getMonth() + 1, 0); // Last day of month

      intervals.push({
        id: `monthly-${targetMonth.getFullYear()}-${targetMonth.getMonth()}`,
        startDate: monthStart,
        endDate: monthEnd,
        label: `${monthStart.toLocaleDateString('en-US', { month: 'long', year: 'numeric' })} (Monthly)`,
        frequencyType: 'monthly'
      });
    }

    return intervals;
  };

  const handleIntervalChange = (e) => {
    const intervalId = e.target.value;
    const interval = intervals.find(i => i.id === intervalId);
    onIntervalSelect(interval || null);
  };

  if (!paymentFrequency) {
    return (
      <div className={`bg-yellow-50 border border-yellow-200 rounded-md p-4 ${className}`}>
        <p className="text-yellow-800">
          No payment frequency configured for this user.
        </p>
      </div>
    );
  }

  if (intervals.length === 0) {
    return (
      <div className={`bg-yellow-50 border border-yellow-200 rounded-md p-4 ${className}`}>
        <p className="text-yellow-800">
          No payroll intervals available for {paymentFrequency} frequency.
        </p>
      </div>
    );
  }

  const getFrequencyDescription = () => {
    switch (paymentFrequency) {
      case 'weekly':
        return 'Full weeks from Monday to Sunday';
      case 'bi-weekly':
        return 'Two-week periods from Monday to Sunday';
      case 'semi-monthly':
        return '1st-15th and 16th-end of month';
      case 'monthly':
        return 'Full calendar months';
      default:
        return 'Semi-monthly periods';
    }
  };

  return (
    <div className={`space-y-4 ${className}`}>
      {/* Payment Frequency Display */}
      <div className="bg-gray-50 border border-gray-200 rounded-md p-3">
        <p className="text-sm font-medium text-gray-700 mb-1">
          Payment Frequency: <span className="capitalize">{paymentFrequency}</span>
        </p>
        <p className="text-sm text-gray-600">
          {getFrequencyDescription()}
        </p>
      </div>

      {/* Interval Selector */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Select Payroll Period
        </label>
        <select
          value={selectedInterval?.id || ''}
          onChange={handleIntervalChange}
          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
        >
          <option value="">Select a period...</option>
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
          <h4 className="font-medium text-blue-900 mb-2">Selected Period</h4>
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
            <p className="text-blue-800">
              <span className="font-medium">Type:</span> <span className="capitalize">{selectedInterval.frequencyType}</span>
            </p>
          </div>
        </div>
      )}

      {/* Quick Stats */}
      <div className="text-xs text-gray-500">
        Showing {intervals.length} available {paymentFrequency} payroll periods
      </div>
    </div>
  );
}