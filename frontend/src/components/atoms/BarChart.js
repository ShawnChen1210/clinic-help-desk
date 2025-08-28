// client/src/components/atoms/BarChart.js

import React from 'react';
import { Bar } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend,
} from 'chart.js';

// Register the necessary components for Chart.js
ChartJS.register(
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend
);

export default function BarChart({
  data = [],
  primaryAxisKey = 'x',
  secondaryAxisKey = 'y',
  height = 'h-96',
  className = '',
  emptyMessage = 'No data available',
  showValues = false,
  formatValue = (val) => val,
  noHoverLines = false
}) {

  // Chart.js requires a specific data structure
  const chartData = {
    labels: data.map(d => d[primaryAxisKey]),
    datasets: [
      {
        label: 'Net Income',
        data: data.map(d => d[secondaryAxisKey]),
        // Set bar color based on positive or negative net income
        backgroundColor: data.map(d => d[secondaryAxisKey] >= 0 ? 'rgba(59, 130, 246, 0.7)' : 'rgba(239, 68, 68, 0.7)'),
        borderColor: data.map(d => d[secondaryAxisKey] >= 0 ? 'rgba(59, 130, 246, 1)' : 'rgba(239, 68, 68, 1)'),
        borderWidth: 1,
      },
    ],
  };

  // Chart.js options for customization
  const options = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        display: false, // Hides the default legend
      },
      tooltip: {
        enabled: !noHoverLines, // Disables the tooltip
      },
    },
    // This disables all pointer events on the chart, removing hover lines and effects
    events: noHoverLines ? [] : ['mousemove', 'mouseout', 'click', 'touchstart', 'touchmove'],
    scales: {
      x: {
        grid: {
          display: false,
        }
      },
      y: {
        beginAtZero: true,
        grid: {
          color: '#e5e7eb',
        }
      },
    },
  };

  if (!data || data.length === 0) {
    return (
      <div className={`flex items-center justify-center ${height} ${className}`}>
        <p className="text-gray-500">{emptyMessage}</p>
      </div>
    );
  }

  return (
    <div className={`w-full ${className}`}>
      <div className={`relative w-full ${height}`}>
        <Bar options={options} data={chartData} />
      </div>

      {/* Show values below chart if enabled */}
      {showValues && (
        <div className="mt-4 overflow-x-auto">
          <div className="flex justify-between items-end space-x-2 min-w-full">
            {data.map((item, index) => {
              // Calculate total revenue, adding back any negative payroll expenses
              const displayRevenue = (item['Transaction Income'] || 0) - (item['Payroll Expense'] < 0 ? item['Payroll Expense'] : 0);
              // Only show positive payroll expenses
              const displayExpense = item['Payroll Expense'] > 0 ? item['Payroll Expense'] : 0;

              return (
                <div key={index} className="text-center flex-1 min-w-0">
                  {/* Period Label */}
                  <div className="text-xs text-gray-600 truncate mb-1" title={item[primaryAxisKey]}>
                    {item[primaryAxisKey]}
                  </div>

                  {/* Net Income (Primary Value) */}
                  <div className="text-sm font-bold text-blue-600 mb-1">
                    {formatValue(item[secondaryAxisKey])}
                  </div>
                  <div className="text-xs text-gray-500 mb-2">Net Income</div>

                  {/* Breakdown */}
                  <div className="space-y-1">
                    {/* Revenue Section */}
                    <div>
                      <div className="text-xs text-green-600 font-medium">
                        +{formatValue(displayRevenue)}
                      </div>
                      <div className="text-xs text-gray-400">Revenue</div>
                    </div>

                    {/* Expenses Section (only shown if > 0) */}
                    {displayExpense > 0 && (
                      <div>
                        <div className="text-xs text-red-600 font-medium">
                          -{formatValue(displayExpense)}
                        </div>
                        <div className="text-xs text-gray-400">Expenses</div>
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}