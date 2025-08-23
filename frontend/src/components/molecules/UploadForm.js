import React, { useState } from "react";
import api from '../../utils/axiosConfig';
import {useParams} from "react-router-dom";

export default function UploadForm({ onUploadSuccess, clinicId }) {
    const [selectedFile, setSelectedFile] = useState(null);
    const [status, setStatus] = useState('Please select a CSV file');
    const [uploading, setUploading] = useState(false);

    const handleFileChange = (event) => {
        const file = event.target.files[0];
        if (file?.name.toLowerCase().endsWith('.csv')) {
            setSelectedFile(file);
            setStatus('File ready to upload');
        } else {
            setSelectedFile(null);
            setStatus('Please select a CSV file');
        }
    };

    const handleUpload = async (event) => {
        event.preventDefault();
        if (!selectedFile) return;

        setUploading(true);
        setStatus('Detecting file type and uploading...');

        const formData = new FormData();
        formData.append('file', selectedFile);
        formData.append('clinic_id', clinicId);

        try {
            const response = await api.post('/api/spreadsheets/detect_and_upload/', formData, {
                headers: { 'Content-Type': 'multipart/form-data' }
            });

            setStatus('✅ Upload successful!');
            setTimeout(() => onUploadSuccess(response.data), 1000);

        } catch (error) {
            const errorMsg = error.response?.data?.error || 'Upload failed';
            setStatus(`❌ ${errorMsg}`);
        } finally {
            setUploading(false);
        }
    };

    return (
        <div className="bg-white rounded-lg shadow-md p-8">
            <form onSubmit={handleUpload}>
                <div className="mb-6">
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                        Select CSV File
                    </label>
                    <input
                        type="file"
                        onChange={handleFileChange}
                        accept=".csv"
                        className="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100 border border-gray-300 rounded-lg p-3"
                        disabled={uploading}
                    />
                </div>

                <div className="mb-6 p-4 bg-blue-50 border border-blue-200 rounded-lg">
                    <h3 className="font-medium text-blue-800 mb-2">Supported Types (Auto-Detected):</h3>
                    <ul className="text-sm text-blue-700 space-y-1">
                        <li>• <strong>Compensation/Sales Reports</strong></li>
                        <li>• <strong>Daily Transaction Reports</strong></li>
                        <li>• <strong>Payment Transaction Reports</strong></li>
                        <li>• <strong>Transaction Reports</strong></li>
                        <li>• <strong>Hour Time Reports</strong></li>
                    </ul>
                </div>

                <button
                    type="submit"
                    className="w-full bg-blue-500 hover:bg-blue-600 text-white font-bold py-3 px-4 rounded-lg transition-colors disabled:bg-gray-400"
                    disabled={!selectedFile || uploading}
                >
                    {uploading ? 'Processing...' : 'Upload & Auto-Detect'}
                </button>

                <div className="mt-4 p-3">
                    <p className="text-sm text-center text-gray-600">{status}</p>
                </div>
            </form>
        </div>
    );
}