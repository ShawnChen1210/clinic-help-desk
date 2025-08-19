import React, { useState } from 'react';
import TanstackTable from "../atoms/TanstackTable";
import ConfirmMergeForm from "../molecules/ConfirmMergeForm";
import UploadForm from "../molecules/UploadForm";
import api from "../../utils/axiosConfig";
import { useDictTable } from "../../hooks/useDictTable";
import { useNavigate, useParams } from "react-router-dom";

// --- Step Components ---

function StepOne({ onUploadSuccess, clinicId }) {
    return (
        <div className="flex justify-center items-center h-[80vh]">
            <div>
                <h1 className="text-2xl font-bold text-gray-800 mb-2 p-4">Upload CSV File</h1>
                <p className="text-sm text-gray-600 mb-4 px-4">
                    The system will automatically detect the file type and upload to the correct sheet.
                </p>
                <UploadForm onUploadSuccess={onUploadSuccess} clinicId={clinicId} />
            </div>
        </div>
    );
}

function StepTwo({ table, finalMergeSuccess, targetSheetId }) {
    return (
        <div className="w-full max-w-7xl mx-auto">
            <h1 className="text-2xl font-bold text-gray-800 mb-2">Step 2: Verify merged data</h1>
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-4">
                <p className="text-sm text-blue-800">
                    <strong>Merge Preview:</strong>
                    <br />• Sheet Type: Compensation/Sales Data
                    <br />• Action: Update existing data with new entries
                    <br />• Strategy: Key-based merge with update/insert logic
                </p>
            </div>
            <p className="text-sm text-gray-600 mb-4">
                This is a preview of the merged data. If it looks correct, press "Confirm & Save".
            </p>
            <ConfirmMergeForm
                table={table}
                onMergeSuccess={finalMergeSuccess}
                targetSheetId={targetSheetId}
            />
        </div>
    );
}

// --- Main Form Controller Component ---

export default function MultiStepForm() {
    const [currentStep, setCurrentStep] = useState(1);
    const { clinic_id } = useParams(); // Get clinic_id from URL

    // Variables for storing merged table data
    const [mergedColumns, setMergedColumns] = useState([]);
    const [mergedData, setMergedData] = useState([]);
    const [targetSheetId, setTargetSheetId] = useState(null);

    const navigate = useNavigate();

    // Handle upload success from the new auto-detection system
    const handleUploadSuccess = async (apiData) => {
        const { action, target_sheet_id, sheet_type } = apiData;

        if (action === 'first_upload' || action === 'data_updated') {
            // Direct upload successful - redirect to the target sheet
            navigate(`/chd-app/${clinic_id}/spreadsheet/${target_sheet_id}`);
            return;
        }

        if (action === 'merge_required') {
            // Need merge preview - trigger merge and show step 2
            setTargetSheetId(target_sheet_id);

            try {
                const mergeResponse = await api.post(`/api/spreadsheets/${target_sheet_id}/merge_sheets/`);

                setMergedData(mergeResponse.data.merged_data);
                setMergedColumns(mergeResponse.data.merged_headers);
                setCurrentStep(2);

            } catch (error) {
                console.error('Auto-merge failed:', error);
                alert(`Merge failed: ${error.response?.data?.error || 'Unknown error'}`);
            }
        }
    };

    const mergedTable = useDictTable({
        rawColumns: mergedColumns,
        rawData: mergedData
    });

    const finalMergeSuccess = () => {
        // Navigate to the target sheet after successful merge
        navigate(`/chd-app/${clinic_id}/spreadsheet/${targetSheetId}`);
    };

    const renderStep = () => {
        switch (currentStep) {
            case 1:
                return <StepOne onUploadSuccess={handleUploadSuccess} clinicId={clinic_id} />;
            case 2:
                return (
                    <StepTwo
                        table={mergedTable}
                        finalMergeSuccess={finalMergeSuccess}
                        targetSheetId={targetSheetId}
                    />
                );
            default:
                return <StepOne onUploadSuccess={handleUploadSuccess} clinicId={clinic_id} />;
        }
    };

    return (
        <div>
            {renderStep()}
        </div>
    );
}