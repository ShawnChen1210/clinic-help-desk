import React, {useState} from "react";
import {useParams} from "react-router-dom";
import api from '../../utils/axiosConfig'

export default function UploadForm({onUploadSuccess}) {
    const [selectedFile, setSelectedFile] = useState(null);
    const [status, setStatus] = useState('Please Select a File')
    const { sheet_id } = useParams()

    const handleFileChange = (event) => {
        setSelectedFile(event.target.files[0]);
        setStatus('File ready to upload');
    };

    const handleUpload = async (event) => {
        event.preventDefault(); //stops form reloading page

        if (!selectedFile) {
            setStatus('No file selected!');
            return;
        }

        setStatus('Uploading...')

        const formData = new FormData()

        formData.append('file', selectedFile)
         try {
          //Send the FormData object to your Django endpoint
              const response = await api.post(
                `/api/spreadsheets/${sheet_id}/upload_csv/`,
                formData,
                {
                  headers: {
                    'Content-Type': 'multipart/form-data',
                  },
                }
              );

              setStatus('Upload successful!');
              onUploadSuccess(response.data); // Notify the parent component

        } catch (error) {
          console.error('Error uploading file:', error);
          setStatus('Upload failed. Please try again.');
        }
    }

    return (
        <form onSubmit={handleUpload} className="p-8 bg-white max-w-md rounded-lg shadow-md">
            <h2 className="text-xl font-bold mb-4">Upload CSV File</h2>

            <input
                type="file"
                onChange={handleFileChange}
                accept=".csv" // Restrict to only CSV files
                className="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100"
            />

            <div className="mt-6">
                <button
                    type="submit"
                    className="w-full bg-blue-500 hover:bg-blue-600 text-white font-bold py-2 px-4 rounded-lg transition-colors disabled:bg-gray-400"
                    disabled={!selectedFile}
                >
                    Upload
                </button>
            </div>

            <p className="mt-4 text-sm text-center text-gray-500">{status}</p>
        </form>
    );
}