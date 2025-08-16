// pages/Clinics.js - Super simplified
import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../utils/axiosConfig';
import CreateClinicForm from "../components/molecules/CreateClinicForm";
import ClinicCard from "../components/atoms/ClinicCard";

export default function Clinics() {
  const navigate = useNavigate();
  const [clinics, setClinics] = useState([]);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [deletingId, setDeletingId] = useState(null);
  const [error, setError] = useState(null);
  const [currentUser, setCurrentUser] = useState(null);

  useEffect(() => {
    fetchCurrentUser();
    fetchClinics();
  }, []);

  const fetchCurrentUser = async () => {
    try {
      const response = await api.get('/api/members/current-user/');
      setCurrentUser(response.data);
    } catch (error) {
      setError('Failed to verify user permissions');
    }
  };

  const fetchClinics = async () => {
    try {
      const response = await api.get('/api/clinics/');
      setClinics(response.data);
    } catch (error) {
      setError('Failed to fetch clinics');
    } finally {
      setLoading(false);
    }
  };

  const createClinic = async (clinicName) => {
    try {
      setCreating(true);
      const response = await api.post('/api/clinics/', { name: clinicName });
      setClinics(prev => [...prev, response.data]);
      setError(null);
    } catch (error) {
      setError(error.response?.data?.error || 'Failed to create clinic');
    } finally {
      setCreating(false);
    }
  };

  const deleteClinic = async (clinicId, clinicName) => {
    const confirmMessage = `Delete "${clinicName}"?\n\nThis will permanently delete:\n• The clinic record\n• All 4 associated Google Sheets\n• All clinic data\n\nThis action cannot be undone.`;

    if (!window.confirm(confirmMessage)) return;

    try {
      setDeletingId(clinicId);
      const response = await api.delete(`/api/clinics/${clinicId}/`);

      setClinics(prev => prev.filter(clinic => clinic.id !== clinicId));
      setError(null);

      // Show success message with details
      if (response.data.deleted_sheets > 0) {
        console.log(`Successfully deleted clinic and ${response.data.deleted_sheets} Google Sheets`);
      }

    } catch (error) {
      console.error('Error deleting clinic:', error);
      setError(error.response?.data?.error || 'Failed to delete clinic and associated sheets');
    } finally {
      setDeletingId(null);
    }
  };

  // Loading
  if (!currentUser || loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  // Permission check
  if (!currentUser.is_staff && !currentUser.is_superuser) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <h2 className="text-2xl font-bold text-gray-900 mb-2">Access Denied</h2>
          <p className="text-gray-600">You don't have permission to manage clinics.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-100 py-8">
      <div className="max-w-4xl mx-auto px-4">
        <div className="bg-white rounded-lg shadow">
          {/* Header */}
          <div className="px-6 py-4 border-b border-gray-200">
            <h1 className="text-2xl font-bold text-gray-900">Clinics</h1>
          </div>

          {/* Create Form */}
          <CreateClinicForm onSubmit={createClinic} isCreating={creating} />

          {/* Error */}
          {error && (
            <div className="px-6 py-4 bg-red-50 border-b border-gray-200">
              <p className="text-red-700">{error}</p>
              <button onClick={() => setError(null)} className="text-red-500 underline">
                Dismiss
              </button>
            </div>
          )}

          {/* Clinics List */}
          <div className="px-6 py-4">
            {clinics.length === 0 ? (
              <p className="text-center text-gray-500 py-8">No clinics yet. Create your first one above.</p>
            ) : (
              <div className="space-y-3">
                {clinics.map((clinic) => (
                  <ClinicCard
                    key={clinic.id}
                    clinic={clinic}
                    onOpen={(id) => navigate(`/chd-app/${id}`)}
                    onDelete={deleteClinic}
                    isDeleting={deletingId === clinic.id}
                  />
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}