import React, { useState } from "react";
import {useParams} from "react-router-dom";
import api from '../../utils/axiosConfig'; // FIX 1: Import your configured api instance
import TanstackTable from "./TanstackTable";

export default function ConfirmMergeForm({ table, onMergeSuccess }) {
    const { sheet_id } = useParams();
    // FIX 3: Initialize loading state to false
    const [loading, setLoading] = useState(false);

    const onSubmitMerge = async () => { // The 'event' parameter isn't needed here
        setLoading(true); // Set loading to true when the process starts
        try {
            const response = await api.post(`/api/spreadsheets/${sheet_id}/confirm_merge_sheets/`);
            onMergeSuccess(response.data); // It's good practice to notify the parent on success
        } catch (err) {
            console.error('Error confirming merge:', err.response.data.error);
            alert('Failed to confirm merge.'); // Give user feedback
        } finally {
            setLoading(false); // Set loading to false when the process is done// Redirects to the spreadsheet
        }
    };

    return (
        <div className="mt-6 pb-24">
            <h3 className="text-lg font-semibold mb-4">Preview of Merged Data</h3>
            <TanstackTable table={table}/>

            {/* This is the container for the sticky button */}
            <div className="fixed bottom-0 left-0 w-full p-4 bg-white border-t border-gray-200 shadow-t-md">
                <button
                    type="button"
                    onClick={onSubmitMerge}
                    // Make the button full-width on small screens, but constrained on larger screens
                    className="w-full max-w-md mx-auto block bg-green-500 hover:bg-green-600 text-white font-bold py-3 px-4 rounded-lg transition-colors disabled:bg-gray-400"
                    disabled={loading}
                >
                    {loading ? 'Saving...' : 'Confirm & Save'}
                </button>
            </div>
        </div>
    );
}