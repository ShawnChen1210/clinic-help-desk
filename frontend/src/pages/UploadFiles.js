import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useClinic } from "../context/ClinicContext";
import api from "../utils/axiosConfig";
import MultiStepForm from "../components/organisms/MultiStepForm";

export default function UploadFiles() {
    const { clinic_id } = useParams();
    const navigate = useNavigate();
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');
    const { clinicName } = useClinic();

    // Clean up temp files when component unmounts (user navigates away)
    useEffect(() => {
        return () => {
            // Cleanup function that runs when component unmounts
            cleanupTempFiles();
        };
    }, []);

    const cleanupTempFiles = async () => {
        try {
            // Call cleanup endpoint
            await api.post('/api/spreadsheets/cleanup_temp_files/');
        } catch (err) {
            console.error('Cleanup failed:', err);
            // Don't show error to user for cleanup failures
        }
    };


    return (
        <div className="bg-gray-100 min-h-screen p-8 font-sans">
            <div className="max-w-4xl mx-auto">
                <MultiStepForm />
            </div>
        </div>
    );
}