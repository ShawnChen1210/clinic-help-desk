import React, { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import axios from "axios";
import { useListTable } from "../hooks/useListTable";
import { useClinic } from '../context/ClinicContext';
import { fetchUser } from "../services/auth";
import TanstackTable from "../components/atoms/TanstackTable";
import SpreadsheetNavbar from "../components/molecules/SpreadsheetNavbar";

export default function SpreadsheetComponent() {
    const [userData, setUserData] = useState(null);
    const { sheet_id } = useParams();
    const [sheetData, setSheetData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const { loading: clinicLoading } = useClinic(); // Get clinic loading state

    // Fetch the user's data - no need to load clinic data here since Layout.js handles it
    useEffect(() => {
        const fetchInitialUser = async () => {
            try {
                const res = await fetchUser();
                setUserData(res.data);
            } catch (err) {
                console.error('User not authenticated:', err);
                setError('Authentication failed. Please log in.');
                setLoading(false);
            }
        };

        fetchInitialUser();
    }, []);

    useEffect(() => {
        // Wait for both user data and clinic data to be ready
        if (!userData || !sheet_id || clinicLoading) {
            return;
        }

        const fetchData = async () => {
            try {
                setLoading(true);
                const response = await axios.get(`/api/spreadsheets/${sheet_id}/`);
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

        fetchData();

    }, [userData, sheet_id, clinicLoading]);

    // Constructs the Tanstack table
    const table = useListTable({
        rawColumns: sheetData?.sheet_header ?? [],
        rawData: sheetData?.sheet_data ?? [],
    });

    // Show loading state - wait for both clinic and sheet data
    if (loading || clinicLoading) {
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

    return (
        <div>
            <SpreadsheetNavbar userData={userData} sheetData={sheetData} />
            <TanstackTable table={table}/>
        </div>
    );
}