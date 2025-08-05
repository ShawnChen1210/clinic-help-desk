import React, {useState} from "react";
import { useReactTable, getCoreRowModel, flexRender } from '@tanstack/react-table';
export default function TanstackTable({table}) {


    return (
        <div className="overflow-x-auto bg-white rounded-lg shadow-md">
            <table className="w-full">
                <thead>
                {table.getHeaderGroups().map(headerGroup => (
                    <tr key={headerGroup.id}>
                        {headerGroup.headers.map(header => (
                            <th
                                key={header.id}
                                className="p-3 text-left text-sm font-semibold text-gray-700 bg-gray-50 border border-gray-300"
                            >
                                {flexRender(header.column.columnDef.header, header.getContext())}
                            </th>
                        ))}
                    </tr>
                ))}
                </thead>
                <tbody>
                {table.getRowModel().rows.map(row => (
                    <tr key={row.id} className="hover:bg-gray-50 transition-colors">
                        {row.getVisibleCells().map(cell => (
                            <td
                                key={cell.id}
                                className="p-3 border border-gray-300"
                            >
                                {flexRender(cell.column.columnDef.cell, cell.getContext())}
                            </td>
                        ))}
                    </tr>
                ))}
                </tbody>
            </table>
        </div>
    )
}