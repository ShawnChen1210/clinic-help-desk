import React from 'react';

export default function ClinicCard({ clinic, onOpen, onDelete, isDeleting }) {
  return (
    <div className="flex items-center justify-between p-4 border border-gray-200 rounded-lg hover:bg-gray-50">
      <div className="flex-1 cursor-pointer" onClick={() => onOpen(clinic.id)}>
        <h3 className="text-lg font-medium text-gray-900 hover:text-blue-600">
          {clinic.name}
        </h3>
        <p className="text-sm text-gray-500">
          Created: {new Date(clinic.created_at).toLocaleDateString()}
          {clinic.has_sheets && <span className="ml-2 text-green-600">• Sheets Ready</span>}
        </p>
      </div>

      <div className="flex items-center space-x-2">
        <button
          onClick={() => onOpen(clinic.id)}
          className="px-3 py-1 text-sm bg-blue-600 text-white rounded hover:bg-blue-700"
        >
          Open
        </button>
        <button
          onClick={(e) => {
            e.stopPropagation();
            onDelete(clinic.id, clinic.name);
          }}
          disabled={isDeleting}
          className="px-3 py-1 text-sm bg-red-600 text-white rounded hover:bg-red-700 disabled:opacity-50"
        >
          {isDeleting ? 'Deleting...' : 'Delete'}
        </button>
      </div>
    </div>
  );
}