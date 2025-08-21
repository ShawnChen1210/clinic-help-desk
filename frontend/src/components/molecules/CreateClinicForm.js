// components/CreateClinicForm.js
import React, { useState } from 'react';

export default function CreateClinicForm({ onSubmit, isCreating }) {
  const [clinicName, setClinicName] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!clinicName.trim()) return;

    onSubmit(clinicName.trim());
    setClinicName('');
  };

  return (
    <div className="px-6 py-4 border-b border-gray-200 bg-gray-50">
      <form onSubmit={handleSubmit} className="flex gap-4">
        <input
          type="text"
          value={clinicName}
          onChange={(e) => setClinicName(e.target.value)}
          placeholder="Enter clinic name..."
          disabled={isCreating}
          className="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
        />
        <button
          type="submit"
          disabled={isCreating || !clinicName.trim()}
          className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50"
        >
          {isCreating ? 'Creating Clinic & Sheets...' : 'Create Clinic'}
        </button>
      </form>
      {isCreating && (
        <p className="text-sm text-gray-600 mt-2">
          Creating clinic and Sheets... This may take a moment.
        </p>
      )}
    </div>
  );
}