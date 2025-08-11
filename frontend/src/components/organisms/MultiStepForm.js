import React, { useState } from 'react';
import UploadForm from '../molecules/UploadForm'
import TanstackTable from "../atoms/TanstackTable";
import ConfirmMergeForm from "../molecules/ConfirmMergeForm";
import {getCoreRowModel, useReactTable} from "@tanstack/react-table";
import axios from "axios";
import api from "../../utils/axiosConfig";
import { useListTable } from "../../hooks/useListTable";
import { useDictTable } from "../../hooks/useDictTable";
import { useNavigate, useParams } from "react-router-dom";

// --- Step Components ---

function StepOne({ onNext, onUploadSuccess }) {
  return (
    <div className="flex justify-center items-center h-[80vh]">
        <div>
            <h1 className="text-2xl font-bold text-gray-800 mb-2 p-4">Step 1: Upload CSV files</h1>
            <p className="text-sm text-gray-600 mb-4 px-4">
                The system will automatically detect columns with format #####-P## or #####-C## for merging.
            </p>
            <UploadForm onUploadSuccess={onUploadSuccess}/>
        </div>
    </div>
  );
}

function StepTwo({onBack, table, finalMergeSuccess, mergeInfo}) {
    return (
        <div className="w-full max-w-7xl mx-auto">
            <h1 className="text-2xl font-bold text-gray-800 mb-2">Step 2: Verify merged data</h1>
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-4">
                <p className="text-sm text-blue-800">
                    <strong>Auto-detected merge columns:</strong>
                    <br />• Existing sheet: "{mergeInfo.stored_merge_column}"
                    <br />• Uploaded file: "{mergeInfo.uploaded_merge_column}"
                    <br />• Merge strategy: {mergeInfo.merge_strategy || 'Automatic merge/insert'}
                </p>
            </div>
            <p className="text-sm text-gray-600 mb-4">
                This is a preview of the merged data. If it looks correct, press "Confirm & Save".
            </p>
            <ConfirmMergeForm table={table} onMergeSuccess={finalMergeSuccess}/>
        </div>
    );
}

// --- Main Form Controller Component ---

export default function MultiStepForm() {
    const [currentStep, setCurrentStep] = useState(1);
    const {sheet_id} = useParams()

    // Variables for storing merged table data
    const [mergedColumns, setMergedColumns] = useState([])
    const [mergedData, setMergedData] = useState([])
    const [mergeInfo, setMergeInfo] = useState({}) // Store merge column info

    const navigate = useNavigate()

    const handleBack = () => setCurrentStep(prev => prev - 1);

    // Handle upload success - now automatically triggers merge
    const handleUploadSuccess = async (apiData) => {
        if (apiData.status === 'first_upload_complete') {
            alert(`First upload successful! Auto-detected merge column: "${apiData.merge_column}"`);
            navigate(`/spreadsheet/${sheet_id}/`);
            return;
        }

        // For subsequent uploads, automatically trigger merge
        try {
            const mergeResponse = await api.post(`/api/spreadsheets/${sheet_id}/merge_sheets/`);

            setMergedData(mergeResponse.data.merged_data);
            setMergedColumns(mergeResponse.data.merged_headers);
            setMergeInfo({
                stored_merge_column: apiData.stored_merge_column,
                uploaded_merge_column: apiData.uploaded_merge_column,
                merge_strategy: mergeResponse.data.merge_strategy || 'Auto merge/insert'
            });

            setCurrentStep(2);
        } catch (error) {
            console.error('Auto-merge failed:', error);
            alert(`Merge failed: ${error.response?.data?.error || 'Unknown error'}`);
        }
    };

    const mergedTable = useDictTable({
        rawColumns: mergedColumns,
        rawData: mergedData
    })

    const finalMergeSuccess = () => {
      navigate(`/spreadsheet/${sheet_id}/`)
    }

    const renderStep = () => {
        switch (currentStep) {
            case 1:
                return <StepOne onUploadSuccess={handleUploadSuccess} />;
            case 2:
                return <StepTwo
                    onBack={handleBack}
                    table={mergedTable}
                    finalMergeSuccess={finalMergeSuccess}
                    mergeInfo={mergeInfo}
                />;
            default:
                return <StepOne onUploadSuccess={handleUploadSuccess}/>;
        }
    };

    return (
        <div>
            {renderStep()}
        </div>
    );
}