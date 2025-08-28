import React, { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import api from '../../utils/axiosConfig';
import BarChart from '../atoms/BarChart';

export default function IncomeReport() {
  const { clinic_id } = useParams();
  const [timeframe, setTimeframe] = useState('weekly');
  const [weeklyPage, setWeeklyPage] = useState(0);
  const [monthlyPage, setMonthlyPage] = useState(0);
  const [reportData, setReportData] = useState({
    weeklyReport: [],
    monthlyReport: []
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const ITEMS_PER_PAGE = 6; // Both weeks and months show 6 items per page

  useEffect(() => {
    if (clinic_id) {
      fetchIncomeReport();
    }
  }, [clinic_id]);

  useEffect(() => {
    // When data loads, set pagination to start from most recent
    if (reportData.weeklyReport.length > 0) {
      const totalWeeklyPages = Math.ceil(reportData.weeklyReport.length / ITEMS_PER_PAGE);
      setWeeklyPage(Math.max(0, totalWeeklyPages - 1));
    }
    if (reportData.monthlyReport.length > 0) {
      const totalMonthlyPages = Math.ceil(reportData.monthlyReport.length / ITEMS_PER_PAGE);
      setMonthlyPage(Math.max(0, totalMonthlyPages - 1));
    }
  }, [reportData]);

  const fetchIncomeReport = async () => {
    try {
      setLoading(true);
      setError(null);

      const response = await api.get(`/api/dashboard/${clinic_id}/income_report/`);
      setReportData(response.data);
    } catch (error) {
      console.error('Error fetching income report:', error);
      if (error.response?.status === 400) {
        setError(error.response.data.error || 'Configuration error. Please check clinic settings.');
      } else {
        setError('Failed to load income report. Please try again.');
      }
    } finally {
      setLoading(false);
    }
  };

  const formatCurrency = (amount) => {
    return new Intl.NumberFormat('en-CA', {
      style: 'currency',
      currency: 'CAD',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2
    }).format(amount || 0);
  };

  // Get data for current timeframe with pagination (most recent first)
  const getCurrentData = () => {
    if (timeframe === 'weekly') {
      const transformedData = reportData.weeklyReport.map(item => {
        // The backend sends YYYY-MM-DD which JS parses as UTC midnight.
        // We create the date object this way to avoid timezone-related date shifts.
        const startDate = new Date(`${item.Date}T00:00:00`);
        const endDate = new Date(startDate);
        endDate.setDate(startDate.getDate() + 6);

        const formatOptions = { month: 'short', day: 'numeric' };

        // Using en-CA locale for Canadian date formatting
        const formattedStart = startDate.toLocaleDateString('en-CA', formatOptions);
        const formattedEnd = endDate.toLocaleDateString('en-CA', formatOptions);

        return {
          ...item,
          Date: `${formattedStart} - ${formattedEnd}` // e.g., "Aug 18 - Aug 24"
        };
      });

      // Reverse the array to show most recent first, then paginate
      const reversedData = transformedData.reverse();
      const startIndex = weeklyPage * ITEMS_PER_PAGE;
      const endIndex = startIndex + ITEMS_PER_PAGE;
      return reversedData.slice(startIndex, endIndex);
    } else {
      // Monthly logic with improved date formatting
      const transformedData = reportData.monthlyReport.map(item => {
          // Backend sends 'YYYY-MM'
          const [year, month] = item.Date.split('-');
          const date = new Date(year, month - 1, 1);
          const formattedMonth = date.toLocaleDateString('en-CA', { month: 'long', year: 'numeric' });
          return {
              ...item,
              Date: formattedMonth // e.g., "August 2025"
          };
      });
      const reversedData = transformedData.reverse();
      const startIndex = monthlyPage * ITEMS_PER_PAGE;
      const endIndex = startIndex + ITEMS_PER_PAGE;
      return reversedData.slice(startIndex, endIndex);
    }
  };


  // Get pagination info
  const getPaginationInfo = () => {
    const currentData = timeframe === 'weekly' ? reportData.weeklyReport : reportData.monthlyReport;
    const currentPage = timeframe === 'weekly' ? weeklyPage : monthlyPage;
    const totalItems = currentData.length;
    const totalPages = Math.ceil(totalItems / ITEMS_PER_PAGE);
    const pageNumber = currentPage + 1;
    return { totalPages, currentPage: pageNumber, totalItems };
  };

  // Handle pagination
  const handlePageChange = (direction) => {
    const { totalPages } = getPaginationInfo();
    if (timeframe === 'weekly') {
      if (direction === 'next' && weeklyPage < totalPages - 1) {
        setWeeklyPage(weeklyPage + 1);
      } else if (direction === 'prev' && weeklyPage > 0) {
        setWeeklyPage(weeklyPage - 1);
      }
    } else {
      if (direction === 'next' && monthlyPage < totalPages - 1) {
        setMonthlyPage(monthlyPage + 1);
      } else if (direction === 'prev' && monthlyPage > 0) {
        setMonthlyPage(monthlyPage - 1);
      }
    }
  };

  const getCurrentMonthIncome = () => {
    if (reportData.monthlyReport.length === 0) return 0;
    return reportData.monthlyReport[reportData.monthlyReport.length - 1]['Net Income'];
  };

  const getYTDTotal = () => {
    return reportData.monthlyReport.reduce((sum, month) => sum + month['Net Income'], 0);
  };

  if (loading) {
    return (
      <div className="bg-white shadow rounded-lg p-6">
        <div className="animate-pulse">
          <div className="flex justify-between items-center mb-4">
            <div className="h-6 bg-gray-200 rounded w-32"></div>
            <div className="h-8 bg-gray-200 rounded w-24"></div>
          </div>
          <div className="h-96 bg-gray-200 rounded mb-6"></div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {[...Array(2)].map((_, i) => (
              <div key={i} className="h-20 bg-gray-200 rounded"></div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-white shadow rounded-lg p-6">
        <div className="text-center">
          <div className="text-red-600 mb-4">
            <svg className="w-12 h-12 mx-auto mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.996-.833-2.768 0L3.232 16.5c-.77.833.192 2.5 1.732 2.5z" />
            </svg>
          </div>
          <h3 className="text-lg font-medium text-red-800 mb-2">Unable to Load Income Report</h3>
          <p className="text-red-600 mb-4">{error}</p>
          <button
            onClick={fetchIncomeReport}
            className="bg-red-600 text-white px-4 py-2 rounded hover:bg-red-700 transition duration-200"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  const paginationInfo = getPaginationInfo();

  return (
    <div className="space-y-6">
      {/* Income Chart */}
      <div className="bg-white shadow rounded-lg p-6">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-xl font-semibold text-gray-900">Income Report</h2>
          <button
            onClick={fetchIncomeReport}
            className="text-sm bg-gray-100 hover:bg-gray-200 px-3 py-1 rounded transition duration-200 flex items-center gap-2"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
            Refresh Data
          </button>
        </div>

        {/* Important Notice */}
        <div className="mb-4 p-3 bg-yellow-50 border border-yellow-200 rounded-md">
          <div className="flex">
            <svg className="w-5 h-5 text-yellow-600 mr-2 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <div className="text-sm text-yellow-800">
              <strong>Note:</strong> Payroll expenses only appear after generating payroll for users. The expense date is based on the payroll period start date, not when it was generated.
            </div>
          </div>
        </div>

        {/* Timeframe Selection */}
        <div className="flex justify-center space-x-2 mb-4">
          <button
            onClick={() => {
              setTimeframe('weekly');
              const totalPages = Math.ceil(reportData.weeklyReport.length / ITEMS_PER_PAGE);
              setWeeklyPage(Math.max(0, totalPages - 1));
            }}
            className={`py-2 px-4 rounded-lg text-sm font-semibold transition duration-200 ${
              timeframe === 'weekly' 
                ? 'bg-blue-500 text-white shadow-md' 
                : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
            }`}
          >
            Weekly View
          </button>
          <button
            onClick={() => {
              setTimeframe('monthly');
              const totalPages = Math.ceil(reportData.monthlyReport.length / ITEMS_PER_PAGE);
              setMonthlyPage(Math.max(0, totalPages - 1));
            }}
            className={`py-2 px-4 rounded-lg text-sm font-semibold transition duration-200 ${
              timeframe === 'monthly' 
                ? 'bg-blue-500 text-white shadow-md' 
                : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
            }`}
          >
            Monthly View
          </button>
        </div>

        {/* Pagination */}
        {paginationInfo.totalPages > 1 && (
          <div className="flex justify-center items-center space-x-4 mb-4">
            <button
              onClick={() => handlePageChange('prev')}
              disabled={paginationInfo.currentPage === 1}
              className={`px-3 py-1 rounded text-sm ${
                paginationInfo.currentPage === 1
                  ? 'bg-gray-200 text-gray-400 cursor-not-allowed' 
                  : 'bg-blue-100 text-blue-700 hover:bg-blue-200'
              }`}
            >
              ← Older
            </button>
            <span className="text-sm text-gray-600">
              Page {paginationInfo.currentPage} of {paginationInfo.totalPages}
            </span>
            <button
              onClick={() => handlePageChange('next')}
              disabled={paginationInfo.currentPage >= paginationInfo.totalPages}
              className={`px-3 py-1 rounded text-sm ${
                paginationInfo.currentPage >= paginationInfo.totalPages
                  ? 'bg-gray-200 text-gray-400 cursor-not-allowed'
                  : 'bg-blue-100 text-blue-700 hover:bg-blue-200'
              }`}
            >
              Newer →
            </button>
          </div>
        )}

        {/* Chart Title */}
        <div className="text-center mb-4">
          <h3 className="text-lg font-semibold text-gray-800">
            {timeframe === 'weekly' ? 'Weekly' : 'Monthly'} Net Income
            <span className="text-sm font-normal text-gray-600 ml-2">
              (Transaction Income - Payroll Expenses)
            </span>
          </h3>
        </div>

        {/* Bar Chart */}
        <BarChart
          data={getCurrentData()}
          primaryAxisKey="Date"
          secondaryAxisKey="Net Income"
          height="h-80"
          showValues={true}
          formatValue={formatCurrency}
          className="p-4 bg-white rounded-lg"
          emptyMessage={`No data available for ${timeframe} view`}
          noHoverLines={true}
        />
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="bg-white shadow rounded-lg p-6">
          <div className="flex items-center">
            <div className="flex-shrink-0">
              <div className="w-8 h-8 bg-blue-500 rounded-md flex items-center justify-center">
                <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
                </svg>
              </div>
            </div>
            <div className="ml-5 w-0 flex-1">
              <dl>
                <dt className="text-sm font-medium text-gray-500 truncate">
                  Current Month Net Income
                </dt>
                <dd className="text-lg font-medium text-gray-900">
                  {formatCurrency(getCurrentMonthIncome())}
                </dd>
              </dl>
            </div>
          </div>
        </div>

        <div className="bg-white shadow rounded-lg p-6">
          <div className="flex items-center">
            <div className="flex-shrink-0">
              <div className="w-8 h-8 bg-purple-500 rounded-md flex items-center justify-center">
                <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
                </svg>
              </div>
            </div>
            <div className="ml-5 w-0 flex-1">
              <dl>
                <dt className="text-sm font-medium text-gray-500 truncate">
                  Year to Date Net Income
                </dt>
                <dd className="text-lg font-medium text-gray-900">
                  {formatCurrency(getYTDTotal())}
                </dd>
              </dl>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}