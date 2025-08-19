import React, { useState } from "react";
import api from '../../utils/axiosConfig';
import TanstackTable from "../atoms/TanstackTable";

export default function ConfirmMergeForm({ table, onMergeSuccess, targetSheetId }) {
    const [loading, setLoading] = useState(false);

    const onSubmitMerge = async () => {
        if (!targetSheetId) {
            console.error('No target sheet ID provided');
            alert('Error: No target sheet ID available');
            return;
        }

        setLoading(true);
        try {
            const response = await api.post(`/api/spreadsheets/${targetSheetId}/confirm_merge_sheets/`);
            onMergeSuccess(response.data);
        } catch (err) {
            console.error('Error confirming merge:', err.response?.data?.error || err.message);
            alert(`Failed to confirm merge: ${err.response?.data?.error || 'Unknown error'}`);
        } finally {
            setLoading(false);
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
                    className="w-full max-w-md mx-auto block bg-green-500 hover:bg-green-600 text-white font-bold py-3 px-4 rounded-lg transition-colors disabled:bg-gray-400"
                    disabled={loading || !targetSheetId}
                >
                    {loading ? 'Saving...' : 'Confirm & Save'}
                </button>
            </div>
        </div>
    );
}