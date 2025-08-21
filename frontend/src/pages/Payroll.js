import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import api from '../utils/axiosConfig';
import PayrollIntervalSelector from '../components/molecules/PayrollIntervalSelector';

export default function Payroll() {
  const { userId, clinic_id } = useParams();
  const navigate = useNavigate();
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedInterval, setSelectedInterval] = useState(null);
  const [generating, setGenerating] = useState(false);

  useEffect(() => {
    fetchUserDetails();
  }, [userId]);

  const fetchUserDetails = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await api.get(`/api/payroll/${userId}/get_user/`);
      setUser(response.data);
    } catch (error) {
      console.error('Error fetching user details:', error);
      if (error.response?.status === 403) {
        setError('You do not have permission to access payroll data.');
      } else if (error.response?.status === 404) {
        setError('User not found.');
      } else {
        setError('Failed to fetch user details. Please try again.');
      }
    } finally {
      setLoading(false);
    }
  };

  const handleBackToMembers = () => {
    navigate(`/chd-app/${clinic_id}/members`);
  };

  const handleGeneratePayroll = async () => {
    if (!selectedInterval) {
      alert('Please select a payroll interval');
      return;
    }

    setGenerating(true);

    // Format dates as YYYY-MM-DD to avoid timezone conversion issues
    const formatDateForAPI = (date) => {
      const year = date.getFullYear();
      const month = String(date.getMonth() + 1).padStart(2, '0');
      const day = String(date.getDate()).padStart(2, '0');
      return `${year}-${month}-${day}`;
    };

    const payrollData = {
      startDate: formatDateForAPI(selectedInterval.startDate),
      endDate: formatDateForAPI(selectedInterval.endDate),
      interval: selectedInterval.label,
      clinic_id: clinic_id
    };

    try {
      const response = await api.post(`/api/payroll/${userId}/generate_payroll/`, payrollData);
      console.log('Payroll generation response:', response.data);

      // Navigate to confirm payroll page with the data
      navigate(`/chd-app/${clinic_id}/payroll/${userId}/confirm`, {
        state: { payrollData: response.data }
      });
    } catch (error) {
      console.error('Error generating payroll:', error);
      let errorMessage = 'Failed to generate payroll. Please try again.';

      if (error.response?.data?.error) {
        errorMessage = error.response.data.error;
      } else if (error.response?.status === 403) {
        errorMessage = 'You do not have permission to generate payroll.';
      } else if (error.response?.status === 400) {
        errorMessage = 'Invalid payroll data or user configuration.';
      }

      alert(errorMessage);
    } finally {
      setGenerating(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading user details...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-md p-4">
        <h3 className="text-red-800 font-medium">Error</h3>
        <p className="text-red-600 mt-1">{error}</p>
        <div className="mt-4 space-x-2">
          <button
            onClick={() => {
              setError(null);
              fetchUserDetails();
            }}
            className="px-3 py-1 bg-red-100 text-red-800 rounded text-sm hover:bg-red-200"
          >
            Retry
          </button>
          <button
            onClick={handleBackToMembers}
            className="px-3 py-1 bg-gray-100 text-gray-800 rounded text-sm hover:bg-gray-200"
          >
            Back to Members
          </button>
        </div>
      </div>
    );
  }

  if (!user) {
    return (
      <div className="text-center py-12">
        <p className="text-gray-500">User not found.</p>
        <button
          onClick={handleBackToMembers}
          className="mt-4 px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
        >
          Back to Members
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Generate Payroll</h1>
          <p className="text-gray-600 mt-2">
            Payroll generation for selected member
          </p>
        </div>
        <button
          onClick={handleBackToMembers}
          className="px-4 py-2 bg-gray-600 text-white rounded hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-gray-500 focus:ring-offset-2"
        >
          Back to Members
        </button>
      </div>

      <div className="bg-white shadow rounded-lg p-6">
        <h2 className="text-xl font-semibold text-gray-800 mb-4">Member Information</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700">Full Name</label>
            <p className="mt-1 text-sm text-gray-900">
              {user.first_name || user.last_name
                ? `${user.first_name || ''} ${user.last_name || ''}`.trim()
                : 'N/A'
              }
            </p>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700">Username</label>
            <p className="mt-1 text-sm text-gray-900">{user.username}</p>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700">Email</label>
            <p className="mt-1 text-sm text-gray-900">{user.email || 'N/A'}</p>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700">Primary Role</label>
            <p className="mt-1 text-sm text-gray-900">{user.primaryRole || 'None'}</p>
          </div>
        </div>
      </div>

      <div className="bg-white shadow rounded-lg p-6">
        <h2 className="text-xl font-semibold text-gray-800 mb-6">Payroll Generation</h2>

        <PayrollIntervalSelector
          payrollDates={user?.payroll_dates}
          onIntervalSelect={setSelectedInterval}
          selectedInterval={selectedInterval}
          className="mb-6"
        />

        <div className="flex items-center justify-between pt-4 border-t border-gray-200">
          <div className="text-sm text-gray-600">
            {selectedInterval ? 'Ready to generate payroll' : 'Please select an interval to continue'}
          </div>
          <button
            onClick={handleGeneratePayroll}
            disabled={!selectedInterval || generating}
            className={`px-6 py-2 rounded-md font-medium focus:outline-none focus:ring-2 focus:ring-offset-2 transition-colors ${
              !selectedInterval || generating
                ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
                : 'bg-green-600 text-white hover:bg-green-700 focus:ring-green-500'
            }`}
          >
            {generating ? (
              <div className="flex items-center">
                <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                Generating...
              </div>
            ) : (
              'Generate Payroll'
            )}
          </button>
        </div>
      </div>
    </div>
  );
}