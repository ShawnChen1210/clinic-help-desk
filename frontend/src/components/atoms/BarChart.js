import React, { useState, useMemo } from 'react';
import { Chart } from 'react-charts';

export default function BarChartDisplay({ reportData }) {
  const [timeframe, setTimeframe] = useState('weekly');

  // Select the correct data based on the chosen timeframe
  const dataForChart = useMemo(() => {
    if (timeframe === 'weekly') return reportData.weeklyReport;
    if (timeframe === 'monthly') return reportData.monthlyReport;
    if (timeframe === 'yearly') return reportData.yearlyReport;
    return [];
  }, [reportData, timeframe]);

  // Define the primary axis (X-axis) for the chart.
  // We use useMemo for performance.
  const primaryAxis = useMemo(
    () => ({
      getValue: (datum) => datum.Date, // Use the 'Date' key from our data objects
    }),
    []
  );

  // Define the secondary axes (Y-axes) for the chart.
  const secondaryAxes = useMemo(
    () => [
      {
        getValue: (datum) => datum['Total Income'], // Use the 'Total Income' key
        elementType: 'bar', // We want this to be a bar chart
      },
    ],
    []
  );

  return (
    <div className="p-4 bg-white rounded-lg shadow-md">
      <div className="flex justify-center space-x-2 mb-4">
        {/* Buttons to control the timeframe state */}
        <button onClick={() => setTimeframe('weekly')} className={`py-1 px-3 rounded-full text-sm font-semibold ${timeframe === 'weekly' ? 'bg-blue-500 text-white' : 'bg-gray-200'}`}>Weekly</button>
        <button onClick={() => setTimeframe('monthly')} className={`py-1 px-3 rounded-full text-sm font-semibold ${timeframe === 'monthly' ? 'bg-blue-500 text-white' : 'bg-gray-200'}`}>Monthly</button>
        <button onClick={() => setTimeframe('yearly')} className={`py-1 px-3 rounded-full text-sm font-semibold ${timeframe === 'yearly' ? 'bg-blue-500 text-white' : 'bg-gray-200'}`}>Yearly</button>
      </div>

      {/* The Chart component requires a fixed-size container */}
      <div className="w-full h-96">
        <Chart
          options={{
            data: dataForChart,
            primaryAxis,
            secondaryAxes,
            dark: false, // Optional: set to true for dark mode
          }}
        >
          {/* These are the visual components you render yourself */}
          <Chart.SVG>
            <Chart.Axis type="primary" />
            <Chart.Axis type="secondary" />
            <Chart.Bar />
            <Chart.Tooltip />
          </Chart.SVG>
        </Chart>
      </div>
    </div>
  );
}