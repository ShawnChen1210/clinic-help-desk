import React, {useState} from "react";
import { useReactTable, getCoreRowModel, flexRender } from '@tanstack/react-table';
export default function TanstackTable({table}) {

    return (
        <div
            className="bg-white rounded-lg shadow-md overflow-auto max-h-[75vh]"
        >
            <table className="table-auto border-collapse w-full">
                <thead className="sticky top-0 bg-gray-100">
                {table.getHeaderGroups().map(headerGroup => (
                    <tr key={headerGroup.id}>
                        {headerGroup.headers.map(header => (
                            <th
                                key={header.id}
                                className="p-3 text-left text-sm font-semibold text-gray-700 border border-gray-300 whitespace-nowrap"
                            >
                                {flexRender(header.column.columnDef.header, header.getContext())}
                            </th>
                        ))}
                    </tr>
                ))}
                </thead>
                <tbody>
                {table.getRowModel().rows.map(row => (
                    <tr key={row.id} className="hover:bg-gray-50">
                        {row.getVisibleCells().map(cell => (
                            <td
                                key={cell.id}
                                className="p-3 border border-gray-300 whitespace-nowrap"
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