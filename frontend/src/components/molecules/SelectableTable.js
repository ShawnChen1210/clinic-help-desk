import React from 'react';
import { flexRender } from '@tanstack/react-table';

// This component receives the table instance, selection state, and a handler from its parent
export default function SelectableTable({ title, table, selectedColumn, onColumnSelect }) {
  if (!table) return <div>Loading...</div>;

  return (
    <div className="bg-white p-4 rounded-lg shadow">
      <h3 className="font-bold mb-2">{title}</h3>
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead>
            {table.getHeaderGroups().map(headerGroup => (
              <tr key={headerGroup.id}>
                {headerGroup.headers.map(header => {
                  const isSelected = selectedColumn === header.column.id;
                  return (
                    <th
                      key={header.id}
                      className={`
                        p-3 text-left text-sm font-semibold border border-gray-300 cursor-pointer transition-colors
                        ${isSelected ? 'bg-blue-500 text-white' : 'bg-gray-50 text-gray-700 hover:bg-gray-200'}
                      `}
                      // When clicked, it calls the function from props with the column's name
                      onClick={() => {
                        // If the clicked column is already selected, pass null to deselect it.
                        // Otherwise, pass the new column's name to select it.
                        const newSelection = isSelected ? null : header.column.id;
                        onColumnSelect(newSelection);
                      }}
                    >
                      {flexRender(header.column.columnDef.header, header.getContext())}
                    </th>
                  );
                })}
              </tr>
            ))}
          </thead>
          <tbody>
            {table.getRowModel().rows.map(row => (
              <tr key={row.id}>
                {row.getVisibleCells().map(cell => (
                  <td key={cell.id} className="p-3 border border-gray-300">
                    {flexRender(cell.column.columnDef.cell, cell.getContext())}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}