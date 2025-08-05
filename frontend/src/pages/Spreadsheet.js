import { useEffect, useMemo, useState } from 'react';
import { fetchUser } from '../services/auth';
import { useParams } from 'react-router-dom';
import { useReactTable, getCoreRowModel, flexRender } from '@tanstack/react-table';
import axios from "axios";
import LinkButton from "../components/atoms/LinkButton";

export default function SpreadsheetComponent() {
    const [userData, setUserData] = useState(null);
    const { sheet_id } = useParams();
    const [sheetData, setSheetData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    // Fetch the user's data first. This runs once on mount.
    useEffect(() => {
        const fetchInitialUser = async () => {
            try {
                const res = await fetchUser(); // Fetches from your user API endpoint
                setUserData(res.data);
            } catch (err) {
                console.error('User not authenticated:', err);
                setError('Authentication failed. Please log in.');
                setLoading(false); // Stop loading if user fetch fails
            }
        };

        fetchInitialUser();
    }, []);

    // Fetch spreadsheet data ONLY AFTER we have a confirmed user.
    useEffect(() => {
        if (!userData || !sheet_id) {
            return;
        }

        const fetchData = async () => {
            try {
                setLoading(true);
                console.log("getting django api response")
                const response = await axios.get(`/api/spreadsheets/${sheet_id}/`);
                console.log("response recieved")
                setSheetData(response.data);
            } catch (err) {
                if (err.response?.status === 404) {
                    setError('Sheet not found');
                } else if (err.response?.status === 403) {
                    setError('No permission to access this sheet');
                } else {
                    setError('Failed to load sheet data');
                }
            } finally {
                setLoading(false);
            }
        };


        if (sheet_id) {
            fetchData();
        }

    }, [userData, sheet_id]);

    // Parse the header and data. Use the optional chaining operator (?)
    // to prevent errors if sheetData is null during initial renders.
    const columns = useMemo(() => {
        return sheetData?.sheet_header?.map((header, index) => ({
            header: header,
            accessorKey: String(index),
        })) || [];
    }, [sheetData]);

    const data = useMemo(() => sheetData?.sheet_data || [], [sheetData]);

    const table = useReactTable({
        data,
        columns,
        getCoreRowModel: getCoreRowModel(),
    });




    // Show loading state (spinner)
    if (loading) {
        return (
            <div className="flex items-center justify-center min-h-screen bg-gray-100">
                <div className="w-16 h-16 border-4 border-dashed rounded-full animate-spin border-blue-500"></div>
            </div>
        );
    }

    // Show error state
    if (error) {
        return <div>Error: {error}</div>;
    }

    // Show message if no sheet data
    if (!sheetData) {
        return <div>No sheet data available</div>;
    }

    const spreadsheetTitle = sheetData.sheet_name;

    return (
        <div className="bg-gray-100 min-h-screen p-4 sm:p-8 font-sans">

            {/* The top div (header bar) you requested */}
            <div className="flex flex-wrap justify-between items-center bg-white p-4 sm:p-6 rounded-lg shadow-md mb-8">
                <div>
                    <h1 className="text-xl sm:text-2xl font-bold text-gray-800">Welcome, {userData?.username}!</h1>
                    <h4 className="text-sm font-medium text-gray-500 mt-1">SheetName: {spreadsheetTitle}</h4>
                </div>
                <div className="flex space-x-2 mt-4 sm:mt-0">
                    <LinkButton text="Upload CSV" link={`/spreadsheet/${sheet_id}/upload`} />
                </div>
            </div>

            {/* A container for the table to handle overflow and styling */}
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
        </div>
    );
}