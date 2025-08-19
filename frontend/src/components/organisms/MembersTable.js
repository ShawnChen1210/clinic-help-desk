import React, { useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { useReactTable, getCoreRowModel, createColumnHelper } from '@tanstack/react-table';
import TanstackTable from "../atoms/TanstackTable";
import RoleManagement from '../molecules/RoleManagement';

const columnHelper = createColumnHelper();

export default function MembersTable({ users, onUpdateUser, isUpdating }) {
  const [editingUser, setEditingUser] = useState(null);
  const navigate = useNavigate();
  const { clinic_id } = useParams();

  const handleViewProfile = (user) => {
    setEditingUser(user);
  };

  const handleSaveUser = async (userData) => {
    await onUpdateUser(userData);
    setEditingUser(null);
  };

  const handleCancelEdit = () => {
    setEditingUser(null);
  };

  const handleGeneratePayroll = (user) => {
    navigate(`/chd-app/${clinic_id}/payroll/${user.id}`);
  };

  const columns = [
    columnHelper.accessor('username', {
      header: 'Username',
      cell: info => info.getValue(),
    }),
    columnHelper.accessor('first_name', {
      header: 'First Name',
      cell: info => info.getValue() || 'N/A',
    }),
    columnHelper.accessor('last_name', {
      header: 'Last Name',
      cell: info => info.getValue() || 'N/A',
    }),
    columnHelper.accessor('email', {
      header: 'Email',
      cell: info => info.getValue() || 'N/A',
    }),
    columnHelper.accessor('is_verified', {
      header: 'Verified',
      cell: info => (
        <span className={`px-2 py-1 rounded text-xs font-medium ${
          info.getValue() ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
        }`}>
          {info.getValue() ? 'Yes' : 'No'}
        </span>
      ),
    }),
    columnHelper.accessor('primaryRole', {
      header: 'Primary Role',
      cell: info => info.getValue() || 'None',
    }),
    columnHelper.display({
      id: 'actions',
      header: 'Actions',
      cell: props => (
        <div className="flex space-x-2">
          <button
            onClick={() => handleViewProfile(props.row.original)}
            className="px-3 py-1.5 text-sm font-medium text-white bg-blue-600 rounded hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 transition duration-200"
          >
            View Profile
          </button>
          <button
            onClick={() => handleGeneratePayroll(props.row.original)}
            className="px-3 py-1.5 text-sm font-medium text-white bg-green-600 rounded hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-green-500 focus:ring-offset-2 transition duration-200"
          >
            Generate Payroll
          </button>
        </div>
      ),
    }),
  ];

  const table = useReactTable({
    data: users,
    columns,
    getCoreRowModel: getCoreRowModel(),
  });

  return (
    <>
      <TanstackTable table={table} />

      {editingUser && (
        <RoleManagement
          user={editingUser}
          onSave={handleSaveUser}
          onCancel={handleCancelEdit}
          isLoading={isUpdating}
          isOpen={!!editingUser}
        />
      )}
    </>
  );
}