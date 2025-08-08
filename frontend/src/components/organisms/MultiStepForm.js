import React, { useState } from 'react';
import UploadForm from '../molecules/UploadForm'
import TanstackTable from "../atoms/TanstackTable";
import JoinTableForm from "../molecules/JoinTableForm";
import ConfirmMergeForm from "../molecules/ConfirmMergeForm";
import {getCoreRowModel, useReactTable} from "@tanstack/react-table";
import axios from "axios";
import api from "../../utils/axiosConfig";
import { useListTable } from "../../hooks/useListTable";
import { useDictTable } from "../../hooks/useDictTable";
import { useNavigate, useParams } from "react-router-dom";


// --- Step Components ---
// Each step is its own component. It receives functions to go next or back.

function StepOne({ onNext, onUploadSuccess }) {
  return (
    <div className="flex justify-center items-center h-[80vh]">
        <div>
            <h1 className="text-2xl font-bold text-gray-800 mb-2 p-4">Step 1: Upload CSV files</h1>
            <UploadForm onUploadSuccess={onUploadSuccess}/>
        </div>
    </div>
  );
}

function StepTwo({onNext, onBack, tableL, tableR, onMergeSuccess}) {
    return (
        <div className="flex justify-center items-center">
            <div>
                <h1 className="text-2xl font-bold text-gray-800 mb-2">Step 2: Choose one column from each table to be
                    the merge columns.</h1>
                <p className="text-sm text-gray-600 mb-4">
                    IMPORTANT: They must have data in the same format to be mergeable, (e.g. "Column 1: 2021-04-09" and
                    Column 2: "April 9th, 2024" are not mergeable)
                    It is also recommended to choose two columns with all UNIQUE values, to avoid repeating rows after
                    join.
                </p>
                <JoinTableForm tableL={tableL} tableR={tableR} onJoinSuccess={onMergeSuccess}/>
            </div>
        </div>
    );
}

function StepThree({onBack, table, finalMergeSuccess}) {
    return (
        <div className="w-full max-w-7xl mx-auto">
            <h1 className="text-2xl font-bold text-gray-800 mb-2">Step 3: Verify data is correct</h1>
            <p className="text-sm text-gray-600 mb-4">
                This is a preview of the merged data. If it looks correct, press "Confirm & Save".
            </p>
            <ConfirmMergeForm table={table} onMergeSuccess={finalMergeSuccess}/>
        </div>
    );
}


// --- Main Form Controller Component ---
// This component manages the state and decides which step to show.

export default function MultiStepForm() {
    // STATE: A state variable to hold the current step number.
    const [currentStep, setCurrentStep] = useState(1);
    const {sheet_id} = useParams()

    //variables for storing headers and body for the second step (joining tables)
    const [columns, setColumns] = useState([]);
    const [data, setData] = useState([]);
    const [sheetColumns, setSheetColumns] = useState([])
    const [sheetData, setSheetData] = useState([])

    //variables for storing headers and body of the merged table
    const [mergedColumns, setMergedColumns] = useState([])
    const [mergedData, setMergedData] = useState([])

    const navigate = useNavigate()
  // NAVIGATION: Functions to update the step state.
  const handleNext = () => setCurrentStep(prev => prev + 1);
  const handleBack = () => setCurrentStep(prev => prev - 1);

  // vv----BELOW IS CODE FOR HANDLING RETURNED DATA FROM A SUCCESSFUL CSV UPLOAD----vv
  const handleUploadSuccess = (apiData) => {

        if (apiData.status === 'first_upload_complete') {
            alert('First upload successful! Your sheet has been populated.');
            // Redirect the user back to the main spreadsheet view
            navigate(`/spreadsheet/${sheet_id}/`);
            return;
        }
      // Transform headers
        const transformedColumns = apiData.headers.map(header => ({
            header: header,
            accessorKey: header
        }));

        // Set the state
        setColumns(transformedColumns);
        setData(apiData.body);

        setSheetColumns(apiData.sheet_headers);
        setSheetData(apiData.sheet_data);

        // Move to the next step
        setCurrentStep(2);
  };

  //table for the uploaded csv
  const tableR = useReactTable({
        data,
        columns,
        getCoreRowModel: getCoreRowModel(),
  });

  const tableL = useListTable({
      rawColumns: sheetColumns,
      rawData: sheetData
  })

  // ^^----ABOVE IS CODE FOR HANDLING RETURNED DATA FROM A SUCCESSFUL CSV UPLOAD----^^

    // vv----BELOW IS CODE FOR HANDLING SUCCESSFUL TABLE MERGE----vv
    const handleMergeSuccess = (apiData) => {
        setMergedData(apiData.merged_data)
        setMergedColumns(apiData.merged_headers)
        setCurrentStep(3);
    }

    const mergedTable = useDictTable({
        rawColumns: mergedColumns,
        rawData: mergedData
    })

    const finalMergeSuccess = () => {
      navigate(`/spreadsheet/${sheet_id}/`)
    }

    // CONDITIONAL RENDERING: A function or switch case to render the correct step.
  const renderStep = () => {
    switch (currentStep) {
      case 1:
        return <StepOne onNext={handleNext} onUploadSuccess={handleUploadSuccess} />;
      case 2:
        return <StepTwo onNext={handleNext} onBack={handleBack} tableL={tableL} tableR={tableR} onMergeSuccess={handleMergeSuccess}/>;
      case 3:
        return <StepThree onBack={handleBack} table={mergedTable} finalMergeSuccess={finalMergeSuccess}/>;
      default:
        return <StepOne onNext={handleNext}/>;
    }
  };

  return (
    <div>
      {renderStep()}
    </div>
  );
}