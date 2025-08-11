import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import axios from "axios";
import api from "../utils/axiosConfig";
import MultiStepForm from "../components/organisms/MultiStepForm";

export default function UploadFiles() {
    const { sheet_id } = useParams()
    const navigate = useNavigate()
    const [loading, setLoading] = useState(true)
    const [allowed, setAllowed] = useState(false)
    const [error, setError] = useState('')

    useEffect(() => {
        const checkAllowed = async () => {
            try {
                await axios.get(`/api/spreadsheets/${sheet_id}/check_perms/`);
                setAllowed(true);
            } catch (err) {
                console.error('User not allowed access:', err);
                setError('You do not have permission to view this page.');
                setAllowed(false);
            } finally {
                setLoading(false);
            }
        };
        checkAllowed();
    }, [sheet_id]);

    const handleClose = async () => {
        try {
            await api.post(`/api/spreadsheets/${sheet_id}/delete_session_storage/`);
        } catch (err) {
            console.error('Close Failed', err);
        } finally {
            navigate(`/spreadsheet/${sheet_id}/`)
        }
    }

    if (loading) {
        return (
            <div className="flex items-center justify-center min-h-screen bg-gray-100">
                <div className="w-16 h-16 border-4 border-dashed rounded-full animate-spin border-blue-500"></div>
            </div>
        );
    }

    if (!allowed) {
        return (
            <div className="flex items-center justify-center min-h-screen bg-gray-100">
                <div className="bg-red-50 border border-red-200 rounded-lg p-6 max-w-md">
                    <h2 className="text-lg font-semibold text-red-800 mb-2">Access Denied</h2>
                    <p className="text-red-600">{error}</p>
                    <button
                        onClick={() => navigate('/')}
                        className="mt-4 bg-red-500 hover:bg-red-600 text-white px-4 py-2 rounded"
                    >
                        Go Back
                    </button>
                </div>
            </div>
        );
    }

    return (
        <div className="bg-gray-100 min-h-screen p-8 sm:p-8 font-sans">
            <button
                onClick={handleClose}
                className="text-yellow-800 hover:text-yellow-900 font-sans font-bold text-2xl leading-none"
                aria-label="Close"
            >
                &times;
            </button>
            <MultiStepForm/>
        </div>
    )
}