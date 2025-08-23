import React, { useState, useEffect } from 'react';
import api from '../utils/axiosConfig';
import MembersTable from "../components/organisms/MembersTable";

export default function Members() {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [updating, setUpdating] = useState(false);
  const [error, setError] = useState(null);
  const [currentUser, setCurrentUser] = useState(null);

  useEffect(() => {
    fetchCurrentUser();
    fetchUsers();
  }, []);

  const fetchCurrentUser = async () => {
    try {
      const response = await api.get('/api/members/current-user/');
      setCurrentUser(response.data);
      console.log(currentUser);
    } catch (error) {
      console.error('Error fetching current user:', error);
      setError('Failed to verify user permissions');
    }
  };

  const fetchUsers = async () => {
    try {
      setLoading(true);
      const response = await api.get('/api/members/');
      setUsers(response.data);
    } catch (error) {
      console.error('Error fetching users:', error);
      setError('Failed to fetch users');
    } finally {
      setLoading(false);
    }
  };

  const updateUser = async (userData) => {
  try {
    setUpdating(true);
    console.log('Sending user data:', JSON.stringify(userData, null, 2)); // More detailed logging

    const response = await api.post(`/api/members/${userData.userId}/update-roles/`, {
      primary_role: userData.primary_role,
      additional_roles: userData.additional_roles,
      is_verified: userData.is_verified,
      is_staff: userData.is_staff, // Add this line
      payment_frequency: userData.payment_frequency,
      primaryRoleValues: userData.primaryRoleValues,
      additionalRoleValues: userData.additionalRoleValues
    });

    console.log('Server response:', response.data); // Log successful response
    await fetchUsers();
  } catch (error) {
    console.error('Error updating user:', error);
    console.error('Error response:', error.response?.data); // Log server error details
    console.error('Error status:', error.response?.status); // Log status code
    setError('Failed to update user roles');
  } finally {
    setUpdating(false);
  }
};

  // Check if user has permission to view this page
  if (currentUser && !currentUser.is_staff && !currentUser.is_superuser) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <h2 className="text-2xl font-bold text-gray-900 mb-2">Access Denied</h2>
          <p className="text-gray-600">You don't have permission to view this page.</p>
        </div>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading members...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
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
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Members Management</h1>
          <p className="text-gray-600 mt-2">
            Manage user roles and permissions (Admin Only)
          </p>
        </div>
      </div>

      {users.length > 0 ? (
        <MembersTable
          users={users}
          onUpdateUser={updateUser}
          isUpdating={updating}
        />
      ) : (
        <div className="text-center py-12">
          <p className="text-gray-500">No members found.</p>
        </div>
      )}
    </div>
  );
}